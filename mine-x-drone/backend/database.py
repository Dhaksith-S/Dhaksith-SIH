"""
MINE-X DRONE COMMAND - Database & Telemetry Logger
Stores flight telemetry, sensor readings, alerts, and mission logs in SQLite.
"""

import sqlite3
import datetime
import csv
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from .config import DB_PATH, LOGS_DIR

logger = logging.getLogger("Database")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables for telemetry, sensors, alerts, and missions."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # Telemetry Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        x REAL, y REAL, z REAL,
        vx REAL, vy REAL, vz REAL,
        roll REAL, pitch REAL, yaw REAL,
        altitude REAL, ground_speed REAL, vertical_speed REAL,
        battery_pct REAL, battery_voltage REAL, battery_current REAL,
        armed INTEGER, flight_mode TEXT
    );
    """)

    # Sensor Readings Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        ch4_pct REAL, co_ppm REAL, co2_ppm REAL, o2_pct REAL, h2s_ppm REAL,
        temp_ambient REAL, temp_hotspot REAL,
        pressure_hpa REAL,
        dist_front REAL, dist_rear REAL, dist_left REAL, dist_right REAL, dist_up REAL, dist_down REAL,
        rssi_dbm REAL, lidar_points_sec INTEGER
    );
    """)

    # Safety Alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        severity TEXT NOT NULL,
        code TEXT NOT NULL,
        message TEXT NOT NULL,
        sensor TEXT,
        value REAL,
        threshold REAL,
        acknowledged INTEGER DEFAULT 0
    );
    """)

    # Mission History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_name TEXT NOT NULL,
        status TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        distance_m REAL DEFAULT 0.0,
        area_scanned_pct REAL DEFAULT 0.0,
        waypoints_count INTEGER DEFAULT 0,
        notes TEXT
    );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully at %s", DB_PATH)

def log_telemetry(t: Dict[str, Any]):
    """Insert telemetry snapshot."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
            INSERT INTO telemetry_logs (
                timestamp, x, y, z, vx, vy, vz,
                roll, pitch, yaw, altitude, ground_speed, vertical_speed,
                battery_pct, battery_voltage, battery_current,
                armed, flight_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            t.get("position", {}).get("x", 0.0),
            t.get("position", {}).get("y", 0.0),
            t.get("position", {}).get("z", 0.0),
            t.get("velocity", {}).get("x", 0.0),
            t.get("velocity", {}).get("y", 0.0),
            t.get("velocity", {}).get("z", 0.0),
            t.get("orientation", {}).get("roll", 0.0),
            t.get("orientation", {}).get("pitch", 0.0),
            t.get("orientation", {}).get("yaw", 0.0),
            t.get("altitude", 0.0),
            t.get("ground_speed", 0.0),
            t.get("vertical_speed", 0.0),
            t.get("battery", {}).get("percentage", 0.0),
            t.get("battery", {}).get("voltage", 0.0),
            t.get("battery", {}).get("current", 0.0),
            1 if t.get("armed", False) else 0,
            t.get("flight_mode", "MANUAL")
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Error logging telemetry: %s", e)

def log_sensors(s: Dict[str, Any]):
    """Insert sensor readings snapshot."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
            INSERT INTO sensor_logs (
                timestamp, ch4_pct, co_ppm, co2_ppm, o2_pct, h2s_ppm,
                temp_ambient, temp_hotspot, pressure_hpa,
                dist_front, dist_rear, dist_left, dist_right, dist_up, dist_down,
                rssi_dbm, lidar_points_sec
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            s.get("gas", {}).get("ch4_pct", 0.0),
            s.get("gas", {}).get("co_ppm", 0.0),
            s.get("gas", {}).get("co2_ppm", 0.0),
            s.get("gas", {}).get("o2_pct", 20.9),
            s.get("gas", {}).get("h2s_ppm", 0.0),
            s.get("thermal", {}).get("avg_temp", 22.0),
            s.get("thermal", {}).get("hotspot_temp", 25.0),
            s.get("barometer", {}).get("pressure_hpa", 1013.25),
            s.get("distances", {}).get("front", 0.0),
            s.get("distances", {}).get("rear", 0.0),
            s.get("distances", {}).get("left", 0.0),
            s.get("distances", {}).get("right", 0.0),
            s.get("distances", {}).get("up", 0.0),
            s.get("distances", {}).get("down", 0.0),
            s.get("comms", {}).get("rssi_dbm", -60.0),
            s.get("lidar", {}).get("points_sec", 120000)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Error logging sensor data: %s", e)

def log_alert(alert: Dict[str, Any]) -> int:
    """Record safety alert."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
            INSERT INTO alerts (timestamp, severity, code, message, sensor, value, threshold, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            now,
            alert.get("severity", "WARNING"),
            alert.get("code", "GENERAL_ALERT"),
            alert.get("message", ""),
            alert.get("sensor", ""),
            alert.get("value", 0.0),
            alert.get("threshold", 0.0)
        ))
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return alert_id
    except Exception as e:
        logger.error("Error logging alert: %s", e)
        return -1

def acknowledge_alert(alert_id: int):
    """Mark an alert acknowledged."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Error acknowledging alert: %s", e)

def get_recent_telemetry(limit: int = 60) -> List[Dict[str, Any]]:
    """Retrieve recent telemetry records."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM telemetry_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows[::-1]
    except Exception as e:
        logger.error("Error fetching telemetry: %s", e)
        return []

def get_recent_alerts(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve recent alerts."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error("Error fetching alerts: %s", e)
        return []

def export_telemetry_csv(limit: int = 1000) -> str:
    """Export recent telemetry to CSV in logs directory."""
    records = get_recent_telemetry(limit)
    if not records:
        return ""
    
    csv_path = LOGS_DIR / "telemetry" / f"telemetry_export_{int(datetime.datetime.utcnow().timestamp())}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        
    return str(csv_path)
