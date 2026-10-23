from fastapi import APIRouter
from src.core.models import FuelResponse
from src.services.external_api_service import api_service

router = APIRouter(prefix="/api/fuel", tags=["Fuel Prices"])


@router.get("", response_model=FuelResponse)
async def get_fuel_data() -> FuelResponse:
    """Fetch live Australian fuel pricing data across states and regions."""
    return await api_service.get_fuel_prices()
