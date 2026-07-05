"""Amadeus API service for flight and hotel search."""
from __future__ import annotations

import httpx
from typing import Any, Optional

from backend.config import settings


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

_access_token: Optional[str] = None
_token_expiry: float = 0.0


async def _get_token() -> str:
    import time

    global _access_token, _token_expiry
    if _access_token and time.time() < _token_expiry - 30:
        return _access_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.amadeus_base_url}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.amadeus_client_id,
                "client_secret": settings.amadeus_client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _access_token = data["access_token"]
        _token_expiry = time.time() + data.get("expires_in", 1799)
        return _access_token


# ---------------------------------------------------------------------------
# City → IATA lookup
# ---------------------------------------------------------------------------

async def city_to_iata(city_name: str) -> Optional[str]:
    """Resolve a free-text city name to its primary airport IATA code."""
    try:
        token = await _get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.amadeus_base_url}/v1/reference-data/locations",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "keyword": city_name,
                    "subType": "AIRPORT,CITY",
                    "page[limit]": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            locations = data.get("data", [])
            if locations:
                return locations[0].get("iataCode")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Flight search
# ---------------------------------------------------------------------------

async def search_flights(
    origin_iata: str,
    destination_iata: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY",
) -> dict[str, Any]:
    """Search for flight offers via Amadeus Flight Offers Search."""
    if not settings.amadeus_client_id:
        return {"available": False, "reason": "Amadeus credentials not configured"}

    try:
        token = await _get_token()
        params: dict[str, Any] = {
            "originLocationCode": origin_iata,
            "destinationLocationCode": destination_iata,
            "departureDate": departure_date,
            "adults": adults,
            "travelClass": cabin_class,
            "max": 5,
            "currencyCode": "GBP",
        }
        if return_date:
            params["returnDate"] = return_date

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.amadeus_base_url}/v2/shopping/flight-offers",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=20.0,
            )
            resp.raise_for_status()
            raw = resp.json()

        offers = raw.get("data", [])
        parsed = []
        for offer in offers[:5]:
            price = offer.get("price", {})
            itineraries = offer.get("itineraries", [])
            segments_out = itineraries[0]["segments"] if itineraries else []
            segments_ret = itineraries[1]["segments"] if len(itineraries) > 1 else []

            parsed.append(
                {
                    "id": offer.get("id"),
                    "price": {
                        "total": price.get("total"),
                        "currency": price.get("currency", "GBP"),
                        "per_person": str(
                            round(float(price.get("total", 0)) / adults, 2)
                        ),
                    },
                    "outbound": _format_segments(segments_out),
                    "return": _format_segments(segments_ret),
                    "validating_carrier": offer.get("validatingAirlineCodes", [None])[0],
                    "last_ticketing_date": offer.get("lastTicketingDate"),
                }
            )

        return {"available": True, "offers": parsed, "currency": "GBP"}

    except httpx.HTTPStatusError as exc:
        return {
            "available": False,
            "reason": f"Amadeus API error {exc.response.status_code}",
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def _format_segments(segments: list) -> list[dict]:
    result = []
    for seg in segments:
        dep = seg.get("departure", {})
        arr = seg.get("arrival", {})
        result.append(
            {
                "from": dep.get("iataCode"),
                "to": arr.get("iataCode"),
                "departs": dep.get("at"),
                "arrives": arr.get("at"),
                "carrier": seg.get("carrierCode"),
                "flight_number": seg.get("number"),
                "duration": seg.get("duration"),
                "aircraft": seg.get("aircraft", {}).get("code"),
            }
        )
    return result


# ---------------------------------------------------------------------------
# Hotel search
# ---------------------------------------------------------------------------

async def search_hotels(
    city_code: str,
    check_in: str,
    check_out: str,
    adults: int = 1,
) -> dict[str, Any]:
    """Search for hotel offers via Amadeus Hotel Search."""
    if not settings.amadeus_client_id:
        return {"available": False, "reason": "Amadeus credentials not configured"}

    try:
        token = await _get_token()

        # Step 1: get hotel IDs for the city
        async with httpx.AsyncClient() as client:
            list_resp = await client.get(
                f"{settings.amadeus_base_url}/v1/reference-data/locations/hotels/by-city",
                headers={"Authorization": f"Bearer {token}"},
                params={"cityCode": city_code, "radius": 5, "radiusUnit": "KM", "hotelSource": "ALL"},
                timeout=20.0,
            )
            list_resp.raise_for_status()
            hotel_ids = [h["hotelId"] for h in list_resp.json().get("data", [])[:20]]

        if not hotel_ids:
            return {"available": False, "reason": "No hotels found for city code"}

        # Step 2: get offers for those hotel IDs
        async with httpx.AsyncClient() as client:
            offers_resp = await client.get(
                f"{settings.amadeus_base_url}/v3/shopping/hotel-offers",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "hotelIds": ",".join(hotel_ids[:10]),
                    "checkInDate": check_in,
                    "checkOutDate": check_out,
                    "adults": adults,
                    "currency": "GBP",
                    "bestRateOnly": "true",
                },
                timeout=20.0,
            )
            offers_resp.raise_for_status()
            raw = offers_resp.json()

        hotels = []
        for item in raw.get("data", [])[:5]:
            hotel = item.get("hotel", {})
            offers = item.get("offers", [{}])
            best = offers[0] if offers else {}
            price = best.get("price", {})
            hotels.append(
                {
                    "hotel_id": hotel.get("hotelId"),
                    "name": hotel.get("name"),
                    "rating": hotel.get("rating"),
                    "latitude": hotel.get("latitude"),
                    "longitude": hotel.get("longitude"),
                    "price_per_night": price.get("total"),
                    "currency": price.get("currency", "GBP"),
                    "room_type": best.get("room", {}).get("typeEstimated", {}).get("category"),
                    "check_in": check_in,
                    "check_out": check_out,
                }
            )

        return {"available": True, "hotels": hotels}

    except httpx.HTTPStatusError as exc:
        return {
            "available": False,
            "reason": f"Amadeus API error {exc.response.status_code}",
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
