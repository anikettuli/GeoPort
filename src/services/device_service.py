import asyncio
from typing import Any
from src.core.config import logger
from src.core.models import DeviceInfo
from src.services.external_api_service import api_service
from pymobiledevice3.cli.mounter import auto_mount
from pymobiledevice3.exceptions import DeviceHasPasscodeSetError, NoDeviceConnectedError
from pymobiledevice3.lockdown import LockdownClient, create_using_tcp, create_using_usbmux
from pymobiledevice3.services.amfi import AmfiService
from pymobiledevice3.usbmux import list_devices


class DeviceService:
    def __init__(self) -> None:
        self._lockdowns: dict[str, LockdownClient] = {}
        self._devices_cache: dict[str, DeviceInfo] = {}
        self._lock = asyncio.Lock()

    async def list_connected_devices(self, wifihost: str | None = None, target_udid: str | None = None) -> list[DeviceInfo]:
        """Discover connected devices via usbmux and optional manual TCP/Wi-Fi host."""
        devices_list: list[DeviceInfo] = []
        user_country = api_service.get_user_country()

        # 1. Manual Wi-Fi Host if specified
        if wifihost:
            try:
                lockdown = await create_using_tcp(hostname=wifihost, identifier=target_udid)
                udid = lockdown.udid or target_udid or "wifi-device"
                info = lockdown.short_info
                dev = DeviceInfo(
                    udid=udid,
                    name=info.get("DeviceName", "Network Device"),
                    connection_type="Network",
                    product_version=info.get("ProductVersion", "Unknown"),
                    product_type=info.get("ProductType", "iPhone"),
                    device_class=info.get("DeviceClass", "iPhone"),
                    developer_mode=bool(lockdown.developer_mode_status),
                    wifi_state=True,
                    user_locale=user_country,
                    is_connected=True,
                )
                self._lockdowns[udid] = lockdown
                self._devices_cache[udid] = dev
                devices_list.append(dev)
            except Exception as e:
                logger.error(f"Failed to connect to manual Wi-Fi host {wifihost}: {e}")

        # 2. USB / Auto-detected usbmux devices
        try:
            raw_devices = await list_devices()
            for raw_dev in raw_devices:
                udid = raw_dev.serial
                conn_type = "WiFi" if raw_dev.connection_type == "Network" else "USB"

                try:
                    lockdown = await create_using_usbmux(
                        udid, connection_type=raw_dev.connection_type, autopair=True
                    )
                    info = lockdown.short_info

                    # Ensure Wi-Fi connection is enabled on device if supported
                    wifi_state = False
                    try:
                        wifi_state = bool(lockdown.enable_wifi_connections)
                        if not wifi_state:
                            lockdown.enable_wifi_connections = True
                            wifi_state = True
                    except Exception:
                        pass

                    dev_mode = False
                    try:
                        dev_mode = bool(lockdown.developer_mode_status)
                    except Exception:
                        pass

                    dev = DeviceInfo(
                        udid=udid,
                        name=info.get("DeviceName", f"iPhone ({udid[:8]})"),
                        connection_type=conn_type,
                        product_version=info.get("ProductVersion", "Unknown"),
                        product_type=info.get("ProductType", "iPhone"),
                        device_class=info.get("DeviceClass", "iPhone"),
                        developer_mode=dev_mode,
                        wifi_state=wifi_state,
                        user_locale=user_country,
                        is_connected=True,
                    )
                    self._lockdowns[udid] = lockdown
                    self._devices_cache[udid] = dev
                    devices_list.append(dev)
                except Exception as e:
                    logger.warning(f"Could not initialize lockdown for device {udid}: {e}")
                    # Include basic fallback entry
                    devices_list.append(
                        DeviceInfo(
                            udid=udid,
                            name=f"Device ({udid[:8]})",
                            connection_type=conn_type,
                            user_locale=user_country,
                        )
                    )
        except Exception as e:
            logger.error(f"Error listing usbmux devices: {e}")

        return devices_list

    async def get_lockdown(self, udid: str, connection_type: str = "USB") -> LockdownClient:
        """Get or recreate lockdown client for device."""
        if udid in self._lockdowns:
            return self._lockdowns[udid]

        conn_arg = "Network" if connection_type in ("WiFi", "Network") else "USB"
        lockdown = await create_using_usbmux(udid, connection_type=conn_arg, autopair=True)
        self._lockdowns[udid] = lockdown
        return lockdown

    async def check_developer_mode(self, udid: str) -> bool:
        """Query developer mode status on device."""
        try:
            lockdown = await self.get_lockdown(udid)
            return bool(lockdown.developer_mode_status)
        except Exception as e:
            logger.warning(f"Developer mode check failed for {udid}: {e}")
            return False

    async def enable_developer_mode(self, udid: str) -> tuple[bool, str | None]:
        """Attempt to turn on developer mode via AMFI."""
        try:
            lockdown = await self.get_lockdown(udid)
            logger.info(f"Enabling Developer Mode for {udid}...")
            await AmfiService(lockdown).enable_developer_mode()
            logger.info("Developer mode enabled, mounting developer image...")
            await auto_mount(lockdown)
            return True, None
        except DeviceHasPasscodeSetError:
            msg = (
                "Device has a passcode set.\n"
                "Please temporarily disable your passcode in Settings -> Face ID & Passcode, "
                "then click Enable Developer Mode again."
            )
            logger.error(msg)
            return False, msg
        except Exception as e:
            err = str(e)
            logger.error(f"Failed to enable developer mode: {err}")
            return False, err

    async def mount_developer_image(self, udid: str) -> tuple[bool, str | None]:
        """Mount the Developer Disk Image for the connected device."""
        try:
            lockdown = await self.get_lockdown(udid)
            logger.info(f"Mounting Developer Disk Image for {udid}...")
            await auto_mount(lockdown)
            return True, None
        except Exception as e:
            err = str(e)
            logger.error(f"Failed to mount developer image for {udid}: {err}")
            return False, err

    def is_ios17_or_greater(self, version_str: str) -> bool:
        """Check if iOS major version is 17 or higher."""
        try:
            major = int(version_str.split(".")[0])
            return major >= 17
        except Exception:
            return False


device_service = DeviceService()
