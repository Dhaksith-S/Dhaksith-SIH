"""
MINE-X DRONE COMMAND - Physics & Multi-Sensor Simulation Engine
Simulates 3D mine aerodynamics, LiDAR scanning, thermal imaging,
atmospheric gas dispersion, IMU dynamics, battery drain, and RF communications.
"""

import math
import random
import time
import io
import base64
from typing import Dict, Any, List, Tuple
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from .config import DRONE_PARAMS, MINE_BOUNDS, MINE_STATIONS, SAFETY_THRESHOLDS

class CavernGeometry:
    """Mathematical spline model of the underground mine cavern network."""
    def __init__(self):
        # Centerline control nodes along the 240m mine tunnel
        self.nodes = [
            np.array([0.0, 4.0, 35.0]),     # 0: Portal mouth (surface entrance)
            np.array([0.0, 5.0, 5.0]),      # 1: Throat
            np.array([10.0, 6.5, -30.0]),   # 2: Western bend
            np.array([-14.0, 9.5, -72.0]),  # 3: Grand Extraction Stope (expanded dome)
            np.array([16.0, 8.0, -118.0]),  # 4: North-East Ore Chute
            np.array([-5.0, 4.5, -160.0]),  # 5: Deep Abyss Winze Shaft
            np.array([0.0, 1.5, -205.0])    # 6: Deep Sump terminus
        ]

    def get_closest_centerline_point(self, pos: np.ndarray) -> Tuple[np.ndarray, float]:
        """Find closest point on the centerline spline and return distance and local radius."""
        z = pos[2]
        # Linear interpolation between nodes based on Z
        best_pt = self.nodes[0]
        for i in range(len(self.nodes) - 1):
            n1 = self.nodes[i]
            n2 = self.nodes[i+1]
            if (n1[2] >= z >= n2[2]) or (n2[2] >= z >= n1[2]):
                t = (z - n1[2]) / (n2[2] - n1[2] + 1e-6)
                t = max(0.0, min(1.0, t))
                best_pt = n1 + t * (n2 - n1)
                break
            elif z > self.nodes[0][2]:
                best_pt = self.nodes[0]
            elif z < self.nodes[-1][2]:
                best_pt = self.nodes[-1]

        # Cavern radius expansion in Grand Stope (Z: -45 to -100)
        radius = 17.0
        if -100.0 <= z <= -45.0:
            expansion = 1.55 + math.sin((z + 45.0) / 55.0 * math.pi) * 0.85
            radius = 17.0 * expansion

        return best_pt, radius


class MineSimulator:
    """High-fidelity simulation engine for the MINE-X drone."""
    def __init__(self):
        self.cavern = CavernGeometry()
        
        # Drone physical state
        # Initial position inside portal mouth
        self.x = 0.0
        self.y = 4.5
        self.z = 25.0
        
        # Velocities
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        
        # Command velocity targets
        self.cmd_vx = 0.0
        self.cmd_vy = 0.0
        self.cmd_vz = 0.0
        self.cmd_yaw_rate = 0.0
        
        # Orientation (Euler degrees)
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 180.0  # Facing into the cavern (negative Z)
        
        # Accelerations
        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0
        
        # Flight state
        self.armed = False
        self.flight_mode = "MANUAL"
        self.speed_multiplier = 1.0  # 1.0 normal, 1.8 shift boost, 0.35 ctrl slow
        
        # Battery state
        self.battery_pct = 86.5
        self.battery_voltage = 22.8
        self.battery_current = 1.8  # Idle current
        self.battery_temp = 29.5
        
        # Motor RPMs and ESC states
        self.motor_rpms = [0.0, 0.0, 0.0, 0.0]
        self.motor_temps = [28.0, 28.0, 28.0, 28.0]
        self.esc_temps = [27.0, 27.0, 27.0, 27.0]
        self.motor_throttles = [0.0, 0.0, 0.0, 0.0]
        
        # Simulation clock
        self.last_update_time = time.time()
        self.start_time = time.time()
        self.total_distance_m = 0.0
        
        # Spherical Cage Geometry & Motion Modes
        self.cage_radius = 1.35
        self.ground_y = 1.35
        self.ground_contact = True
        self.motion_mode = "DISARMED"
        self.target_hover_y = None

        # Calibrations status
        self.calibrations = {
            "imu": False,
            "lidar": False,
            "barometer": False,
            "gas": False,
            "camera": False
        }

    def set_command_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float):
        """Set commanded target velocities from keyboard or autonomous planner."""
        self.cmd_vx = vx * self.speed_multiplier
        self.cmd_vy = vy * self.speed_multiplier
        self.cmd_vz = vz * self.speed_multiplier
        self.cmd_yaw_rate = yaw_rate * self.speed_multiplier

    def update_physics(self, dt: float):
        """Run kinematic and dynamic integration for spherical cage drone."""
        if not self.armed:
            # When disarmed, settle down to floor gently or stay rested
            self.cmd_vx = 0.0
            self.cmd_vy = 0.0
            self.cmd_vz = 0.0
            self.cmd_yaw_rate = 0.0
            self.target_hover_y = None
            
            # Floor level is y=1.35 (cage radius 1.35m resting on floor y=0)
            if self.y > self.ground_y:
                self.vy = max(-2.0, self.vy - 4.5 * dt)
                self.y = max(self.ground_y, self.y + self.vy * dt)
            else:
                self.vy = 0.0
                self.y = self.ground_y
            
            self.vx *= 0.8
            self.vz *= 0.8
            self.roll *= 0.85
            self.pitch *= 0.85
            self.ground_contact = True
            self.motion_mode = "EMERGENCY" if self.flight_mode == "EMERGENCY" else "DISARMED"
            
            # Motors off when disarmed
            for i in range(4):
                self.motor_rpms[i] = max(0.0, self.motor_rpms[i] - 1500 * dt)
                self.motor_throttles[i] = 0.0
                self.motor_temps[i] = max(24.0, self.motor_temps[i] - 0.05 * dt)
            
            self.battery_current = 1.2
            return

        # Smooth velocity acceleration toward commanded values
        accel = DRONE_PARAMS["acceleration"]
        decel = DRONE_PARAMS["deceleration"]

        def approach(curr, target, rate_up, rate_down):
            if abs(target) > abs(curr):
                step = rate_up * dt
                return curr + math.copysign(min(abs(target - curr), step), target - curr)
            else:
                step = rate_down * dt
                return curr + math.copysign(min(abs(target - curr), step), target - curr)

        self.vx = approach(self.vx, self.cmd_vx, accel, decel)
        self.vy = approach(self.vy, self.cmd_vy, accel, decel)
        self.vz = approach(self.vz, self.cmd_vz, accel, decel)

        # Yaw rotation
        self.yaw = (self.yaw + self.cmd_yaw_rate * (180.0 / math.pi) * dt) % 360.0

        # Dynamic roll and pitch response based on planar acceleration & velocity
        # Transform velocity to local body frame to calculate banking tilt
        yaw_rad = math.radians(self.yaw)
        # In our coordinate system:
        # Forward in local body translates into world delta X & delta Z
        forward_v = - (self.vz * math.cos(yaw_rad) + self.vx * math.sin(yaw_rad))
        lateral_v = (-self.vz * math.sin(yaw_rad) + self.vx * math.cos(yaw_rad))

        target_pitch = forward_v * 4.2  # Tilts nose down when moving forward
        target_roll = lateral_v * 4.2   # Banks right/left
        
        self.pitch += (target_pitch - self.pitch) * min(1.0, 8.0 * dt)
        self.roll += (target_roll - self.roll) * min(1.0, 8.0 * dt)

        # Update position
        dx = self.vx * dt
        dy = self.vy * dt
        dz = self.vz * dt
        
        self.x += dx
        self.y += dy
        self.z += dz

        # Accumulate odometer
        speed_3d = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)
        self.total_distance_m += speed_3d * dt

        # Cavern Boundary & Collision Clamping
        center_pt, cavern_r = self.cavern.get_closest_centerline_point(np.array([self.x, self.y, self.z]))
        dist_from_center = math.sqrt((self.x - center_pt[0])**2 + (self.y - center_pt[1])**2)
        safe_r = max(2.0, cavern_r - 1.2)  # 1.2m buffer from rock wall
        
        if dist_from_center > safe_r:
            # Soft wall repulsion bounce
            angle = math.atan2(self.y - center_pt[1], self.x - center_pt[0])
            self.x = center_pt[0] + math.cos(angle) * safe_r
            self.y = center_pt[1] + math.sin(angle) * safe_r
            self.vx *= -0.3
            self.vy *= -0.3

        # Ground Floor Clamp & Touchdown logic
        if self.y <= self.ground_y:
            self.y = self.ground_y
            self.vy = max(0.0, self.vy)
            if self.flight_mode == "LAND":
                self.flight_mode = "MANUAL"
                self.cmd_vy = 0.0

        # Handle smooth takeoff ascent
        if self.target_hover_y is not None:
            if self.y >= self.target_hover_y:
                self.cmd_vy = 0.0
                self.target_hover_y = None

        # Determine distinct motion mode
        speed_h = math.sqrt(self.vx**2 + self.vz**2)
        self.ground_contact = (self.y <= (self.ground_y + 0.05))

        if not self.armed:
            self.motion_mode = "EMERGENCY" if self.flight_mode == "EMERGENCY" else "DISARMED"
        elif self.ground_contact:
            if speed_h > 0.05:
                self.motion_mode = "GROUND_ROLLING"
            else:
                self.motion_mode = "GROUND_REST"
        elif self.flight_mode == "LAND" and self.vy < -0.1:
            self.motion_mode = "LANDING"
        elif self.target_hover_y is not None or (self.vy > 0.2 and self.y < 3.2):
            self.motion_mode = "TAKEOFF"
        else:
            self.motion_mode = "FLIGHT"

        # Ceiling Clamp
        if self.y > 27.5:
            self.y = 27.5
            self.vy = min(0.0, self.vy)

        # Z Clamps (Portal mouth to Deep Winze Terminus)
        if self.z > 36.0:
            self.z = 36.0
            self.vz = min(0.0, self.vz)
        elif self.z < -202.0:
            self.z = -202.0
            self.vz = max(0.0, self.vz)

        # Calculate Motor RPMs & Throttles
        if self.ground_contact:
            # On ground, ground drive mechanism moves drone; props idle or stop
            base_throttle = 8.0 if speed_h > 0.05 else 0.0
        else:
            hover_throttle = DRONE_PARAMS["hover_throttle_pct"]
            throttle_mod = (self.vy * 8.0) + (speed_3d * 3.5)
            base_throttle = max(15.0, min(95.0, hover_throttle + throttle_mod))
        
        # Differential motor throttles for roll/pitch/yaw
        pitch_diff = self.pitch * 0.4 if not self.ground_contact else 0.0
        roll_diff = self.roll * 0.4 if not self.ground_contact else 0.0
        yaw_diff = self.cmd_yaw_rate * 8.0

        t1 = max(10.0, min(100.0, base_throttle + pitch_diff - roll_diff + yaw_diff))
        t2 = max(10.0, min(100.0, base_throttle + pitch_diff + roll_diff - yaw_diff))
        t3 = max(10.0, min(100.0, base_throttle - pitch_diff - roll_diff - yaw_diff))
        t4 = max(10.0, min(100.0, base_throttle - pitch_diff + roll_diff + yaw_diff))

        throttles = [t1, t2, t3, t4]
        for i in range(4):
            self.motor_throttles[i] = throttles[i]
            target_rpm = throttles[i] * 92.0 + random.uniform(-15, 15)
            self.motor_rpms[i] += (target_rpm - self.motor_rpms[i]) * min(1.0, 15.0 * dt)
            
            # Motor temperatures rise with throttle
            heat_gen = (throttles[i] / 100.0) * 0.12 * dt
            cooling = (self.motor_temps[i] - 22.0) * 0.02 * dt
            self.motor_temps[i] = max(22.0, min(85.0, self.motor_temps[i] + heat_gen - cooling))
            self.esc_temps[i] = self.motor_temps[i] * 0.94

        # Battery Drain Model
        total_throttle = sum(self.motor_throttles) / 4.0
        current_draw = 2.0 + (total_throttle / 100.0) * 22.0  # Amps
        self.battery_current = current_draw
        drain_rate = (current_draw / 30.0) * DRONE_PARAMS["battery_drain_rate_active"] * dt
        self.battery_pct = max(0.0, self.battery_pct - drain_rate)
        
        # Voltage drop based on battery percentage & current sag
        nom_v = 19.8 + (self.battery_pct / 100.0) * (25.2 - 19.8)
        sag = current_draw * 0.035
        self.battery_voltage = max(18.0, nom_v - sag)
        self.battery_temp = max(22.0, 24.0 + (current_draw / 25.0) * 14.0)

    def calculate_cavern_distances(self) -> Dict[str, float]:
        """Compute raycast distance to walls, roof, and floor."""
        center_pt, radius = self.cavern.get_closest_centerline_point(np.array([self.x, self.y, self.z]))
        
        # Down distance to floor
        down_dist = max(0.05, self.y - 0.0)
        
        # Up distance to vaulted roof
        roof_y = center_pt[1] + radius * 0.95
        up_dist = max(0.2, roof_y - self.y)
        
        # Left and Right distances from current X to cavern walls
        left_wall_x = center_pt[0] - radius
        right_wall_x = center_pt[0] + radius
        left_dist = max(0.2, self.x - left_wall_x)
        right_dist = max(0.2, right_wall_x - self.x)
        
        # Front and Rear distances along tunnel corridor
        # Add rock boulders / timber archways as obstacle intercepts
        front_dist = 18.5 + math.sin(self.z * 0.2) * 4.0
        rear_dist = 14.2 + math.cos(self.z * 0.15) * 3.5

        # In tight timber zones (e.g. Z around -25, -48, -98), clearance narrows
        for tz in [18, -4, -25, -48, -98, -125]:
            if abs(self.z - tz) < 2.5:
                left_dist = min(left_dist, 5.5 + abs(self.x - center_pt[0]))
                right_dist = min(right_dist, 5.5 + abs(self.x - center_pt[0]))
                up_dist = min(up_dist, 6.0)

        return {
            "front": round(max(0.4, front_dist), 2),
            "rear": round(max(0.4, rear_dist), 2),
            "left": round(max(0.4, left_dist), 2),
            "right": round(max(0.4, right_dist), 2),
            "up": round(max(0.4, up_dist), 2),
            "down": round(max(0.05, down_dist), 2)
        }

    def generate_gas_readings(self) -> Dict[str, Any]:
        """Simulate realistic mine atmospheric gas dispersion by depth & sector."""
        z = self.z
        
        # Methane CH4: Highest in unventilated Deep Abyss Winze Shaft (Z < -135)
        ch4_base = 0.02
        if z < -130:
            depth_factor = min(1.0, (-130 - z) / 60.0)
            ch4_base = 0.04 + depth_factor * 0.48  # Rises up to 0.52%
        elif -100 <= z <= -50:
            ch4_base = 0.05  # Moderate in Great Stope dome pocket
        ch4 = max(0.01, ch4_base + random.uniform(-0.008, 0.008))

        # Carbon Monoxide CO: Blast residue near Ore Chute (Z ~ -118)
        co_base = 3.0
        if -130 <= z <= -100:
            co_base = 18.0 + math.sin((z + 100) / 30.0 * math.pi) * 14.0
        elif z < -130:
            co_base = 12.0
        co = max(1.0, co_base + random.uniform(-1.2, 1.2))

        # Carbon Dioxide CO2: Base 500 ppm, accumulates in stagnant sumps
        co2_base = 520.0
        if z < -60:
            co2_base = 520.0 + min(900.0, (-60 - z) * 6.5)
        co2 = max(420.0, co2_base + random.uniform(-25.0, 25.0))

        # Oxygen O2: Safe 20.9% near portal, drops slightly in deep winze
        o2_base = 20.9
        if z < -120:
            o2_base = 20.9 - min(2.5, (-120 - z) * 0.028)
        o2 = max(17.8, min(20.95, o2_base + random.uniform(-0.06, 0.06)))

        # Hydrogen Sulfide H2S: Damp mineralized sump basin at Z < -155
        h2s_base = 0.0
        if z < -150:
            h2s_base = min(7.5, (-150 - z) * 0.15)
        h2s = max(0.0, h2s_base + random.uniform(-0.3, 0.3))

        # Safety classification
        status = "SAFE"
        if ch4 >= SAFETY_THRESHOLDS["ch4_critical_pct"] or o2 <= SAFETY_THRESHOLDS["o2_critical_pct"]:
            status = "CRITICAL HAZARD"
        elif ch4 >= SAFETY_THRESHOLDS["ch4_warning_pct"] or co >= SAFETY_THRESHOLDS["co_warning_ppm"]:
            status = "WARNING"

        return {
            "ch4_pct": round(ch4, 3),
            "co_ppm": round(co, 1),
            "co2_ppm": round(co2, 0),
            "o2_pct": round(o2, 1),
            "h2s_ppm": round(h2s, 1),
            "atmosphere_status": status,
            "is_simulation": True
        }

    def generate_thermal_data(self) -> Dict[str, Any]:
        """Simulate infrared radiometric matrix with motor heat and geological fissures."""
        # Baseline rock ambient temp
        base_ambient = 19.5 + min(12.0, max(0.0, -self.z * 0.06))
        
        # Geothermal hotspot near Great Stope (Z ~ -72)
        hotspot_temp = base_ambient + 4.0
        hotspot_loc = {"x": 0.5, "y": 0.5}
        
        if -85 <= self.z <= -60:
            hotspot_temp = 58.4 + math.sin((self.z + 60) / 25.0 * math.pi) * 12.0
            hotspot_loc = {"x": 0.62, "y": 0.42}
        elif self.z < -150:
            hotspot_temp = 48.0 + random.uniform(-2, 3)
            hotspot_loc = {"x": 0.38, "y": 0.71}

        # Drone's own motor heat
        max_motor_temp = max(self.motor_temps)
        if max_motor_temp > hotspot_temp:
            hotspot_temp = max_motor_temp

        status = "NORMAL"
        if hotspot_temp >= SAFETY_THRESHOLDS["temp_critical_c"]:
            status = "HOTSPOT CRITICAL"
        elif hotspot_temp >= SAFETY_THRESHOLDS["temp_warning_c"]:
            status = "HOTSPOT WARNING"

        return {
            "min_temp": round(base_ambient - 2.5, 1),
            "max_temp": round(hotspot_temp, 1),
            "avg_temp": round(base_ambient + 3.2, 1),
            "hotspot_temp": round(hotspot_temp, 1),
            "hotspot_location": hotspot_loc,
            "status": status
        }

    def generate_imu_readings(self) -> Dict[str, Any]:
        """Simulate 9-DOF IMU accelerometer, gyro, and roll/pitch/yaw."""
        # Motor vibration harmonics noise
        vib = 0.08 if self.armed else 0.01
        
        acc_x = (self.ax / 9.81) + random.gauss(0, vib)
        acc_y = (self.ay / 9.81) + random.gauss(0, vib)
        acc_z = 1.0 + (self.az / 9.81) + random.gauss(0, vib)

        gyro_x = math.radians(self.roll * 0.5) + random.gauss(0, vib * 0.5)
        gyro_y = math.radians(self.pitch * 0.5) + random.gauss(0, vib * 0.5)
        gyro_z = self.cmd_yaw_rate + random.gauss(0, vib * 0.3)

        return {
            "accel": {"x": round(acc_x, 3), "y": round(acc_y, 3), "z": round(acc_z, 3)},
            "gyro": {"x": round(gyro_x, 3), "y": round(gyro_y, 3), "z": round(gyro_z, 3)},
            "roll": round(self.roll, 1),
            "pitch": round(self.pitch, 1),
            "yaw": round(self.yaw, 1),
            "status": "ONLINE"
        }

    def generate_barometer_data(self) -> Dict[str, float]:
        """Atmospheric pressure & vertical speed derived from elevation."""
        # Surface QNH 1013.25 hPa; underground pressure increases with depth
        # ~1 hPa per 8.5m descent
        depth_m = max(0.0, -self.z)
        pressure = 1013.25 + (depth_m / 8.5) - (self.y / 8.5)
        return {
            "pressure_hpa": round(pressure + random.uniform(-0.15, 0.15), 1),
            "altitude_m": round(self.y, 2),
            "vertical_speed_ms": round(self.vy, 2)
        }

    def generate_gnss_data(self) -> Dict[str, Any]:
        """Simulate GNSS availability: acquired near portal, lost underground."""
        is_surface = (self.z >= 18.0 and self.y >= 3.0)
        
        if is_surface:
            return {
                "status": "SURFACE AVAILABLE",
                "fix": "3D RTK FIX",
                "satellites": 16,
                "hdop": 0.8,
                "latitude": 34.052230 + (self.x * 0.00001),
                "longitude": -118.243680 + (self.z * 0.00001),
                "altitude_m": 48.5 + self.y
            }
        else:
            return {
                "status": "UNDERGROUND UNAVAILABLE",
                "fix": "NO FIX (SHIELDED ROCK)",
                "satellites": 0,
                "hdop": 99.9,
                "latitude": None,
                "longitude": None,
                "altitude_m": self.y
            }

    def generate_battery_data(self) -> Dict[str, Any]:
        """Generate detailed smart BMS data."""
        # 6S cell balance
        cells = []
        cell_nom = self.battery_voltage / 6.0
        for i in range(6):
            c_val = cell_nom + random.uniform(-0.02, 0.02)
            cells.append(round(c_val, 3))
            
        power_w = round(self.battery_voltage * self.battery_current, 1)
        est_flight_s = 0
        if self.battery_current > 0.5:
            remaining_ah = (self.battery_pct / 100.0) * (DRONE_PARAMS["battery_capacity_mah"] / 1000.0)
            est_flight_s = int((remaining_ah / self.battery_current) * 3600)

        return {
            "percentage": round(self.battery_pct, 1),
            "voltage": round(self.battery_voltage, 2),
            "current": round(self.battery_current, 1),
            "power_w": power_w,
            "temperature_c": round(self.battery_temp, 1),
            "cells": cells,
            "cell_min_v": min(cells),
            "cell_max_v": max(cells),
            "estimated_flight_time_s": est_flight_s,
            "bms_status": "NORMAL" if self.battery_pct > 20 else "LOW VOLTAGE",
            "charge_state": "DISCHARGING" if self.armed else "STANDBY"
        }

    def generate_motor_telemetry(self) -> List[Dict[str, Any]]:
        """Return 4-motor telemetry."""
        return [
            {
                "id": i + 1,
                "rpm": int(self.motor_rpms[i]),
                "current": round((self.motor_throttles[i] / 100.0) * 6.5 + 0.4, 1),
                "temp_c": round(self.motor_temps[i], 1),
                "throttle_pct": round(self.motor_throttles[i], 1),
                "status": "NORMAL" if self.motor_temps[i] < SAFETY_THRESHOLDS["motor_temp_max_c"] else "WARNING"
            }
            for i in range(4)
        ]

    def generate_esc_telemetry(self) -> List[Dict[str, Any]]:
        """Return 4-ESC telemetry."""
        return [
            {
                "id": i + 1,
                "voltage": round(self.battery_voltage, 2),
                "current": round((self.motor_throttles[i] / 100.0) * 6.5 + 0.4, 1),
                "temp_c": round(self.esc_temps[i], 1),
                "throttle_pct": round(self.motor_throttles[i], 1),
                "status": "OK" if self.esc_temps[i] < SAFETY_THRESHOLDS["esc_temp_max_c"] else "OVERHEAT"
            }
            for i in range(4)
        ]

    def generate_comms_data(self) -> Dict[str, Any]:
        """Subterranean mesh radio attenuation with tunnel distance."""
        dist_from_portal = max(0.0, 25.0 - self.z)
        
        # RSSI decays with depth in rock
        base_rssi = -42.0 - (dist_from_portal * 0.18)
        rssi = max(-92.0, base_rssi + random.uniform(-1.5, 1.5))
        
        latency = 28 + int(dist_from_portal * 0.22) + random.randint(0, 4)
        pkt_loss = min(12.0, 0.2 + (dist_from_portal * 0.015))
        
        status = "STABLE"
        if rssi < SAFETY_THRESHOLDS["rssi_critical_dbm"]:
            status = "CRITICAL (RELAY RECOMMENDED)"
        elif rssi < SAFETY_THRESHOLDS["rssi_weak_dbm"]:
            status = "WEAK SIGNAL"

        return {
            "link_type": "SUB-SURFACE 900MHz MESH",
            "rssi_dbm": round(rssi, 1),
            "latency_ms": latency,
            "packet_loss_pct": round(pkt_loss, 2),
            "video_link": "STABLE" if rssi > -80 else "DEGRADED",
            "telemetry_link": "ONLINE",
            "status": status
        }

    def generate_power_rails(self) -> Dict[str, Any]:
        """Power Distribution Board (PDB) diagnostic rails."""
        return {
            "v_main": round(self.battery_voltage, 2),
            "i_main": round(self.battery_current, 1),
            "rail_5v": round(5.02 + random.uniform(-0.02, 0.02), 2),
            "rail_12v": round(12.04 + random.uniform(-0.03, 0.03), 2),
            "rail_24v": round(self.battery_voltage * 0.99, 2),
            "pdb_temp_c": round(32.4 + (self.battery_current / 25.0) * 8.0, 1),
            "regulator_status": "NORMAL"
        }

    def generate_onboard_computer_status(self) -> Dict[str, Any]:
        """Onboard companion computer (Nvidia Jetson Orin / Raspberry Pi 5)."""
        cpu_load = 38.0 + (15.0 if self.armed else 0.0) + random.uniform(-2.5, 2.5)
        ram_load = 58.4
        gpu_load = 42.0 + (22.0 if self.armed else 0.0) + random.uniform(-4.0, 4.0)
        temp = 48.0 + (cpu_load * 0.12)
        return {
            "model": "Nvidia Jetson Orin NX 16GB",
            "cpu_pct": round(cpu_load, 1),
            "ram_pct": round(ram_load, 1),
            "gpu_pct": round(gpu_load, 1),
            "temp_c": round(temp, 1),
            "storage_used_pct": 54.2,
            "esp32_coprocessor": "CONNECTED (SPI 10MHz)",
            "status": "NOMINAL"
        }

    def generate_lidar_scan(self) -> Dict[str, Any]:
        """Generate LiDAR metadata and current point count."""
        return {
            "status": "ONLINE",
            "scan_rate_hz": 20.0,
            "points_sec": 128000,
            "range_m": 40.0,
            "point_count": 22000,
            "scan_quality_pct": 98.8,
            "connection": "CONNECTED (Gigabit Ethernet)"
        }

    def generate_simulated_camera_frame(self) -> str:
        """Create a synthetic RGB camera frame with HUD overlay and return base64 JPEG."""
        if not HAS_CV2:
            return ""
        
        w, h = 320, 240
        # Dark subterranean rock gradient backdrop
        img = np.zeros((h, w, 3), dtype=np.uint8)
        # Cavern ambient darkness with slight red-brown terracotta tint
        img[:, :] = (15, 20, 32)
        
        # Simulate tunnel crosshair & horizon
        cv2.line(img, (w//2 - 20, h//2), (w//2 + 20, h//2), (0, 215, 255), 1)
        cv2.line(img, (w//2, h//2 - 20), (w//2, h//2 + 20), (0, 215, 255), 1)
        
        # Flight telemetry text
        font = cv2.FONT_HERSHEY_PLAIN
        cv2.putText(img, f"ALT: {self.y:.1f}m", (10, 20), font, 0.9, (0, 255, 200), 1)
        cv2.putText(img, f"HDG: {int(self.yaw)}", (w - 75, 20), font, 0.9, (0, 255, 200), 1)
        cv2.putText(img, f"SPD: {math.sqrt(self.vx**2+self.vz**2):.1f}m/s", (10, h - 15), font, 0.9, (0, 215, 255), 1)
        cv2.putText(img, "CAM-1 RGB [SIM]", (w - 110, h - 15), font, 0.8, (120, 120, 120), 1)
        
        _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
        return base64.b64encode(buf).decode('utf-8')
