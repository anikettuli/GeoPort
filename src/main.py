import argparse
import asyncio
import socket
import sys
import threading
import time
import webbrowser
import pyuac
import uvicorn

from src.app import create_app
from src.core.config import (
    APP_NAME,
    APP_VERSION,
    IS_WINDOWS,
    PLATFORM_LABEL,
    logger,
    settings,
)

if IS_WINDOWS:
    # Set Windows selector event loop policy for pymobiledevice3 compatibility
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if TCP port is currently in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def find_available_port(preferred_port: int, host: str = "127.0.0.1") -> int:
    """Return preferred port if available, otherwise find a free dynamic port."""
    if not is_port_in_use(preferred_port, host):
        return preferred_port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def open_browser_delayed(url: str, delay_seconds: float = 1.2) -> None:
    """Launch the user's default browser after server initializes."""
    def _open():
        time.sleep(delay_seconds)
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.debug(f"Could not open browser automatically: {e}")

    threading.Thread(target=_open, daemon=True).start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION} - Modern iOS Location Simulator")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind to (default: 127.0.0.1)")
    parser.add_argument("--wireless", action="store_true", help="Enable wireless host mode (binds to LAN so you can control GeoPort from your iPhone Safari)")
    parser.add_argument("--port", type=int, default=54321, help="Port to listen on (default: 54321)")
    parser.add_argument("--no-browser", action="store_true", help="Skip automatically opening the web browser")
    parser.add_argument("--wifihost", type=str, help="Specify manual Wi-Fi IP address of the iOS device")
    parser.add_argument("--udid", type=str, help="Target specific device by UDID")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def run_app() -> None:
    args = parse_args()

    # Check administrator privileges on Windows
    if IS_WINDOWS:
        try:
            # Handle PyInstaller splash screen if bundled
            import pyi_splash  # type: ignore
            pyi_splash.update_text("GeoPort Loaded...")
            pyi_splash.close()
        except ImportError:
            pass

        if not pyuac.isUserAdmin():
            logger.warning("Running without Administrator privileges.")
            logger.info("Relaunching with Administrator permissions for Apple Mobile Device USB access...")
            try:
                pyuac.runAsAdmin()
                sys.exit(0)
            except Exception as e:
                logger.warning(f"Could not elevate permissions automatically: {e}")

    # Configure settings
    if args.wireless:
        settings.host = "0.0.0.0"
        settings.wireless_mode = True
    else:
        settings.host = args.host
        settings.wireless_mode = args.host in ("0.0.0.0", "")

    settings.open_browser = not args.no_browser
    settings.wifihost = args.wifihost
    settings.target_udid = args.udid
    settings.debug = args.debug

    # Assign port
    actual_port = find_available_port(args.port, "0.0.0.0" if settings.wireless_mode else settings.host)
    settings.port = actual_port

    from src.core.config import LOCAL_LAN_IP
    desktop_url = f"http://localhost:{actual_port}"
    mobile_url = f"http://{LOCAL_LAN_IP}:{actual_port}"

    logger.info("=" * 64)
    logger.info(f"  {APP_NAME} v{APP_VERSION} ({PLATFORM_LABEL})")
    logger.info(f"  Desktop URL: {desktop_url}")
    if settings.wireless_mode:
        logger.info(f"  Wireless iPhone Safari URL: {mobile_url}")
        logger.info("  -> Open this URL on your iPhone Safari to control GPS wirelessly!")
    else:
        logger.info("  Tip: Start with '--wireless' to control location directly from iPhone!")
    logger.info("=" * 64)

    if settings.open_browser:
        open_browser_delayed(server_url)

    app = create_app()

    # Run FastAPI via Uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="debug" if settings.debug else "warning",
    )


if __name__ == "__main__":
    run_app()
