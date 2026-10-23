import asyncio
import os
import signal
import sys
from typing import Any
from fastapi import APIRouter
import pyuac
from src.core.config import (
    APP_VERSION,
    IS_MACOS,
    IS_WINDOWS,
    LOCAL_LAN_IP,
    PLATFORM_LABEL,
    logger,
    settings,
)
from src.core.models import SystemInfoResponse
from src.services.external_api_service import api_service
from src.services.tunnel_service import tunnel_service

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info() -> SystemInfoResponse:
    """Retrieve platform info, privileges, wireless LAN URLs, and remote version status."""
    is_admin = False
    sudo_msg = ""

    if IS_WINDOWS:
        try:
            is_admin = bool(pyuac.isUserAdmin())
        except Exception:
            is_admin = False
    elif IS_MACOS:
        is_admin = os.geteuid() == 0
        if not is_admin:
            sudo_msg = "Notice: Running without sudo. iOS 17+ tunnel operations may require administrator/sudo."

    github_ver, github_broadcast = await api_service.get_github_version_and_broadcast()
    mobile_url = f"http://{LOCAL_LAN_IP}:{settings.port}"

    return SystemInfoResponse(
        app_version=APP_VERSION,
        platform=PLATFORM_LABEL,
        is_admin=is_admin,
        sudo_message=sudo_msg,
        local_lan_ip=LOCAL_LAN_IP,
        mobile_url=mobile_url,
        github_version=github_ver,
        github_broadcast=github_broadcast,
    )


@router.post("/shutdown")
async def shutdown_app() -> dict[str, Any]:
    """Gracefully terminate background tasks and stop the local server."""
    logger.info("Application shutdown requested via API")

    async def _delayed_exit():
        await asyncio.sleep(0.5)
        await tunnel_service.close_all()
        # Kill this process cleanly
        os.kill(os.getpid(), signal.SIGTERM if not IS_WINDOWS else signal.SIGINT)

    asyncio.create_task(_delayed_exit())
    return {"success": True, "message": "GeoPort server is shutting down..."}
