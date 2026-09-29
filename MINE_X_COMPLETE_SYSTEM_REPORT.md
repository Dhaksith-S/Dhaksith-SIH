# MINE-X DRONE COMMAND: AUTONOMOUS SUBTERRANEAN MINE INSPECTION & SPHERICAL DRONE SYSTEM
### Technical Architecture, Digital Twin Engineering, Multi-Mode Kinematics & Verification Report
**Project Name**: MINE-X Drone Command  
**Target Domain**: Subterranean Mining Safety, Hazardous Drift Exploration & Autonomous Remote Inspection  
**Repository**: [Dhaksith-S/Dhaksith-SIH](https://github.com/Dhaksith-S/Dhaksith-SIH)  
**Date**: September 2026  

---

## 1. Executive Summary

Subterranean mining presents extreme operational hazards: toxic gas accumulations (methane $\text{CH}_4$, carbon monoxide $\text{CO}$, hydrogen sulfide $\text{H}_2\text{S}$), oxygen deficiency ($\text{O}_2 < 19.5\%$), rockfall, structural timber collapse, and complete GPS deprivation. Conventional ground rovers are easily immobilized by blasted rock talus and rail debris, while conventional open-rotor multirotors suffer catastrophic destruction upon contacting mine walls, roofs, or support timbering.

**MINE-X Drone Command** solves these core vulnerabilities through a unified software, physics, and digital-twin control architecture:
1. **Spherical Protective Cage Drone**: A lightweight carbon-fiber geodesic spherical cage ($R = 1.35\text{m}$) that encloses the flight mechanics. It decouples flight aerodynamics from ground locomotion, enabling the drone to fly through large open stopes and smoothly roll along mine drift floors and haulage rail corridors without snagging.
2. **Decoupled Gimbal Kinematics**: During ground travel, the outer spherical protective cage rotates freely to provide traction, while an internal stabilized gimbal keeps the central avionics, optical inspection camera, and high-intensity searchlights strictly upright and level ($\Delta\theta_{\text{pitch}} < 0.03\text{ rad}$).
3. **Subterranean Digital Twin & Geospatial Radar**: A full Three.js 3D reconstruction of a 240-meter underground haulage drift (Titan Cavern) featuring timber square-set arches, ore rail tracks, fallen boulder talus, volumetric methane gas plumes, and simulated LiDAR point clouds.
4. **Safety & Telemetry Interlocks**: Bidirectional 20 Hz WebSocket telemetry streaming, 9-DOF IMU artificial horizon, 6-axis Time-of-Flight (ToF) obstacle rangefinders, atmospheric multi-gas monitoring, spacebar Emergency Stop with latched fault recovery, and single-metric trend charting.
5. **Zero-Error Automated Verification**: End-to-end verification executed via Playwright confirming seamless operation across flight, landing touchdown, ground rolling with upright horizon, takeoff, and emergency disarming.

---

## 2. Visual Proof of Operations

| Mode | Screenshot File | State & Telemetry Highlights |
|---|---|---|
| **Mode 1: Normal Flight** | `mine-x-drone/screenshots/spherical_drone/mode_1_normal_flight.png` | Props spin at high RPM with semi-transparent blur discs (`opacity: 0.75`), outer cage remains stationary (`\theta = 0`), dual searchlights illuminate cavern, Follow Drone view active. |
| **Mode 2: Landing Touchdown** | `mine-x-drone/screenshots/spherical_drone/mode_2_touchdown.png` | Smooth descent to floor contact at $y = 1.35\text{m}$ between haulage rails, props throttle to idle. |
| **Mode 3: Ground Rolling** | `mine-x-drone/screenshots/spherical_drone/mode_3_ground_rolling.png` | Forward traversal along $Z: 25.0 \to 36.0\text{m}$, outer cage rolled **$+11.815\text{ rad}$**, while inner camera stayed **strictly upright and level** ($0.022\text{ rad}$). |
| **Mode 4: Takeoff** | `mine-x-drone/screenshots/spherical_drone/mode_4_takeoff.png` | Cage rotation halts, propellers spin up to high RPM, and drone climbs into hover ($y = 3.78\text{m}$). |
| **Mode 5: Emergency Disarm** | `mine-x-drone/screenshots/spherical_drone/mode_5_emergency_disarmed.png` | Motors immediately killed (`0.0 RPM`), latched fault banner active, zero flight animation while disarmed. |
| **Mode 6: Design Reference Modal** | `mine-x-drone/screenshots/spherical_drone/mode_6_design_ref_modal.png` | Secondary button opens video modal playing the original 10-second reference clip without disturbing the live 3D viewport. |
| **Wide Cavern Overview** | `mine-x-drone/screenshots/spherical_drone/overview_scene_wide.png` | Top cyan locator beacon ensures instant orientation in wide overview zoom across the 240m drift. |

---

## 3. High-Level System Architecture

```text
       ┌────────────────────────────────────────────────────────────────────────┐
       │                       WEB 3D COMMAND DASHBOARD                         │
       │                                                                        │
       │  Three.js 3D Titan Cavern Scene    │  Real-Time Flight Control HUD     │
       │  Spherical Cage Drone & Kinematics │  9-DOF IMU Artificial Horizon     │
       │  Dynamic Spotlights & Light Cones  │  Atmospheric Gas Monitor (5-Gas)  │
       │  Top-Down Geospatial Mine Radar    │  Single-Metric Trend Charts       │
       │  Follow Drone / Overview Views     │  Latched Emergency Fault Banner   │
       └───────────────────────────────────┬────────────────────────────────────┘
                                           │
                                   WebSocket (20 Hz)
                               JSON Telemetry & Control
                                           │
       ┌───────────────────────────────────▼────────────────────────────────────┐
       │                        PYTHON BACKEND ENGINE                           │
       │                                                                        │
       │  FastAPI (ASGI Framework)          │  Drone Kinematics & Physics Engine│
       │  WebSocket Broadcast Manager       │  Sensor Fusion Aggregator         │
       │  Safety Monitor & Alert Evaluator  │  SQLite Persistent Database       │
       │  Flight Controller & Command Dispatch │ Mission Exporter (CSV / JSON) │
       └───────────────────────────────────┬────────────────────────────────────┘
                                           │
                               Hardware Abstraction Layer
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            ▼                              ▼                              ▼
    Flight Controller               Sensor Array                   Vision & Nav
    • PX4 / MAVLink / Sim           • 5-Gas Atmospheric Hub       • Forward RGB Cam
    • ESC Motor Controllers         • 6-Axis ToF Rangefinders     • Thermal LWIR Core
    • 4-in-1 DShot1200              • Optical Flow & Barometer    • LiDAR Point Cloud
```

---

## 4. Spherical Rolling-Cage Drone Engineering

The 3D drone model was modeled to match the physical reference video (`main.mp4`), addressing all industrial underground constraints:

### 4.1 Structural Components
1. **Open Protective Cage ($R = 1.35\text{m}$)**:
   - **Geodesic Wireframe**: Dark carbon-composite icosahedron strut structure with open triangular facets allowing high airflow through rotors with zero prop-wash blockage.
   - **Structural Reinforcing Hoops**: Five precision carbon toroids (Equatorial hoop, Prime Meridian, Orthogonal Meridian, and dual 45-degree diagonal load-distributing rings).
   - **Node Gussets**: Anodized orange aluminum bracket nodes clamping all rib intersections for impact dissipation.
2. **Compact Ground Drive System**:
   - **Concealed Traction Mechanism**: High-drag hanging external wheels were eliminated. Ground drive is executed via a low-profile internal drive ring fitted near the bottom inner equator of the sphere and paired with an enclosed micro-actuator housing tucked flush beneath the central chassis.
3. **Inner Avionics Core & Gimbal**:
   - **Central Flight Body**: Rigid dual-deck carbon-fiber chassis holding the flight controller, power distribution board, and radio transceiver.
   - **Brass/Gold Antenna Puck**: Top-mounted hemispherical antenna puck matching the reference visual design.
   - **Arm Spars & Motors**: 4 carbon-fiber arm spars terminating in anodized orange brushless motor stators and bells.
   - **Propellers & Dynamic Motion Blur**: 2-blade carbon props equipped with semi-transparent blur discs that scale in opacity and spin speed directly based on telemetry motor RPMs.
4. **Inspection Lighting & Optical Sensors**:
   - **Forward Optical Camera**: Wide-angle inspection camera housing with anti-reflective blue coated lens bezel.
   - **Twin High-Intensity Searchlights**: Dual forward headlight pods casting real-time Three.js `SpotLight` illumination (range 50m) paired with volumetric conical light beam meshes penetrating the subterranean mist.
   - **Navigation & Locator Markers**: Red port LED, green starboard LED, flashing rear cyan strobe, and a hovering top cyan octahedron beacon for instant visual orientation from distant overview zoom levels.

---

## 5. Mathematical Formulation of Multi-Mode Kinematics

The drone dynamically transitions between 5 operational modes based on telemetry states:

### 5.1 Mode 1: Normal Flight
- **Outer Cage Behavior**: The outer cage remains aerodynamically neutral and does not roll ($\theta_{\text{cage}} \to 0$).
- **Inner Core Banking**: The inner core responds to velocity vectors with realistic pitch and roll banking:
  $$\phi_{\text{target}} = \text{clamp}\left(\frac{v_x}{v_{\text{max}}} \cdot 0.35, -0.35, 0.35\right)$$
  $$\theta_{\text{target}} = \text{clamp}\left(\frac{-v_z}{v_{\text{max}}} \cdot 0.35, -0.35, 0.35\right)$$
- **Propeller Aerodynamics**: Blur disc opacity scales with motor speed:
  $$\text{Opacity}_{\text{blur}} = \min(0.75, \omega_{\text{prop}} \cdot 0.45)$$

### 5.2 Mode 2: Landing Touchdown
- **Descent Control**: Vertical descent velocity is throttled to $-0.8\text{ m/s}$ until ground proximity sensors detect the floor:
  $$y_{\text{contact}} = R_{\text{cage}} = 1.35\text{ m}$$
- **Ground Transition**: Upon floor contact, vertical velocity halts and `ground_contact` is latched to `true`.

### 5.3 Mode 3: Ground Rolling Traversal
- **Decoupled Cage Rolling**: As the drone moves horizontally across the mine drift floor along vector $(\Delta x, \Delta z)$, the outer cage rotates according to the distance traveled:
  $$\Delta s_{\text{ground}} = \sqrt{\Delta x^2 + \Delta z^2}$$
  $$\Delta\theta_{\text{roll}} = \frac{-\Delta z \cos(\psi) - \Delta x \sin(\psi)}{R_{\text{cage}}} \times 2.2$$
  $$\theta_{\text{cage}}(t) = \theta_{\text{cage}}(t-1) + \Delta\theta_{\text{roll}}$$
- **Gimbal Horizon Stabilization**: Concurrently, the inner gimbal core counter-rotates to preserve optical inspection camera horizon alignment:
  $$\text{Pitch}_{\text{inner}} = \text{lerp}(\text{Pitch}_{\text{inner}}, 0.0, 0.25) \implies |\text{Pitch}_{\text{inner}}| < 0.03\text{ rad}$$
- **Propeller Idle**: Propellers drop to low-RPM ground traction assist ($8\%$), conserving battery energy while rolling.

### 5.4 Mode 4: Takeoff
- **Ground Clearance**: Outer cage rotation halts immediately ($\Delta\theta_{\text{roll}} = 0$).
- **Rotor Spool-Up**: Propellers spin up from $8\%$ to $100\%$ within $400\text{ ms}$, generating positive lift ($\dot{y} = +1.5\text{ m/s}$) to clear obstacles.

### 5.5 Mode 5: Emergency Stop / Latched Disarm
- **Hard Motor Kill**: Spacebar or E-Stop triggers an immediate cutoff:
  $$\omega_{\text{motors}} = 0\text{ RPM}, \quad \text{Opacity}_{\text{blur}} = 0.0$$
- **Safety Interlock**: Disarms the flight controller (`armed = false`), displays the latched fault banner with recovery actions, and gently settles the spherical cage onto the terrain.

---

## 6. Subterranean Digital Twin & Cavern Reconstruction

The 3D environment models a deep-level extraction drift based on geological CAD surveys:

| Environmental Feature | Technical Specification | Functional Purpose |
|---|---|---|
| **Drift Length & Spline** | 240 meters, 7-point Catmull-Rom spline curve | Models portal, eastern bypass, Great Stope dome, and winze descent. |
| **Cavern Wall Shader** | 1024×1024 procedural canvas texture with hematite ore veins | High visual fidelity without heavy external image network dependencies. |
| **Haulage Ore Rails** | Twin continuous steel rails ($0.75\text{m}$ gauge) on timber ties | Provides realistic ground reference for ground rolling traversal. |
| **Timber Square-Sets** | Structural timber frames with overhead cross-ties & lanterns | Simulates mine drift support structures requiring obstacle avoidance. |
| **Atmospheric Gas Plumes** | Volumetric particle cloud with pulsing opacity | Visualizes hazardous methane concentration zones along the drift. |
| **LiDAR Point Cloud** | 12,000 spatial point vertices with depth attenuation | Represents real-time SLAM laser scanning and drift cross-sections. |

---

## 7. Atmospheric Safety & Sensor Telemetry Suite

### 7.1 Multi-Gas Atmospheric Monitor
Monitored continuously at 20 Hz with safety threshold limits and packet staleness detection:

| Gas Parameter | Sensor Chemical Target | Safe Threshold | Warning Level | Simulated Nominal |
|---|---|---|---|:---:|
| **Methane ($\text{CH}_4$)** | Explosive gas accumulation | $< 0.50\%$ | $> 0.75\%$ | $0.022\%$ |
| **Carbon Monoxide ($\text{CO}$)** | Incomplete combustion / fire | $< 25\text{ ppm}$ | $> 50\text{ ppm}$ | $2.8\text{ ppm}$ |
| **Carbon Dioxide ($\text{CO}_2$)** | Stale air / displacement | $< 1000\text{ ppm}$ | $> 2500\text{ ppm}$ | $508\text{ ppm}$ |
| **Oxygen ($\text{O}_2$)** | Life-safety minimum | $> 19.5\%$ | $< 18.0\%$ | $20.9\%$ |
| **Hydrogen Sulfide ($\text{H}_2\text{S}$)** | Toxic strata gas | $< 10\text{ ppm}$ | $> 15\text{ ppm}$ | $0.1\text{ ppm}$ |

### 7.2 Obstacle Proximity & Attitude HUD
- **6-Axis ToF Rangefinders**: Real-time distance measurements (Forward, Reverse, Left, Right, Up, Down) with color-coded warnings when clearance drops below $2.0\text{m}$.
- **9-DOF IMU Artificial Horizon**: Roll, pitch, and yaw heading tape displaying stabilized attitude relative to the subterranean drift centerline.
- **Geospatial Mine Radar**: Plan-view 1:500 scale radar showing drift centerline, timber portals, and drone position with distance rings and North orientation arrow.

---

## 8. Verification & Automated Test Audit

Automated testing was conducted using the headless Playwright test suite (`verify_spherical_drone.py`).

| Stage | Mode Verified | Telemetry Altitude | Cage Roll Angle | Inner Core Status | Test Verdict |
|---|---|:---:|:---:|:---:|:---:|
| 1 | Normal Flight | $3.78\text{ m}$ | $0.0\text{ rad}$ | Leveled | **PASSED** |
| 2 | Landing Touchdown | $1.35\text{ m}$ | $0.0\text{ rad}$ | Ground Contact `True` | **PASSED** |
| 3 | Ground Rolling Traversal | $1.35\text{ m}$ | $+11.815\text{ rad}$ | **Upright ($0.022\text{ rad}$)** | **PASSED** |
| 4 | Takeoff Spool-Up | $3.78\text{ m}$ | $0.0\text{ rad}$ | Lift active | **PASSED** |
| 5 | Emergency Disarm | $1.35\text{ m}$ | Ceased | Motors killed ($0.0\text{ RPM}$) | **PASSED** |
| 6 | Design Reference Modal | — | — | Modal Visible `True` | **PASSED** |

---

## 9. API & Communication Protocols

### 9.1 WebSocket Telemetry Packet (Backend $\to$ Frontend @ 20 Hz)
```json
{
  "timestamp": 1790691624.12,
  "flight_status": {
    "armed": true,
    "motion_mode": "GROUND_ROLL",
    "ground_contact": true,
    "battery_pct": 86.2,
    "flight_time_s": 248.5
  },
  "position": { "x": 0.0, "y": 1.35, "z": 36.0 },
  "orientation": { "pitch": 0.0, "yaw": 180.0, "roll": 0.0 },
  "velocity": { "vx": 0.0, "vy": 0.0, "vz": 1.2 },
  "sensors": {
    "gas": {
      "methane_pct": 0.022,
      "co_ppm": 2.8,
      "co2_ppm": 508.0,
      "o2_pct": 20.9,
      "h2s_ppm": 0.1
    },
    "tof": {
      "front": 21.7, "rear": 16.4, "left": 17.0, "right": 17.0, "up": 18.8, "down": 1.35
    },
    "motors": [
      { "id": 1, "rpm": 1200 },
      { "id": 2, "rpm": 1200 },
      { "id": 3, "rpm": 1200 },
      { "id": 4, "rpm": 1200 }
    ]
  }
}
```

---

## 10. Repository & Deployment Guide

- **GitHub Repository**: [Dhaksith-S/Dhaksith-SIH](https://github.com/Dhaksith-S/Dhaksith-SIH)
- **Clone via HTTPS**:
  ```bash
  git clone https://github.com/Dhaksith-S/Dhaksith-SIH.git
  ```

### Launch Instructions
```bash
# 1. Clone repository
git clone https://github.com/Dhaksith-S/Dhaksith-SIH.git
cd Dhaksith-SIH/mine-x-drone

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the platform
python start.py

# 4. Open browser
# Navigate to http://localhost:8000
```
