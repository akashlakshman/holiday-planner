from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class AIProvider(str, Enum):
    gemini = "gemini"
    anthropic = "anthropic"
    openai = "openai"


class TripRequest(BaseModel):
    # Core trip details
    origin_city: str = Field(..., description="City travelling from, e.g. 'London, UK'")
    destinations: List[str] = Field(..., description="List of destination cities")
    departure_date: str = Field(..., description="ISO date YYYY-MM-DD")
    return_date: str = Field(..., description="ISO date YYYY-MM-DD")
    travellers: int = Field(1, ge=1, le=20)
    cabin_class: str = Field("ECONOMY", description="ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST")

    # Questionnaire answers
    trip_purpose: str = Field("leisure", description="leisure | honeymoon | family | adventure | business")
    travel_style: str = Field("balanced", description="budget | balanced | luxury")
    dietary_requirements: List[str] = Field(default_factory=list)
    has_children: bool = False
    children_ages: List[int] = Field(default_factory=list)
    has_elderly: bool = False
    mobility_requirements: bool = False
    interests: List[str] = Field(default_factory=list)
    accommodation_preference: str = Field("hotel", description="hotel | airbnb | hostel | resort")
    pace: str = Field("moderate", description="relaxed | moderate | packed")
    special_instructions: Optional[str] = None
    ai_provider: AIProvider = AIProvider.gemini


class SaveItineraryRequest(BaseModel):
    trip_request: TripRequest
    itinerary: dict
    flights: Optional[dict] = None
    hotels: Optional[dict] = None
