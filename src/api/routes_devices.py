from typing import Any
from fastapi import APIRouter, HTTPException
from src.core.models import DeviceInfo
from src.services.device_service import device_service

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.get("", response_model=list[DeviceInfo])
async def list_devices(wifihost: str | None = None, udid: str | None = None) -> list[DeviceInfo]:
    """Retrieve all connected iOS devices (USB and Wi-Fi)."""
    return await device_service.list_connected_devices(wifihost=wifihost, target_udid=udid)


@router.post("/{udid}/developer-mode")
async def enable_dev_mode(udid: str) -> dict[str, Any]:
    """Turn on Developer Mode for an iOS device."""
    success, error = await device_service.enable_developer_mode(udid)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to enable Developer Mode")
    return {"success": True, "message": "Developer Mode enabled successfully"}


@router.post("/{udid}/mount")
async def mount_disk(udid: str) -> dict[str, Any]:
    """Mount the Developer Disk Image on an iOS device."""
    success, error = await device_service.mount_developer_image(udid)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to mount developer image")
    return {"success": True, "message": "Developer Image mounted successfully"}
