"""Itinerary generation and persistence router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models import SaveItineraryRequest, TripRequest
from backend.services import ai_service, supabase_service

router = APIRouter(prefix="/api/itinerary", tags=["itinerary"])


@router.post("/generate")
async def generate_itinerary(req: TripRequest):
    """Generate a holiday itinerary using the chosen AI provider."""
    try:
        itinerary = await ai_service.generate_itinerary(req)
        return {"success": True, "itinerary": itinerary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/save")
async def save_itinerary(req: SaveItineraryRequest):
    """Persist a generated itinerary to Supabase."""
    payload = req.model_dump()
    itinerary_id = await supabase_service.save_itinerary(payload)
    return {"success": True, "id": itinerary_id}


@router.get("/{itinerary_id}")
async def get_itinerary(itinerary_id: str):
    """Retrieve a previously saved itinerary."""
    data = await supabase_service.get_itinerary(itinerary_id)
    if not data:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return data


@router.get("/")
async def list_itineraries():
    """List recent saved itineraries."""
    return await supabase_service.list_itineraries()
