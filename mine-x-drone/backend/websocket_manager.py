"""
MINE-X DRONE COMMAND - WebSocket Connection Manager
Maintains active real-time client WebSocket connections and broadcasts telemetry packets.
"""

import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("WebSocketManager")

class ConnectionManager:
    """Manages active WebSockets and handles broadcasting to connected operators."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New operator client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Operator client disconnected. Remaining: %d", len(self.active_connections))

    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcast JSON payload to all active dashboard clients."""
        if not self.active_connections:
            return
            
        json_str = json.dumps(data)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json_str)
            except Exception as e:
                logger.error("Failed to send message to client: %s", e)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)
