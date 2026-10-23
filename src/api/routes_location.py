from typing import Any
from fastapi import APIRouter, HTTPException
from src.core.models import GPXPlayRequest, LocationSetRequest, NudgeRequest, SimulationStatus
from src.services.simulation_service import simulation_service

router = APIRouter(prefix="/api/devices/{udid}", tags=["Location Simulation"])


@router.get("/status", response_model=SimulationStatus)
async def get_simulation_status(udid: str) -> SimulationStatus:
    """Get active location simulation status for device."""
    return simulation_service.get_status(udid)


@router.post("/location")
async def set_device_location(udid: str, payload: LocationSetRequest) -> dict[str, Any]:
    """Set custom simulated GPS location on target device."""
    try:
        await simulation_service.set_location(
            udid=udid,
            latitude=payload.latitude,
            longitude=payload.longitude,
            altitude=payload.altitude or 0.0,
            mode="static",
        )
        return {
            "success": True,
            "message": "Location updated successfully",
            "latitude": payload.latitude,
            "longitude": payload.longitude,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/location")
async def stop_device_location(udid: str) -> dict[str, Any]:
    """Clear simulated GPS location and restore real device GPS."""
    try:
        await simulation_service.clear_location(udid)
        return {"success": True, "message": "Location simulation stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nudge")
async def nudge_device_location(udid: str, payload: NudgeRequest) -> dict[str, Any]:
    """Step/nudge location in a cardinal direction (north, south, east, west)."""
    try:
        new_lat, new_lng = await simulation_service.nudge_location(
            udid=udid,
            direction=payload.direction,
            distance_meters=payload.distance_meters,
        )
        return {
            "success": True,
            "latitude": new_lat,
            "longitude": new_lng,
            "direction": payload.direction,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route/play")
async def play_route(udid: str, payload: GPXPlayRequest) -> dict[str, Any]:
    """Play a GPX waypoint route on device."""
    try:
        await simulation_service.play_gpx(
            udid=udid,
            waypoints=payload.waypoints,
            loop=payload.loop,
            speed_multiplier=payload.speed_multiplier,
        )
        return {
            "success": True,
            "message": f"Route playback started with {len(payload.waypoints)} waypoints",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route/pause")
async def pause_route(udid: str) -> dict[str, Any]:
    """Pause active route playback."""
    await simulation_service.pause_gpx(udid)
    return {"success": True, "message": "Route playback paused"}


@router.post("/route/resume")
async def resume_route(udid: str) -> dict[str, Any]:
    """Resume paused route playback."""
    await simulation_service.resume_gpx(udid)
    return {"success": True, "message": "Route playback resumed"}


@router.post("/route/stop")
async def stop_route(udid: str) -> dict[str, Any]:
    """Stop active route playback."""
    await simulation_service.stop_gpx(udid)
    return {"success": True, "message": "Route playback stopped"}
