import logging
import os
import sys
from pathlib import Path
from dataclasses import dataclass

APP_NAME = "GeoPort"
APP_VERSION = "5.0.0"

# Directories
HOME_DIR = Path.home()
GEOPORT_DATA_DIR = HOME_DIR / "GeoPort"
GEOPORT_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Operating system
PLATFORM_SYSTEM = sys.platform
IS_WINDOWS = PLATFORM_SYSTEM == "win32"
IS_MACOS = PLATFORM_SYSTEM == "darwin"
IS_LINUX = PLATFORM_SYSTEM.startswith("linux")

PLATFORM_LABEL = {
    "win32": "Windows",
    "darwin": "macOS",
    "linux": "Linux",
}.get(PLATFORM_SYSTEM, "Unknown")

# External endpoints
FUEL_API_URL = "https://projectzerothree.info/api.php?format=json"
GITHUB_REPO = "davesc63/GeoPort"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_SEARCH_URL = "https://photon.komoot.io/api"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("GeoPort")
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


@dataclass
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 54321
    open_browser: bool = True
    wifihost: str | None = None
    target_udid: str | None = None
    debug: bool = False


# Global config instance (initialized at main startup)
settings = AppConfig()
