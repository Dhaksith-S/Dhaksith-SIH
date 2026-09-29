"""
MINE-X DRONE COMMAND - System Launcher
Starts the FastAPI server, WebSocket telemetry broadcaster, and 3D Web Dashboard.
"""

import sys
import os
import argparse
from pathlib import Path

# Add current folder to sys.path so 'backend' can be imported anywhere
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

import uvicorn
from backend.config import HOST, PORT, MODE

def main():
    parser = argparse.ArgumentParser(description="MINE-X DRONE COMMAND Launcher")
    parser.add_argument("--host", default=HOST, help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=PORT, help="Server port (default: 8000)")
    parser.add_argument("--mode", default=MODE, choices=["SIMULATION", "REAL"], help="Operational mode")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload")
    args = parser.parse_args()

    print("=" * 70)
    print("        MINE-X DRONE COMMAND — SUBTERRANEAN MINE INSPECTION        ")
    print("=" * 70)
    print(f" Mode:            {args.mode}")
    print(f" Server URL:      http://localhost:{args.port}")
    print(f" WebSocket:       ws://localhost:{args.port}/ws")
    print(f" 3D Cavern:       Titan Cavern Procedural Model Loaded")
    print(f" Safety Alerts:   Active Atmospheric & Proximity Monitoring")
    print("=" * 70)
    print(" Keyboard Controls:")
    print("   [W] Forward        [S] Backward       [A] Left        [D] Right")
    print("   [Q] Rotate Left    [E] Rotate Right   [R] Ascend      [F] Descend")
    print("   [SPACE] Emergency Stop (Kill Motors)")
    print("   [SHIFT] Boost Speed (2x)              [CTRL] Precision Speed (0.35x)")
    print("=" * 70)

    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
