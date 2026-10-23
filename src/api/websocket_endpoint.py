from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.config import logger
from src.services.websocket_manager import ws_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time bi-directional events for simulation updates and device state."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client pings
            data = await websocket.receive_text()
            logger.debug(f"Received WS text: {data}")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WS error: {e}")
        await ws_manager.disconnect(websocket)
