import asyncio
from dataclasses import dataclass
from typing import Any
from src.core.config import logger
from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.remote.tunnel_service import (
    CoreDeviceTunnelService,
    create_core_device_tunnel_service_using_rsd,
    get_rsds,
    resume_remoted_if_required,
    stop_remoted_if_required,
)


@dataclass
class TunnelHandle:
    udid: str
    host: str
    port: int
    task: asyncio.Task[Any] | None
    stop_event: asyncio.Event


class TunnelService:
    """Manages CoreDevice / RSD tunnels for iOS 17+ devices."""

    def __init__(self) -> None:
        self._tunnels: dict[str, TunnelHandle] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_tunnel(self, udid: str, is_wifi: bool = False) -> tuple[str, int]:
        """Establish or reuse an existing RSD tunnel for an iOS 17+ device."""
        async with self._lock:
            if udid in self._tunnels:
                handle = self._tunnels[udid]
                if handle.task and not handle.task.done():
                    logger.info(f"Reusing existing tunnel for {udid} at {handle.host}:{handle.port}")
                    return handle.host, handle.port

            logger.info(f"Establishing new RSD tunnel for device {udid}...")
            ready_event = asyncio.Event()
            stop_event = asyncio.Event()
            tunnel_data: dict[str, Any] = {}

            task = asyncio.create_task(
                self._run_tunnel_loop(udid, is_wifi, ready_event, stop_event, tunnel_data)
            )

            try:
                # Wait up to 20 seconds for tunnel to establish
                await asyncio.wait_for(ready_event.wait(), timeout=20.0)
            except asyncio.TimeoutError:
                stop_event.set()
                task.cancel()
                raise RuntimeError(f"Timed out establishing tunnel to device {udid}")

            if "error" in tunnel_data:
                stop_event.set()
                task.cancel()
                raise RuntimeError(tunnel_data["error"])

            host = tunnel_data["host"]
            port = tunnel_data["port"]
            handle = TunnelHandle(
                udid=udid,
                host=host,
                port=port,
                task=task,
                stop_event=stop_event,
            )
            self._tunnels[udid] = handle
            logger.info(f"Tunnel successfully established: {host}:{port}")
            return host, port

    async def _run_tunnel_loop(
        self,
        udid: str,
        is_wifi: bool,
        ready_event: asyncio.Event,
        stop_event: asyncio.Event,
        tunnel_data: dict[str, Any],
    ) -> None:
        """Async worker that holds the tunnel context manager open while active."""
        try:
            stop_remoted_if_required()
            rsds = await get_rsds(bonjour_timeout=3.0, udid=udid)
            if not rsds:
                tunnel_data["error"] = f"No RSD service discovered for udid {udid}"
                ready_event.set()
                return

            rsd = rsds[0]
            service: CoreDeviceTunnelService = await create_core_device_tunnel_service_using_rsd(
                rsd, autopair=True
            )

            # Use TCP tunnel (more stable cross-platform on Windows than raw QUIC)
            async with service.start_tcp_tunnel() as tunnel_result:
                resume_remoted_if_required()
                tunnel_data["host"] = tunnel_result.address
                tunnel_data["port"] = tunnel_result.port
                ready_event.set()

                # Keep tunnel open until requested to stop
                while not stop_event.is_set():
                    await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info(f"Tunnel task for {udid} was cancelled.")
        except Exception as e:
            logger.error(f"Error in tunnel loop for {udid}: {e}")
            if not ready_event.is_set():
                tunnel_data["error"] = str(e)
                ready_event.set()
        finally:
            resume_remoted_if_required()

    async def close_tunnel(self, udid: str) -> None:
        """Close an open tunnel for a device."""
        async with self._lock:
            if udid in self._tunnels:
                handle = self._tunnels.pop(udid)
                handle.stop_event.set()
                if handle.task and not handle.task.done():
                    handle.task.cancel()
                logger.info(f"Tunnel closed for {udid}")

    async def close_all(self) -> None:
        """Close all tunnels during app shutdown."""
        udids = list(self._tunnels.keys())
        for udid in udids:
            await self.close_tunnel(udid)


tunnel_service = TunnelService()
