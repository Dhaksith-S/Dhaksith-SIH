"""
MINE-X DRONE COMMAND - Safety Manager & Alert Center
Continuously evaluates telemetry against safety thresholds, generates categorized alarms,
maintains active alerts, and coordinates automatic failsafe behaviors (auto-hover, RTH, emergency stop).
"""

import time
import logging
from typing import Dict, Any, List
from .config import SAFETY_THRESHOLDS
from .database import log_alert, acknowledge_alert

logger = logging.getLogger("SafetyManager")

class SafetyManager:
    """Evaluates drone and sensor health and generates real-time alerts."""
    def __init__(self):
        self.active_alerts: List[Dict[str, Any]] = []
        self.alert_history: List[Dict[str, Any]] = []
        self.last_check_time = 0.0
        self._alert_id_counter = 1
        
        # Debounce timer dictionaries to prevent spamming
        self._last_alert_times: Dict[str, float] = {}

    def _trigger_alert(self, code: str, severity: str, message: str, sensor: str, value: float, threshold: float):
        """Register a new alert if not already active or cooled down."""
        now = time.time()
        # 4-second cooldown per alert code
        if code in self._last_alert_times and (now - self._last_alert_times[code]) < 4.0:
            return

        self._last_alert_times[code] = now
        
        # Check if already present in active alerts
        for a in self.active_alerts:
            if a["code"] == code and not a.get("acknowledged", False):
                a["value"] = value
                a["timestamp"] = time.strftime("%H:%M:%S")
                return

        alert_item = {
            "id": self._alert_id_counter,
            "code": code,
            "severity": severity,  # INFO, WARNING, CRITICAL, EMERGENCY
            "message": message,
            "sensor": sensor,
            "value": round(value, 2),
            "threshold": threshold,
            "timestamp": time.strftime("%H:%M:%S"),
            "acknowledged": False
        }
        self._alert_id_counter += 1
        
        self.active_alerts.insert(0, alert_item)
        if len(self.active_alerts) > 20:
            self.active_alerts.pop()
            
        self.alert_history.insert(0, alert_item)
        if len(self.alert_history) > 100:
            self.alert_history.pop()

        # Persist to SQLite
        log_alert(alert_item)
        logger.warning("[SAFETY ALERT] [%s] %s: %s (Val: %s, Thresh: %s)", severity, code, message, value, threshold)

    def evaluate(self, telemetry: Dict[str, Any], sensors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run safety inspection on full state snapshot."""
        # 1. Atmospheric Gas Checks
        gas = sensors.get("gas", {})
        ch4 = gas.get("ch4_pct", 0.0)
        co = gas.get("co_ppm", 0.0)
        co2 = gas.get("co2_ppm", 0.0)
        o2 = gas.get("o2_pct", 20.9)
        h2s = gas.get("h2s_ppm", 0.0)

        if ch4 >= SAFETY_THRESHOLDS["ch4_critical_pct"]:
            self._trigger_alert("HIGH_METHANE", "CRITICAL", "High Methane Detected - Flammable Hazard!", "CH4 Sensor", ch4, SAFETY_THRESHOLDS["ch4_critical_pct"])
        elif ch4 >= SAFETY_THRESHOLDS["ch4_warning_pct"]:
            self._trigger_alert("METHANE_WARN", "WARNING", "Elevated Methane Detected", "CH4 Sensor", ch4, SAFETY_THRESHOLDS["ch4_warning_pct"])

        if o2 <= SAFETY_THRESHOLDS["o2_critical_pct"]:
            self._trigger_alert("LOW_OXYGEN", "EMERGENCY", "Critical Oxygen Deficiency!", "O2 Sensor", o2, SAFETY_THRESHOLDS["o2_critical_pct"])
        elif o2 <= SAFETY_THRESHOLDS["o2_min_safe_pct"]:
            self._trigger_alert("OXYGEN_WARN", "WARNING", "Sub-nominal Oxygen Level", "O2 Sensor", o2, SAFETY_THRESHOLDS["o2_min_safe_pct"])

        if co >= SAFETY_THRESHOLDS["co_critical_ppm"]:
            self._trigger_alert("HIGH_CO", "CRITICAL", "Dangerous Carbon Monoxide Concentration!", "CO Sensor", co, SAFETY_THRESHOLDS["co_critical_ppm"])
        elif co >= SAFETY_THRESHOLDS["co_warning_ppm"]:
            self._trigger_alert("CO_WARN", "WARNING", "Elevated Carbon Monoxide Detected", "CO Sensor", co, SAFETY_THRESHOLDS["co_warning_ppm"])

        if h2s >= SAFETY_THRESHOLDS["h2s_critical_ppm"]:
            self._trigger_alert("HIGH_H2S", "CRITICAL", "Lethal Hydrogen Sulfide Detected!", "H2S Sensor", h2s, SAFETY_THRESHOLDS["h2s_critical_ppm"])

        # 2. Obstacle Proximity Checks
        distances = sensors.get("distances", {})
        # Horizontal and ceiling distances
        surround_dist = min([distances.get(k, 10.0) for k in ["front", "rear", "left", "right", "up"]])
        down_dist = distances.get("down", 10.0)
        is_armed = telemetry.get("armed", False)

        if surround_dist <= SAFETY_THRESHOLDS["obstacle_critical_m"] or (is_armed and down_dist <= 0.5 and telemetry.get("vertical_speed", 0.0) < -1.0):
            self._trigger_alert("COLLISION_RISK", "EMERGENCY", f"Imminent Obstacle Hazard ({min(surround_dist, down_dist):.1f}m)!", "ToF Array", min(surround_dist, down_dist), SAFETY_THRESHOLDS["obstacle_critical_m"])
        elif surround_dist <= SAFETY_THRESHOLDS["obstacle_warning_m"]:
            self._trigger_alert("OBSTACLE_CLOSE", "WARNING", f"Obstacle Too Close ({surround_dist:.1f}m)", "ToF Array", surround_dist, SAFETY_THRESHOLDS["obstacle_warning_m"])

        # 3. Thermal Camera Hotspot
        thermal = sensors.get("thermal", {})
        hotspot = thermal.get("hotspot_temp", 20.0)
        if hotspot >= SAFETY_THRESHOLDS["temp_critical_c"]:
            self._trigger_alert("HIGH_TEMPERATURE", "CRITICAL", f"Thermal Hotspot Exceeded ({hotspot:.1f}°C)!", "LWIR Thermal", hotspot, SAFETY_THRESHOLDS["temp_critical_c"])
        elif hotspot >= SAFETY_THRESHOLDS["temp_warning_c"]:
            self._trigger_alert("TEMP_WARN", "WARNING", f"Elevated Ambient Hotspot ({hotspot:.1f}°C)", "LWIR Thermal", hotspot, SAFETY_THRESHOLDS["temp_warning_c"])

        # 4. Battery Level
        battery = telemetry.get("battery", {})
        batt_pct = battery.get("percentage", 100.0)
        if batt_pct <= SAFETY_THRESHOLDS["battery_critical_pct"]:
            self._trigger_alert("LOW_BATTERY", "CRITICAL", f"Critical Battery ({batt_pct:.1f}%) - Land Immediately!", "Smart BMS", batt_pct, SAFETY_THRESHOLDS["battery_critical_pct"])
        elif batt_pct <= SAFETY_THRESHOLDS["battery_low_pct"]:
            self._trigger_alert("BATTERY_LOW", "WARNING", f"Low Battery ({batt_pct:.1f}%)", "Smart BMS", batt_pct, SAFETY_THRESHOLDS["battery_low_pct"])

        # 5. Communication RF Link
        comms = sensors.get("comms", {})
        rssi = comms.get("rssi_dbm", -50.0)
        if rssi <= SAFETY_THRESHOLDS["rssi_critical_dbm"]:
            self._trigger_alert("WEAK_COMMUNICATION", "CRITICAL", f"Mesh Radio Link Degraded ({rssi:.1f} dBm)!", "900MHz Radio", rssi, SAFETY_THRESHOLDS["rssi_critical_dbm"])

        # 6. GNSS Status Notice (Informational for underground mines)
        gnss = sensors.get("gnss", {})
        if gnss.get("status") == "UNDERGROUND UNAVAILABLE":
            if "GNSS_UNAVAILABLE" not in self._last_alert_times:
                self._trigger_alert("GNSS_UNAVAILABLE", "INFO", "GNSS Shielded by Overburden - Inertial/LiDAR Nav Active", "GNSS Receiver", 0, 0)

        # 7. Motor Temperatures
        motors = sensors.get("motors", [])
        for m in motors:
            if m.get("temp_c", 0.0) >= SAFETY_THRESHOLDS["motor_temp_max_c"]:
                self._trigger_alert("HIGH_MOTOR_TEMP", "WARNING", f"Motor #{m.get('id')} Overheating ({m.get('temp_c')}°C)", "ESC Telemetry", m.get("temp_c"), SAFETY_THRESHOLDS["motor_temp_max_c"])

        return self.active_alerts

    def acknowledge(self, alert_id: int):
        """Acknowledge an alert."""
        for a in self.active_alerts:
            if a["id"] == alert_id:
                a["acknowledged"] = True
                acknowledge_alert(alert_id)
                break
        # Remove acknowledged alerts from active view
        self.active_alerts = [a for a in self.active_alerts if not a.get("acknowledged", False)]
