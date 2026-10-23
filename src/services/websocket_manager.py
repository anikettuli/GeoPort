import asyncio
import json
from typing import Any
from fastapi import WebSocket
from src.core.config import logger


class WebSocketManager:
    """Manages active WebSocket connections and broadcasts real-time events to the frontend."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.debug(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.debug(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        message = json.dumps({"event": event_type, "data": data})
        dead_connections = []

        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.debug(f"Failed to send message over websocket: {e}")
                    dead_connections.append(connection)

            for dead in dead_connections:
                if dead in self.active_connections:
                    self.active_connections.remove(dead)


# Global singleton instance
ws_manager = WebSocketManager()
