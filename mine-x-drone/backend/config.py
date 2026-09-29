"""
MINE-X DRONE COMMAND - System Configuration & Safety Thresholds
Hardware Abstraction & Operational Parameters
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "mine.db"

# Mode configuration: "SIMULATION" or "REAL"
# When set to "REAL", the Hardware Abstraction Layer loads real serial/MAVLink/sensor drivers
MODE = "SIMULATION"

# Networking
HOST = "0.0.0.0"
PORT = 8000
UPDATE_RATE_HZ = 20  # Telemetry broadcast rate (20 Hz = 50ms)
TELEMETRY_LOG_RATE_HZ = 2  # Database recording rate (2 Hz)

# Drone Physical & Flight Dynamics Parameters
DRONE_PARAMS = {
    "name": "MINE-X Titan-Quad Alpha",
    "frame": "Carbon Fiber X-Frame with High-Impact Polycarbonate Rolling Cage",
    "weight_kg": 2.85,
    "max_speed_ms": 6.5,
    "boost_multiplier": 1.8,
    "precision_multiplier": 0.35,
    "max_vertical_speed_ms": 3.0,
    "max_yaw_rate_rads": 1.8,
    "acceleration": 4.5,  # m/s^2
    "deceleration": 5.0,  # m/s^2 (braking damping)
    "hover_throttle_pct": 48.0,
    "battery_nominal_v": 22.2,  # 6S LiPo
    "battery_capacity_mah": 8500,
    "battery_drain_rate_idle": 0.015,  # % per second
    "battery_drain_rate_active": 0.085,  # % per second under load
    "portal_home_pos": {"x": 0.0, "y": 4.5, "z": 28.0},  # Cavern entrance portal
}

# Cavern Boundary & Obstacle Bounds
MINE_BOUNDS = {
    "max_elevation": 28.0,
    "min_elevation": 0.6,
    "max_z": 38.0,     # Portal mouth
    "min_z": -200.0,   # Deepest stope / winze shaft
    "nominal_radius": 17.0,  # meters
    "stope_radius": 28.0,    # Great Stope expansion
}

# Safety Limits & Alarm Thresholds
SAFETY_THRESHOLDS = {
    # Atmospheric Gases
    "ch4_warning_pct": 0.20,       # Methane CH4 warning
    "ch4_critical_pct": 0.50,      # Methane CH4 critical explosive hazard
    "co_warning_ppm": 25.0,        # Carbon Monoxide CO warning
    "co_critical_ppm": 50.0,       # CO hazardous
    "co2_warning_ppm": 1000.0,     # Carbon Dioxide CO2 warning
    "co2_critical_ppm": 2000.0,    # CO2 dangerous
    "o2_min_safe_pct": 19.5,       # Oxygen O2 minimum safe
    "o2_critical_pct": 18.0,       # Oxygen deficiency emergency
    "h2s_warning_ppm": 5.0,        # Hydrogen Sulfide H2S warning
    "h2s_critical_ppm": 10.0,      # H2S lethal hazard

    # Physical & Thermal
    "obstacle_warning_m": 3.0,     # Proximity warning
    "obstacle_critical_m": 1.2,    # Imminent collision stop
    "temp_warning_c": 52.0,        # Ambient / hotspot warning
    "temp_critical_c": 68.0,       # Hotspot critical
    "motor_temp_max_c": 75.0,
    "esc_temp_max_c": 78.0,

    # Electrical & Comms
    "battery_low_pct": 25.0,
    "battery_critical_pct": 15.0,
    "rssi_weak_dbm": -74.0,
    "rssi_critical_dbm": -84.0,
    "packet_loss_max_pct": 5.0,
}

# Geological Survey Stations
MINE_STATIONS = [
    {
        "id": 0,
        "name": "Portal Entrance Arch",
        "code": "STN-01-PORTAL",
        "coords": {"x": 0.0, "y": 4.5, "z": 25.0},
        "clearance_span_m": 28.4,
        "lithology": "Weathered Terracotta Ironstone Caprock",
        "gnss_available": True,
        "ch4_base": 0.01,
        "co_base": 2.0,
        "temp_base": 19.5
    },
    {
        "id": 1,
        "name": "Western Timber Corridor",
        "code": "STN-02-TIMBER",
        "coords": {"x": 10.0, "y": 6.5, "-30.0": -30.0, "z": -25.0},
        "clearance_span_m": 32.0,
        "lithology": "Massive Ironstone with Limonite Banding",
        "gnss_available": False,
        "ch4_base": 0.02,
        "co_base": 4.0,
        "temp_base": 21.2
    },
    {
        "id": 2,
        "name": "Grand Extraction Stope",
        "code": "STN-03-STOPE",
        "coords": {"x": -14.0, "y": 9.5, "z": -72.0},
        "clearance_span_m": 52.4,
        "lithology": "High-grade Hematite & Jasper Breccia (Central Pillar)",
        "gnss_available": False,
        "ch4_base": 0.04,
        "co_base": 7.0,
        "temp_base": 25.8
    },
    {
        "id": 3,
        "name": "North-East Ore Chute",
        "code": "STN-04-CHUTE",
        "coords": {"x": 16.0, "y": 8.0, "z": -118.0},
        "clearance_span_m": 36.2,
        "lithology": "Fractured Terracotta with Quartz Veining",
        "gnss_available": False,
        "ch4_base": 0.06,
        "co_base": 12.0,
        "temp_base": 28.4
    },
    {
        "id": 4,
        "name": "Deep Abyss Winze Shaft",
        "code": "STN-05-WINZE",
        "coords": {"x": -5.0, "y": 4.5, "z": -160.0},
        "clearance_span_m": 42.0,
        "lithology": "Silicified Hematite & Pyrite Mineralized Sump Basin",
        "gnss_available": False,
        "ch4_base": 0.28,  # Near-warning methane reservoir!
        "co_base": 24.0,
        "temp_base": 34.6
    }
]
