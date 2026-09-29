# Dhaksith-SIH: Subterranean Mine Inspection & Spherical Drone Command System

Autonomous subterranean mine inspection, 3D digital-twin environment, and spherical rolling-cage drone platform engineered for Smart India Hackathon (SIH).

---

## 🌟 Overview

This repository contains the complete software stack for autonomous underground mine inspection, geospatial surveying, multi-mode drone flight & ground traversal, and real-time hazard monitoring in GPS-denied environments:

1. **[MINE-X Drone Command (`mine-x-drone/`)](file:///mine-x-drone/)**:
   - **Interactive 3D Subterranean Mine Scene (Three.js)**: 240-meter realistic haulage drift, timber archways, haulage track rails, rock talus cones, volumetric gas plumes, and spatial LiDAR point cloud.
   - **3D Spherical Protective Cage Drone**: Decoupled multi-mode drone system with dark geodesic carbon-fiber ribs, concealed inner ring ground drive, upright-stabilized central avionics core with gold dome antenna puck, 4 propellers with dynamic motion blur, forward inspection camera, and high-power searchlights.
   - **5 Distinct Operational Modes**:
     - *Flight Mode*: Aerodynamic banking, high RPM propellers, stabilized inner body, stationary cage.
     - *Touchdown / Landing Mode*: Smooth vertical descent onto haulage rails with floor contact detection ($y = 1.35\text{m}$).
     - *Ground Rolling Mode*: Forward/reverse ground traversal where the outer spherical cage rolls along the ground according to distance traveled while the inner camera and avionics remain strictly upright and level.
     - *Takeoff Mode*: Cage rotation halts, propellers spin up to high RPM, and drone climbs into hover.
     - *Emergency Stop (E-Stop)*: Hard motor kill, latched safety fault banner, and instant disarm interlock.
   - **FastAPI & WebSocket Telemetry Server**: 20 Hz bidirectional telemetry streaming, 9-DOF IMU artificial horizon, 6-axis ToF obstacle rangefinders, atmospheric multi-gas monitoring (CH₄, CO, CO₂, O₂, H₂S), geospatial mine radar, and single-metric telemetry trend charting.
   - **Automated Verification Suite (`verify_spherical_drone.py`)**: End-to-end headless Playwright test suite capturing telemetry-verified screenshots of all operational states.

2. **[Geological Survey GIS (`subterranean_mine_3d_geological_survey_gis.html`)](file:///subterranean_mine_3d_geological_survey_gis.html)**:
   - Standalone 3D geological survey tool and GIS visualization for subterranean mine drifts and ore bodies.

3. **[Rolling Cage Drone Prototype (`rolling-cage-drone/`)](file:///rolling-cage-drone/)**:
   - Prototype web canvas and physics demonstration for rolling-cage mechanics.

4. **Reference Material (`main.mp4`)**:
   - 10-second high-resolution physical reference video clip for the spherical cage drone design and traversal kinematics.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome / Edge / Firefox)

### Setup & Run MINE-X Drone Command

```bash
# Navigate to the mine-x-drone directory
cd mine-x-drone

# Install backend dependencies
pip install -r requirements.txt

# Start the FastAPI server & 3D Web Dashboard
python start.py
```

Open your browser to:
```text
http://localhost:8000
```

### Keyboard Controls
| Key | Action |
|:---:|---|
| **W / S** | Move Forward / Backward (or Roll Forward on ground) |
| **A / D** | Strafe Left / Right |
| **Q / E** | Yaw Left / Right (Rotate Heading) |
| **R / F** | Ascend (Climb) / Descend |
| **SPACE** | **EMERGENCY STOP** (Kill Motors & Disarm Immediately) |
| **SHIFT** | Speed Boost (1.8x) |
| **CTRL** | Precision Speed (0.35x) |
| **Pills** | Switch Camera Perspective (`Overview`, `Follow Drone`, `Camera`) |

---

## 🛠️ Verification Suite

Run the automated verification suite to validate all 5 operational modes and capture screenshots:

```bash
cd mine-x-drone
python verify_spherical_drone.py
```

Screenshots and telemetry logs will be generated in `mine-x-drone/screenshots/spherical_drone/`.
