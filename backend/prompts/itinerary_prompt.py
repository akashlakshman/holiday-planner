"""Prompt builder for AI itinerary generation."""
from __future__ import annotations

from backend.models import TripRequest


def build_itinerary_prompt(req: TripRequest) -> str:
    dietary   = ", ".join(req.dietary_requirements) if req.dietary_requirements else "none"
    interests = ", ".join(req.interests) if req.interests else "general sightseeing"
    children  = f"yes, ages {', '.join(str(a) for a in req.children_ages)}" if req.has_children else "no"

    return f"""You are a concise expert travel planner. Create a day-by-day holiday itinerary as valid JSON only — no markdown, no extra text.

Trip:
- From: {req.origin_city} → {', '.join(req.destinations)}
- Dates: {req.departure_date} to {req.return_date} ({req.travellers} traveller(s), {req.cabin_class})
- Purpose: {req.trip_purpose} | Style: {req.travel_style} | Pace: {req.pace}
- Accommodation: {req.accommodation_preference}
- Interests: {interests}
- Dietary: {dietary}
- Children: {children} | Elderly: {"yes" if req.has_elderly else "no"} | Mobility needs: {"yes" if req.mobility_requirements else "no"}
{f"- Note: {req.special_instructions}" if req.special_instructions else ""}

Rules:
- Be specific — real place names, real restaurants, real neighbourhoods
- Be concise — 1-2 sentences per description, no filler
- Costs in local currency
- JSON only, exactly this schema:

{{
  "summary": "2 sentence trip overview",
  "highlights": ["highlight 1", "highlight 2", "highlight 3"],
  "days": [
    {{
      "day": 1,
      "date": "YYYY-MM-DD",
      "location": "City, Country",
      "title": "Day title",
      "morning":   {{"activity": "", "description": "", "tip": "", "cost": ""}},
      "afternoon": {{"activity": "", "description": "", "tip": "", "cost": ""}},
      "evening":   {{"activity": "", "description": "", "tip": "", "cost": ""}},
      "meals": {{"breakfast": "", "lunch": "", "dinner": ""}},
      "accommodation": {{"name": "", "area": ""}},
      "transport": "",
      "day_budget": ""
    }}
  ],
  "practical_info": {{
    "currency": "",
    "language": "",
    "transport_tip": "",
    "safety_tip": "",
    "packing": ["item1", "item2", "item3"]
  }},
  "estimated_cost": {{
    "accommodation": "",
    "food": "",
    "activities": "",
    "local_transport": "",
    "total_per_person": ""
  }}
}}"""
