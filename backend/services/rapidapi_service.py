"""RapidAPI service — Sky Scrapper (flights) + Booking.com (hotels)."""
from __future__ import annotations

import asyncio
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

async def _resolve_sky_entity(query: str) -> Optional[dict]:
    """Resolve a city/airport query to {skyId, entityId, name}."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{_RAPIDAPI_HOST_FLIGHTS}/api/v1/flights/searchAirport",
                headers=_headers(_RAPIDAPI_HOST_FLIGHTS),
                params={"query": query, "locale": "en-US"},
                timeout=10.0,
            )
            resp.raise_for_status()
            hits = resp.json().get("data", [])
            for hit in hits:
                nav = hit.get("navigation", {})
                fp  = nav.get("relevantFlightParams", {})
                sky_id    = fp.get("skyId")
                entity_id = fp.get("entityId") or nav.get("entityId")
                if sky_id and entity_id:
                    return {"skyId": sky_id, "entityId": entity_id, "name": nav.get("localizedName", query)}
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
        # Resolve sequentially to avoid 429 rate limit on free tier
        origin_entity = await _resolve_sky_entity(origin_city)
        await asyncio.sleep(1)
        destination_entity = await _resolve_sky_entity(destination_city)

        if not origin_entity:
            return {"available": False, "reason": f"Could not resolve airport for '{origin_city}'"}
        if not destination_entity:
            return {"available": False, "reason": f"Could not resolve airport for '{destination_city}'"}

        cabin_map = {
            "ECONOMY": "economy", "PREMIUM_ECONOMY": "premium_economy",
            "BUSINESS": "business", "FIRST": "first",
        }
        cabin = cabin_map.get(cabin_class.upper(), "economy")

        params: dict[str, Any] = {
            "originSkyId":         origin_entity["skyId"],
            "destinationSkyId":    destination_entity["skyId"],
            "originEntityId":      origin_entity["entityId"],
            "destinationEntityId": destination_entity["entityId"],
            "date":                departure_date,
            "adults":              adults,
            "cabinClass":          cabin,
            "currency":            "GBP",
            "market":              "en-GB",
            "countryCode":         "GB",
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
# Hotels — Booking.com (apidojo) via list-by-map
# ---------------------------------------------------------------------------

# Approximate bounding boxes for common cities (lat_min, lat_max, lon_min, lon_max)
_CITY_BBOX: dict[str, tuple] = {
    "paris":     (48.815, 48.902, 2.224, 2.470),
    "london":    (51.385, 51.609, -0.351, 0.148),
    "rome":      (41.794, 41.987, 12.345, 12.614),
    "barcelona": (41.320, 41.470, 2.052, 2.228),
    "amsterdam": (52.278, 52.431, 4.729, 5.079),
    "new york":  (40.477, 40.917, -74.259, -73.700),
    "dubai":     (24.793, 25.359, 54.890, 55.565),
    "tokyo":     (35.530, 35.817, 139.580, 139.921),
    "bangkok":   (13.495, 13.952, 100.329, 100.934),
    "sydney":    (-34.168, -33.578, 150.502, 151.343),
    "singapore": (1.204, 1.471, 103.605, 104.083),
    "istanbul":  (40.802, 41.320, 28.448, 29.459),
    "lisbon":    (38.637, 38.802, -9.228, -9.092),
    "madrid":    (40.312, 40.644, -3.889, -3.518),
    "berlin":    (52.338, 52.675, 13.088, 13.761),
    "prague":    (49.941, 50.177, 14.224, 14.707),
    "vienna":    (48.117, 48.323, 16.182, 16.577),
    "athens":    (37.856, 38.084, 23.578, 23.897),
}

async def _get_city_bbox(city: str) -> Optional[tuple]:
    """Return (lat_min, lat_max, lon_min, lon_max) for a city."""
    key = city.lower().strip()
    # Try direct match or partial match in known cities
    for k, bbox in _CITY_BBOX.items():
        if k in key or key in k:
            return bbox
    # Fall back to Booking.com location lookup to get lat/lng
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{_RAPIDAPI_HOST_HOTELS}/locations/auto-complete",
                headers=_headers(_RAPIDAPI_HOST_HOTELS),
                params={"text": city, "languagecode": "en-us"},
                timeout=10.0,
            )
            resp.raise_for_status()
            hits = resp.json() if isinstance(resp.json(), list) else []
            if hits:
                lat = float(hits[0].get("latitude", 0))
                lon = float(hits[0].get("longitude", 0))
                if lat and lon:
                    delta = 0.15
                    return (lat - delta, lat + delta, lon - delta, lon + delta)
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
    """Search for hotels on Booking.com via list-by-map."""
    if not settings.rapidapi_key:
        return {"available": False, "reason": "RapidAPI key not configured"}

    try:
        bbox = await _get_city_bbox(city)
        if not bbox:
            return {"available": False, "reason": f"Could not resolve location bbox for '{city}'"}

        lat_min, lat_max, lon_min, lon_max = bbox
        bbox_str = f"{lat_min},{lat_max},{lon_min},{lon_max}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{_RAPIDAPI_HOST_HOTELS}/properties/list-by-map",
                headers=_headers(_RAPIDAPI_HOST_HOTELS),
                params={
                    "arrival_date":              check_in,
                    "departure_date":            check_out,
                    "room_qty":                  rooms,
                    "guest_qty":                 adults,
                    "bbox":                      bbox_str,
                    "search_id":                 "none",
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

        results = raw.get("result", [])

        hotels = []
        for h in results[:5]:
            hotel_name = h.get("hotel_name") or h.get("hotel_name_trans", "")
            raw_url    = h.get("url", "")
            # Append dates to the Booking.com hotel URL if we have one
            if raw_url and "booking.com" in raw_url:
                book_url = (
                    f"{raw_url}"
                    f"?checkin={check_in}&checkout={check_out}"
                    f"&group_adults={adults}&no_rooms={rooms}&selected_currency=GBP"
                )
            else:
                book_url = (
                    f"https://www.booking.com/search.html"
                    f"?ss={requests_quote(hotel_name + ' ' + city)}"
                    f"&checkin_year={check_in[:4]}&checkin_month={check_in[5:7]}&checkin_monthday={check_in[8:]}"
                    f"&checkout_year={check_out[:4]}&checkout_month={check_out[5:7]}&checkout_monthday={check_out[8:]}"
                    f"&group_adults={adults}&no_rooms={rooms}"
                )
            hotels.append({
                "hotel_id":        h.get("hotel_id"),
                "name":            hotel_name,
                "rating":          h.get("class"),
                "review_score":    h.get("review_score"),
                "review_word":     h.get("review_score_word"),
                "city":            h.get("city") or h.get("city_trans") or city,
                "address":         h.get("address_trans") or h.get("address"),
                "price_per_night": h.get("min_total_price"),
                "currency":        h.get("currencycode", "GBP"),
                "url":             book_url,
                "thumb":           h.get("main_photo_url"),
            })

        return {"available": True, "hotels": hotels}

    except httpx.HTTPStatusError as exc:
        return {"available": False, "reason": f"Booking.com API error {exc.response.status_code}"}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
