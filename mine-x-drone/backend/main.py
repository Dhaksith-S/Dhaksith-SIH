"""
MINE-X DRONE COMMAND - Main FastAPI Application
Coordinates the simulation loop, Hardware Abstraction Layer, WebSocket streaming,
REST APIs, and serves the 3D Web Dashboard.
"""

import asyncio
import time
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import HOST, PORT, UPDATE_RATE_HZ, TELEMETRY_LOG_RATE_HZ, MODE, DRONE_PARAMS
from .database import init_db, log_telemetry, log_sensors, get_recent_telemetry, get_recent_alerts, acknowledge_alert, export_telemetry_csv
from .hardware import HardwareSystem
from .simulator import MineSimulator
from .safety import SafetyManager
from .sensors import SensorManager
from .drone_controller import DroneController
from .telemetry import TelemetryManager
from .websocket_manager import ConnectionManager, safe_dumps

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Main")

# Initialize app
app = FastAPI(title="MINE-X DRONE COMMAND", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core subsystems
simulator = MineSimulator()
hardware = HardwareSystem(mode=MODE, simulator_ref=simulator)
hardware.attach_simulator(simulator)
safety = SafetyManager()
sensors = SensorManager(hardware, simulator)
controller = DroneController(simulator, hardware)
telemetry = TelemetryManager(simulator, sensors, safety, controller)
ws_manager = ConnectionManager()

# Background task handles
bg_tasks = []

class CommandPayload(BaseModel):
    command: str
    key: str = ""
    speed: float = 1.0
    mode: str = ""
    sensor: str = ""
    alert_id: int = 0

@app.on_event("startup")
async def startup_event():
    """Start database and background simulation loops."""
    init_db()
    logger.info("Initializing MINE-X Drone Command in %s MODE", MODE)
    
    # Run high-frequency physics & telemetry broadcast loop
    task_telemetry = asyncio.create_task(run_telemetry_broadcast_loop())
    # Run periodic database logger loop
    task_logger = asyncio.create_task(run_database_logging_loop())
    bg_tasks.extend([task_telemetry, task_logger])

@app.on_event("shutdown")
async def shutdown_event():
    """Cancel background tasks cleanly."""
    for task in bg_tasks:
        task.cancel()
    logger.info("MINE-X Drone Command shutdown complete.")

async def run_telemetry_broadcast_loop():
    """20Hz (50ms) Physics step, autonomous trajectory, and WebSocket broadcast."""
    dt = 1.0 / UPDATE_RATE_HZ
    last_time = time.time()
    
    while True:
        try:
            now = time.time()
            frame_dt = min(0.1, max(0.01, now - last_time))
            last_time = now
            
            # Step 1: Update physics simulation
            simulator.update_physics(frame_dt)
            
            # Step 2: Update autonomous/RTH navigation
            controller.update_autonomous(frame_dt)
            
            # Step 3: Compile telemetry and broadcast
            telemetry_packet = telemetry.get_current_packet()
            await ws_manager.broadcast_json(telemetry_packet)
            
            await asyncio.sleep(dt)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in telemetry loop: %s", e)
            await asyncio.sleep(0.1)

async def run_database_logging_loop():
    """2Hz database persistence loop."""
    interval = 1.0 / TELEMETRY_LOG_RATE_HZ
    while True:
        try:
            if simulator.armed:
                packet = telemetry.get_current_packet()
                log_telemetry(packet)
                log_sensors(packet.get("sensors", {}))
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in database logging loop: %s", e)
            await asyncio.sleep(1.0)

# ==========================================
# WEBSOCKET ENDPOINT
# ==========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main bidirectional telemetry and control WebSocket."""
    await ws_manager.connect(websocket)
    try:
        # Send initial full packet
        initial_packet = telemetry.get_current_packet()
        await websocket.send_text(safe_dumps(initial_packet))
        
        while True:
            data = await websocket.receive_json()
            # Handle incoming command
            res = controller.handle_command(data)
            
            # Special command: alert acknowledgment
            if data.get("command") == "ACK_ALERT" and "alert_id" in data:
                safety.acknowledge(int(data["alert_id"]))
                
            # Send immediate command ACK
            await websocket.send_text(safe_dumps({"type": "COMMAND_ACK", "result": res}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        ws_manager.disconnect(websocket)

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.get("/api/status")
async def get_system_status():
    """Return core system diagnostic status."""
    return {
        "status": "ONLINE",
        "system": "MINE-X DRONE COMMAND",
        "mode": MODE,
        "drone_name": DRONE_PARAMS["name"],
        "armed": simulator.armed,
        "flight_mode": simulator.flight_mode,
        "active_clients": len(ws_manager.active_connections)
    }

@app.post("/api/command")
async def post_command(payload: CommandPayload):
    """Execute command via REST."""
    res = controller.handle_command(payload.dict())
    return res

@app.get("/api/telemetry/latest")
async def get_latest_telemetry():
    """Return latest complete telemetry packet."""
    return telemetry.get_current_packet()

@app.get("/api/telemetry/history")
async def get_history(seconds: int = 60):
    """Return historical telemetry data for graphs."""
    return telemetry.get_history(seconds=seconds)

@app.get("/api/alerts")
async def get_alerts():
    """Get active and historical safety alerts."""
    return {
        "active": safety.active_alerts,
        "recent": get_recent_alerts(limit=50)
    }

@app.post("/api/alerts/acknowledge/{alert_id}")
async def post_acknowledge_alert(alert_id: int):
    """Acknowledge alert by ID."""
    safety.acknowledge(alert_id)
    return {"status": "ACKNOWLEDGED", "alert_id": alert_id}

@app.get("/api/hardware")
async def get_hardware_status():
    """Detailed component-by-component hardware inspector data."""
    sens = sensors.get_all_sensor_data()
    return {
        "frame": {
            "name": DRONE_PARAMS["frame"],
            "status": "OK",
            "protective_cage": "INSTALLED - HIGH CLEARANCE",
            "weight_kg": DRONE_PARAMS["weight_kg"]
        },
        "motors": sens.get("motors", []),
        "escs": sens.get("escs", []),
        "flight_controller": hardware.fc.get_status(),
        "onboard_computer": sens.get("onboard_computer", {}),
        "microcontroller": {
            "name": "STM32H743 / ESP32-S3 Dual-Core Sub-system",
            "status": "CONNECTED",
            "bus": "CAN + SPI 10MHz",
            "loop_rate_hz": 1000
        },
        "battery": sens.get("battery", {}),
        "power_distribution": sens.get("power_rails", {}),
        "storage": {
            "ssd_capacity_gb": 512,
            "used_pct": 44.2,
            "logging_active": simulator.armed,
            "sd_backup": "MOUNTED (Class 10 U3 V30)"
        }
    }

@app.post("/api/calibrate/{sensor}")
async def post_calibrate_sensor(sensor: str):
    """Initiate sensor zero-calibration."""
    return controller.handle_command({"command": "CALIBRATE", "sensor": sensor})

@app.get("/api/export/csv")
async def get_export_csv():
    """Export recent telemetry to CSV."""
    path = export_telemetry_csv(limit=500)
    if path and Path(path).exists():
        return FileResponse(path, media_type="text/csv", filename=Path(path).name)
    raise HTTPException(status_code=404, detail="No telemetry logs to export yet")

@app.get("/api/camera/frame")
async def get_camera_frame():
    """Return base64 simulated RGB frame."""
    frame_b64 = simulator.generate_simulated_camera_frame()
    return {"frame": frame_b64}

# ==========================================
# STATIC FILES & DASHBOARD SERVING
# ==========================================

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/")
async def serve_index():
    """Serve main 3D dashboard."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"status": "Frontend not found", "path": str(index_file)}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
