from typing import Any, Literal
from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    udid: str
    name: str = "Unknown Device"
    connection_type: str = "USB"  # USB, WiFi, Network
    product_version: str = "Unknown"
    product_type: str = "iPhone"
    device_class: str = "iPhone"
    developer_mode: bool = False
    wifi_state: bool = False
    user_locale: str | None = None
    is_connected: bool = False


class LocationSetRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    altitude: float | None = Field(default=0.0, description="Optional altitude in meters")


class NudgeRequest(BaseModel):
    direction: Literal["north", "south", "east", "west"]
    distance_meters: float = Field(default=10.0, gt=0, le=5000, description="Step distance in meters")


class Waypoint(BaseModel):
    latitude: float
    longitude: float
    speed_mps: float = Field(default=1.4, description="Speed in meters per second (1.4 m/s ~ 5 km/h)")


class GPXPlayRequest(BaseModel):
    waypoints: list[Waypoint]
    loop: bool = False
    speed_multiplier: float = Field(default=1.0, gt=0.1, le=10.0)


class SimulationStatus(BaseModel):
    udid: str
    is_active: bool = False
    latitude: float | None = None
    longitude: float | None = None
    mode: Literal["idle", "static", "gpx"] = "idle"
    gpx_current_index: int = 0
    gpx_total_points: int = 0
    is_paused: bool = False


class SearchResult(BaseModel):
    title: str
    subtitle: str | None = None
    latitude: float
    longitude: float
    bounding_box: list[float] | None = None


class FuelPriceEntry(BaseModel):
    type: str
    price: float | None = None
    suburb: str | None = None
    state: str | None = None
    station: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class FuelRegion(BaseModel):
    region: str
    prices: list[FuelPriceEntry] = []


class FuelResponse(BaseModel):
    regions: list[FuelRegion] = []
    timestamp: str | None = None


class SystemInfoResponse(BaseModel):
    app_version: str
    platform: str
    is_admin: bool
    sudo_message: str = ""
    local_lan_ip: str = "127.0.0.1"
    mobile_url: str = ""
    github_version: str | None = None
    github_broadcast: str | None = None
