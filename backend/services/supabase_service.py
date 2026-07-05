"""Supabase persistence service for saving and retrieving itineraries."""
from __future__ import annotations

from typing import Any, Optional

from backend.config import settings


def _get_client():
    from supabase import create_client  # type: ignore

    return create_client(settings.supabase_url, settings.supabase_anon_key)


async def save_itinerary(data: dict[str, Any]) -> Optional[str]:
    """Persist an itinerary to Supabase. Returns the generated row ID or None."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None

    try:
        client = _get_client()
        result = client.table("itineraries").insert(data).execute()
        rows = result.data
        if rows:
            return str(rows[0].get("id"))
    except Exception:
        pass
    return None


async def get_itinerary(itinerary_id: str) -> Optional[dict[str, Any]]:
    """Fetch a saved itinerary by ID."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None

    try:
        client = _get_client()
        result = (
            client.table("itineraries")
            .select("*")
            .eq("id", itinerary_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def list_itineraries(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent saved itineraries."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        return []

    try:
        client = _get_client()
        result = (
            client.table("itineraries")
            .select("id, created_at, trip_request")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []
