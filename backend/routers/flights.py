"""Flights router — returns deep links to Skyscanner and Google Flights."""
from __future__ import annotations

from fastapi import APIRouter

from backend.services.rapidapi_service import flight_deep_links

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.post("/search")
async def search_flights(body: dict):
    """Return pre-filled Skyscanner and Google Flights search URLs."""
    return flight_deep_links(
        origin_city=body.get("origin_city", ""),
        destination_city=body.get("destination_city", ""),
        departure_date=body.get("departure_date", ""),
        return_date=body.get("return_date"),
        adults=body.get("adults", 1),
        cabin_class=body.get("cabin_class", "ECONOMY"),
    )
