"""Hotels router — Booking.com via RapidAPI."""
from __future__ import annotations

from fastapi import APIRouter

from backend.services import rapidapi_service

router = APIRouter(prefix="/api/hotels", tags=["hotels"])


@router.post("/search")
async def search_hotels(body: dict):
    """Search for hotel offers in a city."""
    return await rapidapi_service.search_hotels(
        city=body.get("city", ""),
        check_in=body.get("check_in", ""),
        check_out=body.get("check_out", ""),
        adults=body.get("adults", 1),
        rooms=body.get("rooms", 1),
    )
