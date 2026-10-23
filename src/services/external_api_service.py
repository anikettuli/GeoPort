import asyncio
import locale
import re
import time
from typing import Any
import httpx
import pycountry

from src.core.config import (
    APP_VERSION,
    FUEL_API_URL,
    GITHUB_REPO,
    NOMINATIM_SEARCH_URL,
    PHOTON_SEARCH_URL,
    logger,
)
from src.core.models import FuelPriceEntry, FuelRegion, FuelResponse, SearchResult


class ExternalApiService:
    def __init__(self) -> None:
        self._fuel_cache: FuelResponse | None = None
        self._fuel_cache_time: float = 0.0
        self._fuel_ttl_seconds: float = 900.0  # 15 minutes
        self._cached_country: str | None = None

    def get_user_country(self) -> str:
        """Derive country name from local system locale, caching the result."""
        if self._cached_country:
            return self._cached_country

        try:
            loc, _ = locale.getlocale()
            if loc and "_" in loc:
                country_code = loc.split("_")[-1].upper()
                country = pycountry.countries.get(alpha_2=country_code)
                if country:
                    self._cached_country = country.name
                    return self._cached_country
        except Exception as e:
            logger.debug(f"Could not read country from system locale: {e}")

        self._cached_country = "Australia"  # Sensible default matching original fuel mode
        return self._cached_country

    async def search_locations(self, query: str) -> list[SearchResult]:
        """Search locations via coordinates regex or modern open geocoding APIs (Photon / Nominatim)."""
        clean_q = query.strip()
        if not clean_q:
            return []

        # 1. Check if user typed direct coordinates (e.g., "37.7749, -122.4194" or "37.7749 -122.4194")
        coord_match = re.match(r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)[,\s]+[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$", clean_q)
        if coord_match:
            parts = [float(p) for p in re.split(r"[,\s]+", clean_q) if p]
            if len(parts) >= 2:
                lat, lng = parts[0], parts[1]
                return [
                    SearchResult(
                        title=f"Coordinates: {lat:.5f}, {lng:.5f}",
                        subtitle="Direct coordinate input",
                        latitude=lat,
                        longitude=lng,
                    )
                ]

        results: list[SearchResult] = []

        # 2. Try Photon API (OpenStreetMap-based search by Komoot, fast and rich)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    PHOTON_SEARCH_URL,
                    params={"q": clean_q, "limit": 7},
                    headers={"User-Agent": f"GeoPort/{APP_VERSION}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for feature in data.get("features", []):
                        props = feature.get("properties", {})
                        geom = feature.get("geometry", {})
                        coords = geom.get("coordinates", [])
                        if len(coords) >= 2:
                            lng, lat = coords[0], coords[1]
                            name = props.get("name", clean_q)
                            details = [
                                props.get("street"),
                                props.get("city"),
                                props.get("state"),
                                props.get("country"),
                            ]
                            subtitle = ", ".join([d for d in details if d])
                            results.append(
                                SearchResult(
                                    title=name,
                                    subtitle=subtitle or None,
                                    latitude=lat,
                                    longitude=lng,
                                )
                            )
                    if results:
                        return results
        except Exception as e:
            logger.debug(f"Photon search failed, trying Nominatim fallback: {e}")

        # 3. Fallback to Nominatim API
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    NOMINATIM_SEARCH_URL,
                    params={"q": clean_q, "format": "json", "limit": 7, "addressdetails": 1},
                    headers={"User-Agent": f"GeoPort/{APP_VERSION}"},
                )
                if resp.status_code == 200:
                    for item in resp.json():
                        lat = float(item["lat"])
                        lng = float(item["lon"])
                        display_name = item.get("display_name", clean_q)
                        parts = display_name.split(", ")
                        title = parts[0]
                        subtitle = ", ".join(parts[1:4]) if len(parts) > 1 else None
                        results.append(
                            SearchResult(
                                title=title,
                                subtitle=subtitle,
                                latitude=lat,
                                longitude=lng,
                            )
                        )
        except Exception as e:
            logger.error(f"Nominatim search error: {e}")

        return results

    async def get_fuel_prices(self) -> FuelResponse:
        """Fetch Australian fuel price data with caching and TLS verification."""
        now = time.time()
        if self._fuel_cache and (now - self._fuel_cache_time) < self._fuel_ttl_seconds:
            return self._fuel_cache

        try:
            async with httpx.AsyncClient(timeout=10.0, verify=True) as client:
                resp = await client.get(FUEL_API_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    regions: list[FuelRegion] = []
                    for r in data.get("regions", []):
                        reg_name = r.get("region", "All")
                        entries: list[FuelPriceEntry] = []
                        for price_item in r.get("prices", []):
                            try:
                                p_val = float(price_item.get("price")) if price_item.get("price") else None
                            except (ValueError, TypeError):
                                p_val = None

                            entries.append(
                                FuelPriceEntry(
                                    type=price_item.get("type", "Unknown"),
                                    price=p_val,
                                    suburb=price_item.get("suburb"),
                                    state=price_item.get("state"),
                                    station=price_item.get("station"),
                                    latitude=price_item.get("lat"),
                                    longitude=price_item.get("lng"),
                                )
                            )
                        regions.append(FuelRegion(region=reg_name, prices=entries))

                    cached_response = FuelResponse(
                        regions=regions,
                        timestamp=data.get("updated") or str(time.strftime("%Y-%m-%d %H:%M:%S")),
                    )
                    self._fuel_cache = cached_response
                    self._fuel_cache_time = now
                    return cached_response
        except Exception as e:
            logger.error(f"Error fetching fuel price API: {e}")

        # Return empty response if unreachable or cache was empty
        return self._fuel_cache or FuelResponse(regions=[], timestamp=None)

    async def get_github_version_and_broadcast(self) -> tuple[str | None, str | None]:
        """Check for updates and broadcast notices from GitHub repository."""
        version_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/CURRENT_VERSION"
        broadcast_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/BROADCAST"

        github_version: str | None = None
        github_broadcast: str | None = None

        try:
            async with httpx.AsyncClient(timeout=5.0, verify=True) as client:
                v_res = await client.get(version_url)
                if v_res.status_code == 200:
                    github_version = v_res.text.strip()

                b_res = await client.get(broadcast_url)
                if b_res.status_code == 200:
                    github_broadcast = b_res.text.strip()
        except Exception as e:
            logger.debug(f"Failed to check GitHub version/broadcast: {e}")

        return github_version, github_broadcast


api_service = ExternalApiService()
