"""
MINE-X DRONE COMMAND - Sensor Manager
Aggregates readings from all physical or simulated hardware sensors:
Gas array, LiDAR, RGB camera, Thermal LWIR, IMU, Distance rangefinders,
Barometer, GNSS, Motors, ESCs, Power rails, and Onboard computer.
"""

from typing import Dict, Any, List
from .hardware import HardwareSystem
from .simulator import MineSimulator

class SensorManager:
    """Consolidates all drone sensor readings into structured telemetry packets."""
    def __init__(self, hardware: HardwareSystem, simulator: MineSimulator):
        self.hw = hardware
        self.sim = simulator

    def get_all_sensor_data(self) -> Dict[str, Any]:
        """Collect synchronized sensor readings across all subsystems."""
        gas_data = self.hw.gas.read_all_gases()
        thermal_data = self.hw.thermal.get_thermal_data()
        imu_data = self.hw.imu.read_imu()
        dist_data = self.hw.distances.read_distances()
        baro_data = self.hw.barometer.read_barometer()
        comms_data = self.hw.comms.read_telemetry_link()
        lidar_data = self.hw.lidar.get_scan()
        cam_status = self.hw.camera.get_status()
        battery_data = self.hw.battery.read_battery()
        motors_data = self.hw.motors.read_motors()
        escs_data = self.hw.motors.read_escs()
        gnss_data = self.sim.generate_gnss_data()
        power_rails = self.sim.generate_power_rails()
        computer_status = self.sim.generate_onboard_computer_status()

        # Overall health badges for dashboard
        health_summary = {
            "lidar": self.hw.lidar.get_status().get("health", "ONLINE"),
            "rgb": cam_status.get("health", "ONLINE"),
            "thermal": thermal_data.get("status", "NORMAL"),
            "ch4": "WARNING" if gas_data.get("ch4_pct", 0) > 0.20 else "ONLINE",
            "co": "WARNING" if gas_data.get("co_ppm", 0) > 25.0 else "ONLINE",
            "co2": "WARNING" if gas_data.get("co2_ppm", 0) > 1000.0 else "ONLINE",
            "o2": "CRITICAL" if gas_data.get("o2_pct", 20.9) < 18.0 else ("WARNING" if gas_data.get("o2_pct", 20.9) < 19.5 else "ONLINE"),
            "h2s": "WARNING" if gas_data.get("h2s_ppm", 0) > 5.0 else "ONLINE",
            "imu": self.hw.imu.get_status().get("health", "ONLINE"),
            "barometer": self.hw.barometer.get_status().get("health", "ONLINE"),
            "gnss": "ONLINE" if gnss_data.get("status") == "SURFACE AVAILABLE" else "NO FIX"
        }

        return {
            "gas": gas_data,
            "thermal": thermal_data,
            "imu": imu_data,
            "distances": dist_data,
            "barometer": baro_data,
            "gnss": gnss_data,
            "lidar": lidar_data,
            "camera": cam_status,
            "battery": battery_data,
            "motors": motors_data,
            "escs": escs_data,
            "comms": comms_data,
            "power_rails": power_rails,
            "onboard_computer": computer_status,
            "health_summary": health_summary
        }
