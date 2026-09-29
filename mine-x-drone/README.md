# MINE-X DRONE COMMAND
### Advanced Autonomous Underground Mine Inspection Drone System

**MINE-X DRONE COMMAND** is a complete, real-time command, control, and 3D digital-twin inspection platform engineered specifically for underground mine environments (unventilated drifts, deep winze shafts, high-clearance stopes, and timber-supported haulage corridors).

---

## 1. System Architecture

```text
                 ┌────────────────────────────────────────────────────────┐
                 │                WEB 3D COMMAND DASHBOARD                │
                 │                                                        │
                 │ Three.js Titan Cavern       Sensors & Gas Array        │
                 │ 3D Rolling-Cage Drone       RGB / Thermal LWIR View    │
                 │ Kinematics & Attitude HUD   Geospatial Mine Radar      │
                 │ Live Telemetry Charts       Safety Alert Center        │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                     WebSocket (20 Hz)
                                             │
                 ┌───────────────────────────▼────────────────────────────┐
                 │                     PYTHON BACKEND                     │
                 │                                                        │
                 │ FastAPI & Uvicorn           Drone Controller           │
                 │ Kinematic & Physics Engine  Telemetry Manager          │
                 │ Safety & Alert Evaluator    SQLite Database Logger     │
                 │ Sensor Fusion Aggregator    Mission Waypoint Planner   │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                 Hardware Abstraction Layer
                                             │
          ┌──────────────────────────────────┼──────────────────────────────────┐
          │                                  │                                  │
   Flight Controller                      Sensors                        Onboard Computer
  (PX4 / MAVLink / Sim)             (LiDAR / Gas / IMU)                 (Jetson / Pi / ESP32)
          │                                  │                                  │
    Motors & ESCs                  Thermal & RGB Cameras                  Sub-surface Comms
  (4-in-1 DShot1200)               (FLIR LWIR / Sony 4K)                 (900MHz MIMO Mesh)
```

---

## 2. Key Capabilities & Features

1. **Interactive Keyboard Flight Control**:
   - `W` / `S`: Move Forward / Backward along current drone heading
   - `A` / `D`: Move Left / Right (lateral strafe)
   - `Q` / `E`: Rotate Left (Yaw -) / Rotate Right (Yaw +)
   - `R` / `F`: Ascend (Up) / Descend (Down)
   - `SPACE`: **EMERGENCY STOP** (immediately cuts throttle, stops velocities, disarms, logs alert)
   - `SHIFT`: Boost speed multiplier (1.8x)
   - `CTRL`: Precision fine-alignment mode (0.35x)
   - On-screen mechanical keycap HUD illuminates in real-time as keys are pressed.

2. **Full Three.js 3D Subterranean Mine Environment**:
   - Recreates the complete 240-meter haulage drift from `subterranean_mine_3d_geological_survey_gis.html`
   - High-detail procedural terracotta hematite ore texture & bump mapping
   - Central rock pillar inside Grand Extraction Stope
   - Fallen boulders, talus cones, ceiling stalactites, timber square-set support portals with mining lanterns
   - Dual haulage steel rail tracks + wooden sleepers and overhead yellow flexible ventilation ducts
   - 10-meter spatial cadastral grid & 5 interactive geological station beacons

3. **High-Detail 3D Quadcopter Drone Model**:
   - Carbon-fiber frame with 4 arms at 45°
   - 4 brushless motors with dynamic counter-rotating propellers (spinning with RPM motion blur)
   - Outer protective rolling cage protecting against rock strikes
   - Front 3-axis gimbal camera (optical RGB + LWIR thermal lens)
   - Top solid-state LiDAR turret with spinning laser beam projection
   - Navigation LEDs (Red port, Green starboard, flashing rear Cyan strobe, high-power survey searchlight)

4. **Atmospheric Safety Monitoring Panel**:
   - Individual real-time cards for **Methane (CH₄)**, **Carbon Monoxide (CO)**, **Carbon Dioxide (CO₂)**, **Oxygen (O₂)**, and **Hydrogen Sulfide (H₂S)**
   - Clear and prominent label: `● SIMULATION DATA — Sensor values simulated. Not a certified mine life-safety meter.`
   - 3D Volumetric Gas Plume: visualizes contaminated gas pockets in deep unventilated shafts!

5. **Individual Hardware Inspector**:
   - Inspects frame, 4 brushless motors, 4 ESCs, flight controller, Jetson Orin companion computer (CPU, RAM, GPU, Temp), STM32/ESP32 coprocessor, battery BMS, PDB rails (5V, 12V, 24V), and storage.

6. **6-Direction Obstacle Rangefinders**:
   - Distance measurements (UP, DOWN, LEFT, RIGHT, FRONT, REAR) color-coded green (>3m), amber (1.5-3m), red (<1.5m).

7. **Geospatial Cavern Radar**:
   - 2D Top-down CAD radar canvas that auto-tracks and centers on the drone, showing drift corridor walls, safe corridor, station pins, gas hazard zones, and breadcrumb flight path.

8. **Sensor Zero-Calibration System**:
   - Calibration modal for IMU, LiDAR, Barometer, Gas Array, and Camera with simulated progress feedback.

9. **Data Persistence & Telemetry Logging**:
   - Stores flight logs, sensor logs, and safety alerts into SQLite database (`data/mine.db`).
   - One-click CSV export via `/api/export/csv`.

---

## 3. Hardware Abstraction Layer (HAL)

The system is designed with abstract base classes (`backend/hardware.py`) so physical drivers can be hooked up without altering the frontend or telemetry pipeline:

```python
# To switch to real hardware:
# In backend/config.py:
MODE = "REAL"
```

Available interfaces:
- `FlightControllerInterface` (e.g., `RealMavlinkFlightController` via PyMAVLink)
- `LiDARInterface` (e.g., `RealRPLiDAR` via USB UART)
- `CameraInterface` (e.g., USB V4L2 or MIPI-CSI camera)
- `ThermalCameraInterface` (e.g., FLIR Boson / Lepton)
- `GasSensorInterface` (e.g., MQ / NDIR optical gas sensors via I2C/CAN)
- `IMUInterface` (e.g., BNO085 / ICM-20948 via SPI/I2C)

---

## 4. Running the System

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start MINE-X Drone Command
python start.py

# 3. Open browser at:
# http://localhost:8000
```
