"""RapidAPI service — Sky Scrapper (flights) + Booking.com (hotels)."""
from __future__ import annotations

import httpx
from urllib.parse import quote as requests_quote
from typing import Any, Optional

from backend.config import settings

_RAPIDAPI_HOST_FLIGHTS = "sky-scrapper.p.rapidapi.com"
_RAPIDAPI_HOST_HOTELS  = "apidojo-booking-v1.p.rapidapi.com"

def _headers(host: str) -> dict:
    return {
        "x-rapidapi-key":  settings.rapidapi_key,
        "x-rapidapi-host": host,
        "Content-Type":    "application/json",
    }


# ---------------------------------------------------------------------------
# Flights — Sky Scrapper
# ---------------------------------------------------------------------------

async def _resolve_sky_entity(query: str, entity_type: str = "airport") -> Optional[dict]:
    """Search Sky Scrapper for an airport/city entity and return the first hit."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{_RAPIDAPI_HOST_FLIGHTS}/api/v1/flights/searchAirport",
                headers=_headers(_RAPIDAPI_HOST_FLIGHTS),
                params={"query": query, "locale": "en-US"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("data", [])
            if hits:
                return hits[0]
    except Exception:
        pass
    return None


async def search_flights(
    origin_city: str,
    destination_city: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "economy",
) -> dict[str, Any]:
    """Search for flights using Sky Scrapper (Skyscanner data)."""
    if not settings.rapidapi_key:
        return {"available": False, "reason": "RapidAPI key not configured"}

    try:
        # Resolve origin and destination entity IDs
        origin_entity      = await _resolve_sky_entity(origin_city)
        destination_entity = await _resolve_sky_entity(destination_city)

        if not origin_entity or not destination_entity:
            return {"available": False, "reason": "Could not resolve airport for one or both cities"}

        origin_id      = origin_entity.get("entityId") or origin_entity.get("skyId")
        destination_id = destination_entity.get("entityId") or destination_entity.get("skyId")
        origin_sky     = origin_entity.get("skyId", origin_city)
        dest_sky       = destination_entity.get("skyId", destination_city)

        cabin_map = {
            "ECONOMY": "economy", "PREMIUM_ECONOMY": "premium_economy",
            "BUSINESS": "business", "FIRST": "first",
        }
        cabin = cabin_map.get(cabin_class.upper(), "economy")

        params: dict[str, Any] = {
            "originSkyId":        origin_sky,
            "destinationSkyId":   dest_sky,
            "originEntityId":     origin_id,
            "destinationEntityId": destination_id,
            "date":               departure_date,
            "adults":             adults,
            "cabinClass":         cabin,
            "currency":           "GBP",
            "market":             "en-GB",
            "countryCode":        "GB",
        }
        if return_date:
            params["returnDate"] = return_date

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{_RAPIDAPI_HOST_FLIGHTS}/api/v2/flights/searchFlights",
                headers=_headers(_RAPIDAPI_HOST_FLIGHTS),
                params=params,
                timeout=20.0,
            )
            resp.raise_for_status()
            raw = resp.json()

        itineraries = (
            raw.get("data", {})
               .get("itineraries", [])
        )

        offers = []
        for item in itineraries[:5]:
            price   = item.get("price", {})
            legs    = item.get("legs", [])
            out_leg = legs[0] if legs else {}
            ret_leg = legs[1] if len(legs) > 1 else {}

            offers.append({
                "id": item.get("id"),
                "price": {
                    "total":      price.get("formatted", "N/A"),
                    "raw":        price.get("raw"),
                    "currency":   "GBP",
                    "per_person": str(round(float(price.get("raw", 0)) / adults, 2)) if price.get("raw") else "N/A",
                },
                "outbound": _format_leg(out_leg),
                "return":   _format_leg(ret_leg),
                "score":    item.get("score"),
            })

        return {"available": True, "offers": offers, "currency": "GBP"}

    except httpx.HTTPStatusError as exc:
        return {"available": False, "reason": f"Sky Scrapper API error {exc.response.status_code}"}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def _format_leg(leg: dict) -> dict:
    if not leg:
        return {}
    segments = leg.get("segments", [])
    formatted_segs = []
    for seg in segments:
        origin      = seg.get("origin", {})
        destination = seg.get("destination", {})
        formatted_segs.append({
            "from":          origin.get("displayCode") or origin.get("id"),
            "to":            destination.get("displayCode") or destination.get("id"),
            "departs":       seg.get("departure"),
            "arrives":       seg.get("arrival"),
            "carrier":       seg.get("marketingCarrier", {}).get("name"),
            "flight_number": seg.get("flightNumber"),
            "duration_mins": seg.get("durationInMinutes"),
        })
    return {
        "origin":          leg.get("origin", {}).get("displayCode"),
        "destination":     leg.get("destination", {}).get("displayCode"),
        "departure":       leg.get("departure"),
        "arrival":         leg.get("arrival"),
        "duration_mins":   leg.get("durationInMinutes"),
        "stops":           leg.get("stopCount", 0),
        "carriers":        [c.get("name") for c in leg.get("carriers", {}).get("marketing", [])],
        "segments":        formatted_segs,
    }


# ---------------------------------------------------------------------------
# Hotels — Booking.com (apidojo)
# ---------------------------------------------------------------------------

async def _get_booking_location_id(city: str) -> Optional[str]:
    """Resolve a city name to a Booking.com dest_id."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{_RAPIDAPI_HOST_HOTELS}/locations/auto-complete",
                headers=_headers(_RAPIDAPI_HOST_HOTELS),
                params={"text": city, "languagecode": "en-us"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data if isinstance(data, list) else data.get("data", [])
            for hit in hits:
                if hit.get("dest_type") in ("city", "region", "country"):
                    return str(hit.get("dest_id") or hit.get("id"))
            if hits:
                return str(hits[0].get("dest_id") or hits[0].get("id"))
    except Exception:
        pass
    return None


async def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    adults: int = 1,
    rooms: int = 1,
) -> dict[str, Any]:
    """Search for hotels on Booking.com via RapidAPI."""
    if not settings.rapidapi_key:
        return {"available": False, "reason": "RapidAPI key not configured"}

    try:
        dest_id = await _get_booking_location_id(city)
        if not dest_id:
            return {"available": False, "reason": f"Could not resolve Booking.com location for '{city}'"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{_RAPIDAPI_HOST_HOTELS}/properties/list",
                headers=_headers(_RAPIDAPI_HOST_HOTELS),
                params={
                    "dest_id":                   dest_id,
                    "search_type":               "city",
                    "arrival_date":              check_in,
                    "departure_date":            check_out,
                    "guest_qty":                 adults,
                    "room_qty":                  rooms,
                    "price_filter_currencycode": "GBP",
                    "languagecode":              "en-us",
                    "travel_purpose":            "leisure",
                    "order_by":                  "popularity",
                    "offset":                    0,
                },
                timeout=20.0,
            )
            resp.raise_for_status()
            raw = resp.json()

        results = raw.get("result", []) or raw.get("data", {}).get("result", [])

        hotels = []
        for h in results[:5]:
            hotel_id   = h.get("hotel_id") or h.get("id")
            hotel_name = h.get("hotel_name") or h.get("name", "")
            # Build a direct Booking.com URL with dates pre-filled
            booking_url = (
                h.get("url")
                or f"https://www.booking.com/hotel/search.html"
                  f"?ss={requests_quote(hotel_name)}"
                  f"&checkin={check_in}&checkout={check_out}"
                  f"&group_adults={adults}&no_rooms={rooms}"
            )
            # Fallback: Booking.com search URL
            search_url = (
                f"https://www.booking.com/search.html"
                f"?ss={requests_quote(hotel_name + ' ' + city)}"
                f"&checkin_year={check_in[:4]}&checkin_month={check_in[5:7]}&checkin_monthday={check_in[8:]}"
                f"&checkout_year={check_out[:4]}&checkout_month={check_out[5:7]}&checkout_monthday={check_out[8:]}"
                f"&group_adults={adults}&no_rooms={rooms}"
            )
            hotels.append({
                "hotel_id":        hotel_id,
                "name":            hotel_name,
                "rating":          h.get("class") or h.get("stars"),
                "review_score":    h.get("review_score"),
                "review_word":     h.get("review_score_word"),
                "city":            h.get("city") or city,
                "address":         h.get("address"),
                "price_per_night": h.get("min_total_price") or h.get("price_breakdown", {}).get("gross_price"),
                "currency":        h.get("currencycode", "GBP"),
                "url":             booking_url if h.get("url") else search_url,
                "thumb":           h.get("main_photo_url"),
            })

        return {"available": True, "hotels": hotels}

    except httpx.HTTPStatusError as exc:
        return {"available": False, "reason": f"Booking.com API error {exc.response.status_code}"}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
