"""
MINE-X DRONE COMMAND - Central Drone Controller
Processes operator keyboard commands, manages flight modes,
coordinates kinematics with the Hardware Abstraction Layer, and executes autonomous missions.
"""

import math
import time
import logging
from typing import Dict, Any, List, Optional
from .config import DRONE_PARAMS, MINE_STATIONS
from .simulator import MineSimulator
from .hardware import HardwareSystem

logger = logging.getLogger("DroneController")

class DroneController:
    """Central controller directing drone movement, state transitions, and failsafes."""
    def __init__(self, simulator: MineSimulator, hardware: HardwareSystem):
        self.sim = simulator
        self.hw = hardware
        
        # Flight state
        self.armed = False
        self.flight_mode = "MANUAL"
        self.speed_mode = "NORMAL"  # "NORMAL", "BOOST", "PRECISION"
        
        # Key states held
        self.keys_pressed = {
            "w": False, "s": False, "a": False, "d": False,
            "q": False, "e": False, "r": False, "f": False,
            "shift": False, "ctrl": False
        }
        
        # Mission Planner
        self.mission_active = False
        self.mission_paused = False
        self.current_waypoint_idx = 0
        self.waypoints = [s["coords"] for s in MINE_STATIONS]
        self.mission_start_time = None
        self.rth_active = False
        
        # Active fault latch (for Emergency stop or critical safety failsafe)
        self.active_fault = None

    def handle_command(self, cmd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch incoming JSON command."""
        cmd = cmd_data.get("command", "").upper()
        
        if cmd == "KEY_DOWN":
            key = cmd_data.get("key", "").lower()
            if key in self.keys_pressed:
                self.keys_pressed[key] = True
            if key == "shift":
                self.speed_mode = "BOOST"
                self.sim.speed_multiplier = DRONE_PARAMS["boost_multiplier"]
            elif key == "control" or key == "ctrl":
                self.speed_mode = "PRECISION"
                self.sim.speed_multiplier = DRONE_PARAMS["precision_multiplier"]
            self._update_keyboard_velocities()
            return {"status": "OK", "action": f"KEY_DOWN_{key}"}

        elif cmd == "KEY_UP":
            key = cmd_data.get("key", "").lower()
            if key in self.keys_pressed:
                self.keys_pressed[key] = False
            if key == "shift" or key == "control" or key == "ctrl":
                self.speed_mode = "NORMAL"
                self.sim.speed_multiplier = 1.0
            self._update_keyboard_velocities()
            return {"status": "OK", "action": f"KEY_UP_{key}"}

        elif cmd == "MOVE_FORWARD":
            self.keys_pressed["w"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "MOVE_FORWARD"}

        elif cmd == "MOVE_BACKWARD":
            self.keys_pressed["s"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "MOVE_BACKWARD"}

        elif cmd == "MOVE_LEFT":
            self.keys_pressed["a"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "MOVE_LEFT"}

        elif cmd == "MOVE_RIGHT":
            self.keys_pressed["d"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "MOVE_RIGHT"}

        elif cmd == "MOVE_UP":
            self.keys_pressed["r"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "MOVE_UP"}

        elif cmd == "MOVE_DOWN":
            self.keys_pressed["f"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "MOVE_DOWN"}

        elif cmd == "ROTATE_LEFT":
            self.keys_pressed["q"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "ROTATE_LEFT"}

        elif cmd == "ROTATE_RIGHT":
            self.keys_pressed["e"] = True
            self._update_keyboard_velocities()
            return {"status": "OK", "action": "ROTATE_RIGHT"}

        elif cmd == "STOP_MOTION":
            for k in self.keys_pressed:
                if k not in ["shift", "ctrl"]:
                    self.keys_pressed[k] = False
            self.sim.set_command_velocity(0, 0, 0, 0)
            return {"status": "OK", "action": "STOP_MOTION"}

        elif cmd == "ARM":
            self.armed = True
            self.sim.armed = True
            self.active_fault = None
            if self.flight_mode == "EMERGENCY":
                self.flight_mode = "MANUAL"
                self.sim.flight_mode = "MANUAL"
            if self.sim.y <= 1.5:
                # Smooth takeoff lift off to hover altitude
                self.sim.target_hover_y = 3.5
                self.sim.cmd_vy = 1.6
            self.hw.fc.arm()
            logger.info("Drone ARMED by operator and initiated smooth takeoff")
            return {"status": "OK", "armed": True}

        elif cmd == "TAKEOFF":
            self.armed = True
            self.sim.armed = True
            self.active_fault = None
            if self.flight_mode == "EMERGENCY":
                self.flight_mode = "MANUAL"
                self.sim.flight_mode = "MANUAL"
            self.sim.target_hover_y = 3.5
            self.sim.cmd_vy = 1.6
            self.hw.fc.arm()
            logger.info("Drone TAKEOFF commanded - climbing to 3.5m hover")
            return {"status": "OK", "action": "TAKEOFF", "armed": True}

        elif cmd == "DISARM":
            self.armed = False
            self.sim.armed = False
            self.hw.fc.disarm()
            logger.info("Drone DISARMED by operator")
            return {"status": "OK", "armed": False}

        elif cmd == "EMERGENCY_STOP" or cmd == "ESTOP":
            self.armed = False
            self.sim.armed = False
            self.flight_mode = "EMERGENCY"
            self.sim.flight_mode = "EMERGENCY"
            self.sim.vx = 0.0
            self.sim.vy = 0.0
            self.sim.vz = 0.0
            self.sim.set_command_velocity(0, 0, 0, 0)
            self.hw.fc.emergency_stop()
            self.rth_active = False
            self.mission_active = False
            self.active_fault = {
                "active": True,
                "code": "EMERGENCY_STOP",
                "cause": "Operator Emergency Stop (Motors Killed)",
                "timestamp": time.strftime("%H:%M:%S"),
                "recovery_status": "Latched Disarm. Re-Arm or select mode to recover."
            }
            logger.critical("EMERGENCY STOP EXECUTED - MOTORS KILLED")
            return {"status": "OK", "action": "EMERGENCY_STOP", "armed": False, "fault": self.active_fault}

        elif cmd == "RESET_FAULT":
            self.active_fault = None
            if self.flight_mode == "EMERGENCY":
                self.flight_mode = "MANUAL"
                self.sim.flight_mode = "MANUAL"
            logger.info("Fault reset by operator")
            return {"status": "OK", "action": "RESET_FAULT"}

        elif cmd == "SET_MODE":
            mode = cmd_data.get("mode", "MANUAL").upper()
            self.flight_mode = mode
            self.sim.flight_mode = mode
            self.hw.fc.set_flight_mode(mode)
            if mode != "EMERGENCY":
                self.active_fault = None
            if mode == "RETURN_TO_HOME" or mode == "RTH":
                self.rth_active = True
            else:
                self.rth_active = False
            return {"status": "OK", "mode": self.flight_mode}

        elif cmd == "HOVER":
            self.flight_mode = "POSITION_HOLD"
            self.sim.flight_mode = "POSITION_HOLD"
            self.sim.set_command_velocity(0, 0, 0, 0)
            self.rth_active = False
            return {"status": "OK", "action": "HOVER"}

        elif cmd == "LAND":
            self.flight_mode = "LAND"
            self.sim.flight_mode = "LAND"
            self.sim.set_command_velocity(0, -1.2, 0, 0)
            return {"status": "OK", "action": "LANDING"}

        elif cmd == "RTH" or cmd == "RETURN_TO_HOME":
            self.flight_mode = "RETURN_TO_HOME"
            self.sim.flight_mode = "RETURN_TO_HOME"
            self.rth_active = True
            logger.info("Initiated Return to Home (RTH) sequence to Portal")
            return {"status": "OK", "action": "RTH"}

        elif cmd == "START_MISSION":
            self.mission_active = True
            self.mission_paused = False
            self.flight_mode = "AUTONOMOUS"
            self.sim.flight_mode = "AUTONOMOUS"
            self.armed = True
            self.sim.armed = True
            self.current_waypoint_idx = 0
            self.mission_start_time = time.time()
            return {"status": "OK", "action": "START_MISSION"}

        elif cmd == "PAUSE_MISSION":
            self.mission_paused = True
            self.sim.set_command_velocity(0, 0, 0, 0)
            return {"status": "OK", "action": "PAUSE_MISSION"}

        elif cmd == "RESUME_MISSION":
            self.mission_paused = False
            return {"status": "OK", "action": "RESUME_MISSION"}

        elif cmd == "ABORT_MISSION":
            self.mission_active = False
            self.flight_mode = "MANUAL"
            self.sim.flight_mode = "MANUAL"
            self.sim.set_command_velocity(0, 0, 0, 0)
            return {"status": "OK", "action": "ABORT_MISSION"}

        elif cmd == "CALIBRATE":
            sensor = cmd_data.get("sensor", "").lower()
            if sensor == "imu":
                self.hw.imu.calibrate()
            elif sensor == "lidar":
                self.hw.lidar.calibrate()
            elif sensor == "barometer":
                self.hw.barometer.calibrate()
            elif sensor == "gas":
                self.hw.gas.zero_calibrate()
            return {"status": "OK", "calibrating": sensor}

        elif cmd == "SET_SPEED_MOD":
            mode = cmd_data.get("mode", "NORMAL").upper()
            if mode == "BOOST":
                self.speed_mode = "BOOST"
                self.sim.speed_multiplier = DRONE_PARAMS["boost_multiplier"]
            elif mode == "PRECISION":
                self.speed_mode = "PRECISION"
                self.sim.speed_multiplier = DRONE_PARAMS["precision_multiplier"]
            else:
                self.speed_mode = "NORMAL"
                self.sim.speed_multiplier = 1.0
            return {"status": "OK", "speed_mode": self.speed_mode}

        return {"status": "UNKNOWN_COMMAND", "cmd": cmd}

    def _update_keyboard_velocities(self):
        """Translate pressed keyboard keys into world velocity vectors."""
        if not self.armed or self.flight_mode == "EMERGENCY":
            self.sim.set_command_velocity(0, 0, 0, 0)
            return

        max_speed = DRONE_PARAMS["max_speed_ms"]
        vert_speed = DRONE_PARAMS["max_vertical_speed_ms"]
        yaw_rate = DRONE_PARAMS["max_yaw_rate_rads"]

        # Forward/Backward along drone's facing heading
        yaw_rad = math.radians(self.sim.yaw)
        
        # Local forward vector in world XZ
        # Heading 0 = +X (East), Heading 90 = -Z (North/Inby in cave), Heading 180 = -X, Heading 270 = +Z
        # In our coordinate system:
        # Facing into cavern (toward -Z) is Heading 180°:
        # dx_forward = -sin(yaw), dz_forward = -cos(yaw)
        fwd_x = -math.sin(yaw_rad)
        fwd_z = -math.cos(yaw_rad)
        
        # Right vector (90 deg to right of forward)
        right_x = math.cos(yaw_rad)
        right_z = -math.sin(yaw_rad)

        target_vx = 0.0
        target_vz = 0.0
        target_vy = 0.0
        target_yaw_rate = 0.0

        if self.keys_pressed["w"]:
            target_vx += fwd_x * max_speed
            target_vz += fwd_z * max_speed
        if self.keys_pressed["s"]:
            target_vx -= fwd_x * max_speed
            target_vz -= fwd_z * max_speed
        if self.keys_pressed["d"]:
            target_vx += right_x * max_speed
            target_vz += right_z * max_speed
        if self.keys_pressed["a"]:
            target_vx -= right_x * max_speed
            target_vz -= right_z * max_speed

        if self.keys_pressed["r"]:
            target_vy += vert_speed
        if self.keys_pressed["f"]:
            target_vy -= vert_speed

        if self.keys_pressed["q"]:
            target_yaw_rate -= yaw_rate
        if self.keys_pressed["e"]:
            target_yaw_rate += yaw_rate

        self.sim.set_command_velocity(target_vx, target_vy, target_vz, target_yaw_rate)

    def update_autonomous(self, dt: float):
        """Handle autonomous waypoint navigation or Return-To-Home."""
        if not self.armed:
            return

        # 1. Return to Home Logic
        if self.rth_active:
            home = DRONE_PARAMS["portal_home_pos"]
            dx = home["x"] - self.sim.x
            dy = home["y"] - self.sim.y
            dz = home["z"] - self.sim.z
            dist_2d = math.sqrt(dx**2 + dz**2)
            
            if dist_2d < 1.0 and abs(dy) < 0.8:
                # Arrived at portal! Descend and land
                if self.sim.y > 0.4:
                    self.sim.set_command_velocity(0, -0.8, 0, 0)
                else:
                    self.armed = False
                    self.sim.armed = False
                    self.rth_active = False
                    self.flight_mode = "MANUAL"
                    logger.info("RTH Landing Complete. Drone Disarmed at Portal.")
                return

            # Navigate towards home along safe corridor
            speed = min(3.5, dist_2d * 0.8)
            vx = (dx / (dist_2d + 1e-4)) * speed
            vz = (dz / (dist_2d + 1e-4)) * speed
            vy = max(-1.5, min(1.5, dy * 0.8))
            
            # Align yaw towards heading
            target_yaw = math.degrees(math.atan2(-vx, -vz)) % 360.0
            yaw_diff = (target_yaw - self.sim.yaw + 180) % 360 - 180
            yaw_rate = max(-1.2, min(1.2, yaw_diff * 0.05))
            
            self.sim.set_command_velocity(vx, vy, vz, yaw_rate)
            return

        # 2. Autonomous Waypoint Mission
        if self.mission_active and not self.mission_paused:
            if self.current_waypoint_idx >= len(self.waypoints):
                logger.info("Mission completed all waypoints. Returning to Home.")
                self.rth_active = True
                self.mission_active = False
                return

            wp = self.waypoints[self.current_waypoint_idx]
            dx = wp["x"] - self.sim.x
            dy = wp["y"] - self.sim.y
            dz = wp["z"] - self.sim.z
            dist_3d = math.sqrt(dx**2 + dy**2 + dz**2)

            if dist_3d < 2.5:
                # Reached waypoint
                logger.info("Reached Waypoint %d (%s)", self.current_waypoint_idx + 1, MINE_STATIONS[self.current_waypoint_idx]["name"])
                self.current_waypoint_idx += 1
                return

            speed = min(2.8, dist_3d * 0.6)
            vx = (dx / (dist_3d + 1e-4)) * speed
            vz = (dz / (dist_3d + 1e-4)) * speed
            vy = (dy / (dist_3d + 1e-4)) * speed
            
            target_yaw = math.degrees(math.atan2(-vx, -vz)) % 360.0
            yaw_diff = (target_yaw - self.sim.yaw + 180) % 360 - 180
            yaw_rate = max(-1.0, min(1.0, yaw_diff * 0.04))

            self.sim.set_command_velocity(vx, vy, vz, yaw_rate)

    def get_active_sector_name(self) -> str:
        """Determine which sector the drone is currently occupying."""
        z = self.sim.z
        if z > 15:
            return "1. Portal Entrance Arch"
        elif z > -50:
            return "2. Western Timber Corridor"
        elif z > -95:
            return "3. Grand Extraction Stope"
        elif z > -140:
            return "4. North-East Ore Chute"
        else:
            return "5. Deep Abyss Winze Shaft"
