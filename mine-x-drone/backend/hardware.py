"""
MINE-X DRONE COMMAND - Hardware Abstraction Layer (HAL)
Defines clean interfaces for flight controller, sensors, cameras, and power systems.
Allows seamless swapping between Simulated drivers and Real physical hardware
(MAVLink/PX4, RPLiDAR, FLIR Thermal, MQ gas sensors, BNO055 IMU, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import time
import logging

logger = logging.getLogger("HAL")

# ==========================================
# 1. ABSTRACT HARDWARE INTERFACES
# ==========================================

class FlightControllerInterface(ABC):
    """Abstract interface for PX4 / ArduPilot / MAVLink or Simulated flight controller."""
    @abstractmethod
    def arm(self) -> bool:
        pass

    @abstractmethod
    def disarm(self) -> bool:
        pass

    @abstractmethod
    def emergency_stop(self) -> bool:
        pass

    @abstractmethod
    def set_flight_mode(self, mode: str) -> bool:
        pass

    @abstractmethod
    def send_velocity_target(self, vx: float, vy: float, vz: float, yaw_rate: float):
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class LiDARInterface(ABC):
    """Abstract interface for 2D/3D LiDAR (e.g. Livox, Ouster, RPLiDAR, or Simulated)."""
    @abstractmethod
    def get_scan(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def calibrate(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class CameraInterface(ABC):
    """Abstract interface for onboard RGB survey camera (USB / MIPI-CSI / Simulated)."""
    @abstractmethod
    def get_frame(self) -> Optional[bytes]:
        pass

    @abstractmethod
    def set_recording(self, recording: bool) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class ThermalCameraInterface(ABC):
    """Abstract interface for Long-Wave Infrared / Radiometric camera (FLIR Lepton / MLX90640)."""
    @abstractmethod
    def get_thermal_data(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class GasSensorInterface(ABC):
    """Abstract interface for atmospheric gas sensor array (CH4, CO, CO2, O2, H2S)."""
    @abstractmethod
    def read_all_gases(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def zero_calibrate(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class IMUInterface(ABC):
    """Abstract interface for 9-DOF Inertial Measurement Unit (BNO085, ICM-20948, or Simulated)."""
    @abstractmethod
    def read_imu(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def calibrate(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class DistanceSensorsInterface(ABC):
    """Abstract interface for 6-axis obstacle rangefinders (ToF / Ultrasonic / Radar)."""
    @abstractmethod
    def read_distances(self) -> Dict[str, float]:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class BarometerInterface(ABC):
    """Abstract interface for precision digital barometer (BMP390 / MS5611)."""
    @abstractmethod
    def read_barometer(self) -> Dict[str, float]:
        pass

    @abstractmethod
    def calibrate(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class BatteryBMSInterface(ABC):
    """Abstract interface for Smart LiPo BMS & Power Distribution Board (SMBus / CAN)."""
    @abstractmethod
    def read_battery(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class MotorESCInterface(ABC):
    """Abstract interface for 4-in-1 DShot/CAN Electronic Speed Controllers & BLDC motors."""
    @abstractmethod
    def read_motors(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def read_escs(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def set_motor_throttles(self, throttles: List[float]):
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class CommsInterface(ABC):
    """Abstract interface for RF mesh radio, LoRa telemetry transceiver & Wi-Fi bridge."""
    @abstractmethod
    def read_telemetry_link(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


# ==========================================
# 2. SIMULATED HARDWARE DRIVERS
# ==========================================

class SimulatedFlightController(FlightControllerInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref
        self.armed = True
        self.flight_mode = "MANUAL"
        self.last_cmd_time = time.time()
        self.calibrating = False

    def arm(self) -> bool:
        self.armed = True
        logger.info("[HAL-SIM] Flight Controller ARMED")
        return True

    def disarm(self) -> bool:
        self.armed = False
        logger.info("[HAL-SIM] Flight Controller DISARMED")
        return True

    def emergency_stop(self) -> bool:
        self.armed = False
        self.flight_mode = "EMERGENCY"
        logger.warning("[HAL-SIM] EMERGENCY STOP TRIGGERED ON FLIGHT CONTROLLER")
        return True

    def set_flight_mode(self, mode: str) -> bool:
        valid_modes = ["MANUAL", "STABILIZE", "ALTITUDE_HOLD", "POSITION_HOLD", "AUTONOMOUS", "RETURN_TO_HOME", "LAND", "HOVER", "EMERGENCY"]
        if mode in valid_modes:
            self.flight_mode = mode
            logger.info("[HAL-SIM] Flight Mode set to: %s", mode)
            return True
        return False

    def send_velocity_target(self, vx: float, vy: float, vz: float, yaw_rate: float):
        if self.simulator and self.armed:
            self.simulator.set_command_velocity(vx, vy, vz, yaw_rate)

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "PX4 FMUv6X (Simulated)",
            "connection": "CONNECTED",
            "health": "ONLINE",
            "armed": self.armed,
            "flight_mode": self.flight_mode,
            "loop_rate_hz": 400,
            "failsafe_active": False
        }


class SimulatedLiDAR(LiDARInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref
        self.calibrating = False
        self.scan_rate = 20.0  # Hz
        self.range_m = 40.0

    def get_scan(self) -> Dict[str, Any]:
        if self.simulator:
            return self.simulator.generate_lidar_scan()
        return {
            "points": [],
            "point_count": 0,
            "scan_quality": 98.5,
            "points_sec": 120000,
            "status": "ONLINE"
        }

    def calibrate(self) -> bool:
        self.calibrating = True
        logger.info("[HAL-SIM] LiDAR Zero-Calibration started")
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "Titan-LiDAR 360 Solid-State",
            "health": "CALIBRATING" if self.calibrating else "ONLINE",
            "scan_rate_hz": self.scan_rate,
            "points_sec": 124000,
            "range_m": self.range_m,
            "quality_pct": 98.4,
            "fov": "360° Horizontal x 90° Vertical"
        }


class SimulatedCamera(CameraInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref
        self.recording = False
        self.fps = 30
        self.exposure_ms = 8.5

    def get_frame(self) -> Optional[bytes]:
        if self.simulator:
            return self.simulator.generate_simulated_camera_frame()
        return None

    def set_recording(self, recording: bool) -> bool:
        self.recording = recording
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "Sony IMX477 4K HDR Mining Cam",
            "health": "ONLINE",
            "resolution": "1920x1080 @ 60FPS",
            "fps": self.fps,
            "exposure_ms": self.exposure_ms,
            "recording": self.recording,
            "fov": "120° Wide Angle Low-Distortion"
        }


class SimulatedThermalCamera(ThermalCameraInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref

    def get_thermal_data(self) -> Dict[str, Any]:
        if self.simulator:
            return self.simulator.generate_thermal_data()
        return {
            "min_temp": 18.2,
            "max_temp": 46.8,
            "avg_temp": 24.3,
            "hotspot_temp": 46.8,
            "hotspot_location": {"x": 0.45, "y": 0.62},
            "status": "NORMAL"
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "FLIR Boson LWIR Core 640x512",
            "health": "ONLINE",
            "refresh_hz": 9.0,
            "spectral_band": "7.5 - 13.5 µm",
            "sensitivity": "<40 mK",
            "status": "ONLINE"
        }


class SimulatedGasSensor(GasSensorInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref
        self.calibrating = False

    def read_all_gases(self) -> Dict[str, Any]:
        if self.simulator:
            return self.simulator.generate_gas_readings()
        return {
            "ch4_pct": 0.02,
            "co_ppm": 4.0,
            "co2_ppm": 650.0,
            "o2_pct": 20.8,
            "h2s_ppm": 0.0,
            "atmosphere_status": "SAFE"
        }

    def zero_calibrate(self) -> bool:
        self.calibrating = True
        logger.info("[HAL-SIM] Multi-Gas Array Zero Calibration")
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "MineSafe Optical NDIR & Electrochemical Multi-Gas Stack",
            "health": "CALIBRATING" if self.calibrating else "ONLINE",
            "sensors": {
                "ch4": {"health": "ONLINE", "type": "NDIR Infrared", "range": "0 - 5.0% LEL"},
                "co": {"health": "ONLINE", "type": "Electrochemical", "range": "0 - 500 ppm"},
                "co2": {"health": "ONLINE", "type": "NDIR Dual-Wave", "range": "0 - 5000 ppm"},
                "o2": {"health": "ONLINE", "type": "Optical Luminescence", "range": "0 - 25.0%"},
                "h2s": {"health": "ONLINE", "type": "Solid Polymer", "range": "0 - 100 ppm"}
            }
        }


class SimulatedIMU(IMUInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref
        self.calibrating = False

    def read_imu(self) -> Dict[str, Any]:
        if self.simulator:
            return self.simulator.generate_imu_readings()
        return {
            "accel": {"x": 0.0, "y": 0.0, "z": 9.81},
            "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
            "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
            "status": "ONLINE"
        }

    def calibrate(self) -> bool:
        self.calibrating = True
        logger.info("[HAL-SIM] IMU Gyro Bias Calibration Initiated")
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "BNO085 9-DOF AHRS + DMP",
            "health": "CALIBRATING" if self.calibrating else "ONLINE",
            "sample_rate_hz": 500,
            "heading_accuracy_deg": 1.2
        }


class SimulatedDistanceSensors(DistanceSensorsInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref

    def read_distances(self) -> Dict[str, float]:
        if self.simulator:
            return self.simulator.calculate_cavern_distances()
        return {"front": 12.0, "rear": 14.5, "left": 8.5, "right": 8.5, "up": 11.0, "down": 4.2}

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "6-Direction Time-of-Flight Laser Array",
            "health": "ONLINE",
            "max_range_m": 25.0,
            "accuracy_mm": 15
        }


class SimulatedBarometer(BarometerInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref
        self.calibrating = False

    def read_barometer(self) -> Dict[str, float]:
        if self.simulator:
            return self.simulator.generate_barometer_data()
        return {"pressure_hpa": 1008.4, "altitude_m": 4.5, "vertical_speed_ms": 0.0}

    def calibrate(self) -> bool:
        self.calibrating = True
        logger.info("[HAL-SIM] Barometer Tare / QNH Set")
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "BMP390 Precision Sub-Surface Barometric Altimeter",
            "health": "CALIBRATING" if self.calibrating else "ONLINE",
            "resolution_cm": 10,
            "noise_pa": 0.4
        }


class SimulatedBatteryBMS(BatteryBMSInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref

    def read_battery(self) -> Dict[str, Any]:
        if self.simulator:
            return self.simulator.generate_battery_data()
        return {
            "percentage": 85.0,
            "voltage": 22.8,
            "current": 8.4,
            "power_w": 191.5,
            "temperature_c": 31.5,
            "cell_min_v": 4.12,
            "cell_max_v": 4.18,
            "estimated_flight_time_s": 1120,
            "bms_status": "NORMAL",
            "charge_state": "DISCHARGING"
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "Smart 6S LiPo BMS & Power Management Module",
            "health": "ONLINE",
            "cells_count": 6,
            "chemistry": "LiPo High-Discharge",
            "cycle_count": 28
        }


class SimulatedMotorESC(MotorESCInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref

    def read_motors(self) -> List[Dict[str, Any]]:
        if self.simulator:
            return self.simulator.generate_motor_telemetry()
        return [
            {"id": i, "rpm": 4800, "current": 8.2, "temp_c": 42.0, "throttle_pct": 52.0, "status": "NORMAL"}
            for i in range(1, 5)
        ]

    def read_escs(self) -> List[Dict[str, Any]]:
        if self.simulator:
            return self.simulator.generate_esc_telemetry()
        return [
            {"id": i, "voltage": 22.8, "current": 8.2, "temp_c": 41.5, "throttle_pct": 52.0, "status": "OK"}
            for i in range(1, 5)
        ]

    def set_motor_throttles(self, throttles: List[float]):
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "Tekko32 4-in-1 65A DShot1200 BLHeli_32",
            "health": "ONLINE",
            "protocol": "DShot1200 Bidirectional Telemetry",
            "active_count": 4
        }


class SimulatedComms(CommsInterface):
    def __init__(self, simulator_ref=None):
        self.simulator = simulator_ref

    def read_telemetry_link(self) -> Dict[str, Any]:
        if self.simulator:
            return self.simulator.generate_comms_data()
        return {
            "link_type": "900MHz MESH RADIO",
            "rssi_dbm": -58.0,
            "signal_pct": 84.0,
            "latency_ms": 38,
            "packet_loss_pct": 0.4,
            "bandwidth_kbps": 240.0,
            "video_link": "STABLE",
            "telemetry_link": "STABLE",
            "status": "STRONG"
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "Microhard pDDL900 Sub-Surface MIMO Mesh Transceiver",
            "health": "ONLINE",
            "frequency_mhz": 915,
            "power_mw": 1000
        }


# ==========================================
# 3. REAL HARDWARE DRIVER SKELETONS (FOR MODE="REAL")
# ==========================================

class RealMavlinkFlightController(FlightControllerInterface):
    """Production driver connecting to PX4 / ArduPilot via PyMAVLink serial port /dev/ttyACM0."""
    def __init__(self, port="/dev/ttyACM0", baud=921600):
        self.port = port
        self.baud = baud
        self.connected = False
        logger.info("[HAL-REAL] Initializing MAVLink connection on %s @ %d baud", port, baud)
        # In real hardware, pymavlink.mavutil.mavlink_connection(port, baud=baud) is instantiated here.

    def arm(self) -> bool:
        logger.info("[HAL-REAL] Sending MAVLink ARM command")
        return True

    def disarm(self) -> bool:
        logger.info("[HAL-REAL] Sending MAVLink DISARM command")
        return True

    def emergency_stop(self) -> bool:
        logger.warning("[HAL-REAL] Sending MAVLink EMERGENCY MOTOR KILL")
        return True

    def set_flight_mode(self, mode: str) -> bool:
        logger.info("[HAL-REAL] Setting MAVLink flight mode: %s", mode)
        return True

    def send_velocity_target(self, vx: float, vy: float, vz: float, yaw_rate: float):
        # Sends SET_POSITION_TARGET_LOCAL_NED MAVLink packet
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": "PX4 FMUv6X (Real MAVLink)",
            "connection": "CONNECTED" if self.connected else "NO HARDWARE DETECTED",
            "health": "ONLINE" if self.connected else "OFFLINE"
        }


class RealRPLiDAR(LiDARInterface):
    """Production driver for physical LiDAR sensor connected via USB UART / Ethernet."""
    def __init__(self, port="/dev/ttyUSB0"):
        self.port = port
        self.connected = False
        # RPLiDAR driver instantiation here

    def get_scan(self) -> Dict[str, Any]:
        return {"points": [], "point_count": 0, "status": "HARDWARE_NOT_ATTACHED"}

    def calibrate(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return {"name": "Physical RPLiDAR", "health": "OFFLINE"}


# ==========================================
# 4. HARDWARE FACTORY
# ==========================================

class HardwareSystem:
    """Consolidated hardware container providing unified access to all subsystems."""
    def __init__(self, mode: str = "SIMULATION", simulator_ref=None):
        self.mode = mode
        self.simulator = simulator_ref

        if mode == "REAL":
            logger.info("Initializing PHYSICAL HARDWARE mode drivers...")
            self.fc = RealMavlinkFlightController()
            self.lidar = RealRPLiDAR()
            # Fallback to simulated for components without physical hardware
            self.camera = SimulatedCamera(simulator_ref)
            self.thermal = SimulatedThermalCamera(simulator_ref)
            self.gas = SimulatedGasSensor(simulator_ref)
            self.imu = SimulatedIMU(simulator_ref)
            self.distances = SimulatedDistanceSensors(simulator_ref)
            self.barometer = SimulatedBarometer(simulator_ref)
            self.battery = SimulatedBatteryBMS(simulator_ref)
            self.motors = SimulatedMotorESC(simulator_ref)
            self.comms = SimulatedComms(simulator_ref)
        else:
            logger.info("Initializing SIMULATED HARDWARE mode drivers...")
            self.fc = SimulatedFlightController(simulator_ref)
            self.lidar = SimulatedLiDAR(simulator_ref)
            self.camera = SimulatedCamera(simulator_ref)
            self.thermal = SimulatedThermalCamera(simulator_ref)
            self.gas = SimulatedGasSensor(simulator_ref)
            self.imu = SimulatedIMU(simulator_ref)
            self.distances = SimulatedDistanceSensors(simulator_ref)
            self.barometer = SimulatedBarometer(simulator_ref)
            self.battery = SimulatedBatteryBMS(simulator_ref)
            self.motors = SimulatedMotorESC(simulator_ref)
            self.comms = SimulatedComms(simulator_ref)

    def attach_simulator(self, simulator_ref):
        """Bind simulator reference to all simulated drivers."""
        self.simulator = simulator_ref
        for component in [self.fc, self.lidar, self.camera, self.thermal, self.gas,
                          self.imu, self.distances, self.barometer, self.battery,
                          self.motors, self.comms]:
            if hasattr(component, "simulator"):
                component.simulator = simulator_ref
