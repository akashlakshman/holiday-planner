"""Flights router — Sky Scrapper via RapidAPI."""
from __future__ import annotations

from fastapi import APIRouter

from backend.services import rapidapi_service

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.post("/search")
async def search_flights(body: dict):
    """Search for flight offers between two cities."""
    return await rapidapi_service.search_flights(
        origin_city=body.get("origin_city", ""),
        destination_city=body.get("destination_city", ""),
        departure_date=body.get("departure_date", ""),
        return_date=body.get("return_date"),
        adults=body.get("adults", 1),
        cabin_class=body.get("cabin_class", "economy"),
    )
