"""
MINE-X DRONE COMMAND - Telemetry Aggregator & History Buffer
Consolidates drone state, sensor arrays, alerts, and rolling historical buffers
for live telemetry graphs (altitude, battery, velocity, gases, temperature, RSSI).
"""

import time
import math
from collections import deque
from typing import Dict, Any, List
from .simulator import MineSimulator
from .sensors import SensorManager
from .safety import SafetyManager

class TelemetryManager:
    """Manages full telemetry state assembly and rolling historical graph buffers."""
    def __init__(self, simulator: MineSimulator, sensors: SensorManager, safety: SafetyManager, controller=None):
        self.sim = simulator
        self.sensors = sensors
        self.safety = safety
        self.controller = controller
        
        # Max history: 5 minutes at 2 Hz = 600 data points
        self.max_history = 600
        self.history_buffer = deque(maxlen=self.max_history)
        self.last_history_tick = 0.0

    def get_current_packet(self) -> Dict[str, Any]:
        """Assemble full real-time telemetry packet."""
        sensor_data = self.sensors.get_all_sensor_data()
        
        # Ground and vertical speed
        ground_spd = math.sqrt(self.sim.vx**2 + self.sim.vz**2)
        vert_spd = self.sim.vy
        speed_3d = math.sqrt(ground_spd**2 + vert_spd**2)

        # Active sector
        z = self.sim.z
        if z > 15.0:
            active_sector = "1. Portal Entrance Arch"
        elif z > -50.0:
            active_sector = "2. Western Timber Corridor"
        elif z > -95.0:
            active_sector = "3. Grand Extraction Stope"
        elif z > -140.0:
            active_sector = "4. North-East Ore Chute"
        else:
            active_sector = "5. Deep Abyss Winze Shaft"

        active_fault = getattr(self.controller, 'active_fault', None)

        packet = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "data_source": "SIMULATION",
            "connection_status": "ONLINE",
            "armed": bool(self.sim.armed),
            "motion_mode": str(getattr(self.sim, 'motion_mode', 'FLIGHT')),
            "ground_contact": bool(getattr(self.sim, 'ground_contact', False)),
            "cage_radius": float(getattr(self.sim, 'cage_radius', 1.35)),
            "flight_status": {
                "armed": bool(self.sim.armed),
                "flight_mode": str(self.sim.flight_mode),
                "motion_mode": str(getattr(self.sim, 'motion_mode', 'FLIGHT')),
                "ground_contact": bool(getattr(self.sim, 'ground_contact', False)),
                "cage_radius": float(getattr(self.sim, 'cage_radius', 1.35)),
                "active_sector": active_sector,
                "speed_mode": "BOOST" if self.sim.speed_multiplier > 1.2 else ("PRECISION" if self.sim.speed_multiplier < 0.8 else "NORMAL"),
                "total_distance_m": round(self.sim.total_distance_m, 1),
                "flight_time_s": int(time.time() - self.sim.start_time),
                "active_fault": active_fault
            },
            "position": {
                "x": round(self.sim.x, 2),
                "y": round(self.sim.y, 2),
                "z": round(self.sim.z, 2)
            },
            "velocity": {
                "x": round(self.sim.vx, 2),
                "y": round(self.sim.vy, 2),
                "z": round(self.sim.vz, 2)
            },
            "orientation": {
                "roll": round(self.sim.roll, 1),
                "pitch": round(self.sim.pitch, 1),
                "yaw": round(self.sim.yaw, 1)
            },
            "altitude": round(self.sim.y, 2),
            "ground_speed": round(ground_spd, 2),
            "vertical_speed": round(vert_spd, 2),
            "total_speed": round(speed_3d, 2),
            "heading": round(self.sim.yaw, 1),
            "battery": sensor_data["battery"],
            "sensors": sensor_data,
            "alerts": self.safety.evaluate({
                "battery": sensor_data["battery"],
                "position": {"x": self.sim.x, "y": self.sim.y, "z": self.sim.z}
            }, sensor_data)
        }

        # Record into rolling graph history buffer (at 2Hz)
        now = time.time()
        if now - self.last_history_tick >= 0.5:
            self.last_history_tick = now
            graph_entry = {
                "t": round(now, 1),
                "alt": round(self.sim.y, 2),
                "batt": round(sensor_data["battery"]["percentage"], 1),
                "spd": round(speed_3d, 2),
                "ch4": round(sensor_data["gas"]["ch4_pct"], 3),
                "co": round(sensor_data["gas"]["co_ppm"], 1),
                "co2": round(sensor_data["gas"]["co2_ppm"], 0),
                "o2": round(sensor_data["gas"]["o2_pct"], 1),
                "temp": round(sensor_data["thermal"]["hotspot_temp"], 1),
                "rssi": round(sensor_data["comms"]["rssi_dbm"], 1)
            }
            self.history_buffer.append(graph_entry)

        return packet

    def get_history(self, seconds: int = 60) -> List[Dict[str, Any]]:
        """Return rolling history filtered by duration."""
        cutoff = time.time() - seconds
        return [entry for entry in self.history_buffer if entry["t"] >= cutoff]
