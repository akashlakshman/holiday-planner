"""RapidAPI service — Booking.com hotels + flight deep links."""
from __future__ import annotations

import httpx
from urllib.parse import quote
from typing import Any, Optional

from backend.config import settings

_RAPIDAPI_HOST_HOTELS = "apidojo-booking-v1.p.rapidapi.com"


def _headers(host: str) -> dict:
    return {
        "x-rapidapi-key":  settings.rapidapi_key,
        "x-rapidapi-host": host,
        "Content-Type":    "application/json",
    }


# ---------------------------------------------------------------------------
# Flights — deep links only (Skyscanner + Google Flights)
# No live API: free flight APIs have too low rate limits to be reliable.
# ---------------------------------------------------------------------------

def flight_deep_links(
    origin_city: str,
    destination_city: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY",
) -> dict[str, Any]:
    """Return pre-filled Skyscanner and Google Flights search URLs."""
    dep = departure_date.replace("-", "")
    ret = return_date.replace("-", "") if return_date else ""

    cabin_map = {
        "ECONOMY": "economy", "PREMIUM_ECONOMY": "premium_economy",
        "BUSINESS": "business", "FIRST": "first",
    }
    cabin = cabin_map.get(cabin_class.upper(), "economy")

    skyscanner = (
        f"https://www.skyscanner.net/transport/flights/"
        f"{quote(origin_city.lower())}/{quote(destination_city.lower())}/"
        f"{dep}/{ret}/"
        f"?adults={adults}&cabinclass={cabin}&rtn={'1' if return_date else '0'}"
    )

    google = (
        f"https://www.google.com/travel/flights"
        f"?q=Flights+from+{quote(origin_city)}+to+{quote(destination_city)}"
        f"+on+{departure_date}"
        + (f"+returning+{return_date}" if return_date else "")
    )

    return {
        "available": True,
        "deep_links": True,
        "origin":      origin_city,
        "destination": destination_city,
        "departure":   departure_date,
        "return":      return_date,
        "adults":      adults,
        "cabin_class": cabin_class,
        "skyscanner":  skyscanner,
        "google_flights": google,
    }


# ---------------------------------------------------------------------------
# Hotels — Booking.com via list-by-map
# ---------------------------------------------------------------------------

# Bounding boxes for common cities (lat_min, lat_max, lon_min, lon_max)
_CITY_BBOX: dict[str, tuple] = {
    "paris":         (48.815, 48.902,  2.224,   2.470),
    "london":        (51.385, 51.609, -0.351,   0.148),
    "rome":          (41.794, 41.987, 12.345,  12.614),
    "barcelona":     (41.320, 41.470,  2.052,   2.228),
    "amsterdam":     (52.278, 52.431,  4.729,   5.079),
    "new york":      (40.477, 40.917, -74.259, -73.700),
    "dubai":         (24.793, 25.359, 54.890,  55.565),
    "tokyo":         (35.530, 35.817, 139.580, 139.921),
    "bangkok":       (13.495, 13.952, 100.329, 100.934),
    "sydney":        (-34.168,-33.578, 150.502, 151.343),
    "singapore":     ( 1.204,  1.471, 103.605, 104.083),
    "istanbul":      (40.802, 41.320,  28.448,  29.459),
    "lisbon":        (38.637, 38.802,  -9.228,  -9.092),
    "madrid":        (40.312, 40.644,  -3.889,  -3.518),
    "berlin":        (52.338, 52.675,  13.088,  13.761),
    "prague":        (49.941, 50.177,  14.224,  14.707),
    "vienna":        (48.117, 48.323,  16.182,  16.577),
    "athens":        (37.856, 38.084,  23.578,  23.897),
    "miami":         (25.709, 25.856, -80.330, -80.130),
    "los angeles":   (33.703, 34.337,-118.668,-118.155),
    "san francisco": (37.630, 37.929,-122.514,-122.355),
    "toronto":       (43.580, 43.855, -79.639, -79.116),
    "mexico city":   (19.197, 19.593, -99.366, -98.940),
    "buenos aires":  (-34.750,-34.524, -58.531, -58.334),
    "cape town":     (-34.178,-33.837,  18.330,  18.700),
    "cairo":         (29.937, 30.214,  31.100,  31.510),
    "mumbai":        (18.894, 19.269,  72.776,  73.059),
    "delhi":         (28.405, 28.881,  76.840,  77.350),
    "beijing":       (39.760, 40.200, 116.160, 116.680),
    "shanghai":      (31.020, 31.530, 121.190, 121.730),
    "hong kong":     (22.193, 22.563, 113.837, 114.433),
    "seoul":         (37.429, 37.701, 126.764, 127.184),
    "kuala lumpur":  ( 3.020,  3.270, 101.570, 101.800),
    "bali":          (-8.850, -8.340, 114.940, 115.620),
    "phuket":        ( 7.760,  8.190,  98.240,  98.450),
}


async def _get_city_bbox(city: str) -> Optional[tuple]:
    """Return (lat_min, lat_max, lon_min, lon_max) for a city."""
    key = city.lower().strip()
    for k, bbox in _CITY_BBOX.items():
        if k in key or key in k:
            return bbox
    # Fall back to Booking.com location lookup for unlisted cities
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
            return {"available": False, "reason": f"Could not resolve location for '{city}'"}

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
            results = resp.json().get("result", [])

        hotels = []
        for h in results[:5]:
            hotel_name = h.get("hotel_name") or h.get("hotel_name_trans", "")
            raw_url    = h.get("url", "")
            if raw_url and "booking.com" in raw_url:
                book_url = (
                    f"{raw_url}"
                    f"?checkin={check_in}&checkout={check_out}"
                    f"&group_adults={adults}&no_rooms={rooms}&selected_currency=GBP"
                )
            else:
                book_url = (
                    f"https://www.booking.com/search.html"
                    f"?ss={quote(hotel_name + ' ' + city)}"
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
            })

        return {"available": True, "hotels": hotels}

    except httpx.HTTPStatusError as exc:
        return {"available": False, "reason": f"Booking.com API error {exc.response.status_code}"}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
