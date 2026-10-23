import asyncio
import math
from typing import Any
from src.core.config import logger
from src.core.models import SimulationStatus, Waypoint
from src.services.device_service import device_service
from src.services.tunnel_service import tunnel_service
from src.services.websocket_manager import ws_manager
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
from pymobiledevice3.services.simulate_location import DtSimulateLocation


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points on a sphere in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class GPXPlaybackState:
    def __init__(self, waypoints: list[Waypoint], loop: bool = False, speed_multiplier: float = 1.0) -> None:
        self.waypoints = waypoints
        self.loop = loop
        self.speed_multiplier = speed_multiplier
        self.current_index = 0
        self.is_paused = False
        self.stop_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Not paused initially
        self.task: asyncio.Task[Any] | None = None


class SimulationService:
    def __init__(self) -> None:
        self._statuses: dict[str, SimulationStatus] = {}
        self._gpx_states: dict[str, GPXPlaybackState] = {}
        self._lock = asyncio.Lock()

    def get_status(self, udid: str) -> SimulationStatus:
        """Retrieve current simulation status for a device."""
        if udid not in self._statuses:
            self._statuses[udid] = SimulationStatus(udid=udid)
        return self._statuses[udid]

    async def set_location(
        self,
        udid: str,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        mode: str = "static",
    ) -> None:
        """Set simulated location on device (auto-detects iOS 17+ RSD or legacy Lockdown)."""
        logger.info(f"Setting location for {udid} -> ({latitude}, {longitude}) [mode={mode}]")

        # Resolve device info and iOS version
        dev_info = device_service._devices_cache.get(udid)
        version_str = dev_info.product_version if dev_info else "17.0"
        is_ios17 = device_service.is_ios17_or_greater(version_str)

        if is_ios17:
            host, port = await tunnel_service.get_or_create_tunnel(udid)
            async with RemoteServiceDiscoveryService((host, port)) as rsd:
                async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as sim:
                    await sim.set(latitude, longitude)
        else:
            lockdown = await device_service.get_lockdown(udid)
            await DtSimulateLocation(lockdown).set(latitude, longitude)

        # Update status
        status = self.get_status(udid)
        status.is_active = True
        status.latitude = latitude
        status.longitude = longitude
        status.mode = "gpx" if mode == "gpx" else "static"

        await ws_manager.broadcast(
            "location_updated",
            {
                "udid": udid,
                "latitude": latitude,
                "longitude": longitude,
                "mode": status.mode,
            },
        )

    async def clear_location(self, udid: str) -> None:
        """Clear simulated location and stop any running GPX route."""
        logger.info(f"Clearing simulated location for {udid}")
        await self.stop_gpx(udid)

        dev_info = device_service._devices_cache.get(udid)
        version_str = dev_info.product_version if dev_info else "17.0"
        is_ios17 = device_service.is_ios17_or_greater(version_str)

        try:
            if is_ios17:
                host, port = await tunnel_service.get_or_create_tunnel(udid)
                async with RemoteServiceDiscoveryService((host, port)) as rsd:
                    async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as sim:
                        await sim.clear()
            else:
                lockdown = await device_service.get_lockdown(udid)
                await DtSimulateLocation(lockdown).clear()
        except Exception as e:
            logger.warning(f"Error executing clear location command: {e}")

        status = self.get_status(udid)
        status.is_active = False
        status.latitude = None
        status.longitude = None
        status.mode = "idle"

        await ws_manager.broadcast("location_cleared", {"udid": udid})

    async def nudge_location(self, udid: str, direction: str, distance_meters: float) -> tuple[float, float]:
        """Nudge the current location in a cardinal direction (north, south, east, west)."""
        status = self.get_status(udid)
        current_lat = status.latitude if status.latitude is not None else 37.774929
        current_lng = status.longitude if status.longitude is not None else -122.419418

        delta_lat = 0.0
        delta_lng = 0.0

        # ~111,139 meters per degree latitude
        lat_step = distance_meters / 111139.0
        # Longitude degree length shrinks by cos(latitude)
        cos_lat = math.cos(math.radians(current_lat))
        if abs(cos_lat) < 1e-6:
            cos_lat = 1e-6
        lng_step = distance_meters / (111139.0 * cos_lat)

        if direction == "north":
            delta_lat = lat_step
        elif direction == "south":
            delta_lat = -lat_step
        elif direction == "east":
            delta_lng = lng_step
        elif direction == "west":
            delta_lng = -lng_step

        new_lat = max(-90.0, min(90.0, current_lat + delta_lat))
        new_lng = max(-180.0, min(180.0, current_lng + delta_lng))

        await self.set_location(udid, new_lat, new_lng, mode="static")
        return new_lat, new_lng

    async def play_gpx(
        self,
        udid: str,
        waypoints: list[Waypoint],
        loop: bool = False,
        speed_multiplier: float = 1.0,
    ) -> None:
        """Start managed GPX playback in an async task."""
        if not waypoints:
            raise ValueError("Waypoints list cannot be empty")

        await self.stop_gpx(udid)

        state = GPXPlaybackState(waypoints=waypoints, loop=loop, speed_multiplier=speed_multiplier)
        self._gpx_states[udid] = state

        status = self.get_status(udid)
        status.mode = "gpx"
        status.is_active = True
        status.gpx_total_points = len(waypoints)
        status.gpx_current_index = 0
        status.is_paused = False

        state.task = asyncio.create_task(self._run_gpx_playback(udid, state))

    async def _run_gpx_playback(self, udid: str, state: GPXPlaybackState) -> None:
        """Async worker iterating through GPX waypoints."""
        total = len(state.waypoints)
        logger.info(f"Starting GPX playback for {udid} with {total} points...")

        try:
            while not state.stop_event.is_set():
                for idx in range(state.current_index, total):
                    if state.stop_event.is_set():
                        break

                    # Handle pause
                    await state.pause_event.wait()
                    state.current_index = idx

                    wp = state.waypoints[idx]
                    await self.set_location(udid, wp.latitude, wp.longitude, mode="gpx")

                    # Calculate delay to next point
                    delay = 1.0
                    if idx + 1 < total:
                        next_wp = state.waypoints[idx + 1]
                        dist = haversine_distance_meters(
                            wp.latitude, wp.longitude, next_wp.latitude, next_wp.longitude
                        )
                        effective_speed = max(0.5, wp.speed_mps * state.speed_multiplier)
                        delay = max(0.2, dist / effective_speed)

                    status = self.get_status(udid)
                    status.gpx_current_index = idx

                    await ws_manager.broadcast(
                        "gpx_step",
                        {
                            "udid": udid,
                            "index": idx,
                            "total": total,
                            "latitude": wp.latitude,
                            "longitude": wp.longitude,
                            "delay_seconds": round(delay, 2),
                        },
                    )

                    # Sleep in small slices to respond immediately to stop/pause
                    elapsed = 0.0
                    step_slice = 0.2
                    while elapsed < delay and not state.stop_event.is_set():
                        await state.pause_event.wait()
                        await asyncio.sleep(min(step_slice, delay - elapsed))
                        elapsed += step_slice

                if not state.loop or state.stop_event.is_set():
                    break
                state.current_index = 0

            logger.info(f"GPX playback finished for {udid}")
        except asyncio.CancelledError:
            logger.info(f"GPX playback cancelled for {udid}")
        except Exception as e:
            logger.error(f"Error during GPX playback for {udid}: {e}")
        finally:
            status = self.get_status(udid)
            status.mode = "static" if status.is_active else "idle"
            status.is_paused = False
            await ws_manager.broadcast("gpx_finished", {"udid": udid})

    async def pause_gpx(self, udid: str) -> None:
        """Pause running GPX playback."""
        state = self._gpx_states.get(udid)
        if state:
            state.is_paused = True
            state.pause_event.clear()
            status = self.get_status(udid)
            status.is_paused = True
            await ws_manager.broadcast("gpx_paused", {"udid": udid})

    async def resume_gpx(self, udid: str) -> None:
        """Resume paused GPX playback."""
        state = self._gpx_states.get(udid)
        if state:
            state.is_paused = False
            state.pause_event.set()
            status = self.get_status(udid)
            status.is_paused = False
            await ws_manager.broadcast("gpx_resumed", {"udid": udid})

    async def stop_gpx(self, udid: str) -> None:
        """Stop and cancel running GPX playback."""
        state = self._gpx_states.pop(udid, None)
        if state:
            state.stop_event.set()
            state.pause_event.set()
            if state.task and not state.task.done():
                state.task.cancel()
            status = self.get_status(udid)
            status.mode = "static" if status.is_active else "idle"
            status.is_paused = False
            await ws_manager.broadcast("gpx_stopped", {"udid": udid})


simulation_service = SimulationService()
