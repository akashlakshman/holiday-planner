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
    dietary_requirements: List[str] = Field(default_factory=list, description="e.g. vegetarian, halal, gluten-free")
    has_children: bool = False
    children_ages: List[int] = Field(default_factory=list)
    has_elderly: bool = False
    mobility_requirements: bool = False
    interests: List[str] = Field(default_factory=list, description="e.g. history, food, nightlife, nature, art")
    accommodation_preference: str = Field("hotel", description="hotel | airbnb | hostel | resort")
    pace: str = Field("moderate", description="relaxed | moderate | packed")

    # Free-text
    special_instructions: Optional[str] = Field(None, description="Any specific instructions")

    # AI provider selection
    ai_provider: AIProvider = AIProvider.gemini


class FlightSearchRequest(BaseModel):
    origin_iata: str
    destination_iata: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    cabin_class: str = "ECONOMY"


class HotelSearchRequest(BaseModel):
    city_code: str
    check_in: str
    check_out: str
    adults: int = 1


class SaveItineraryRequest(BaseModel):
    trip_request: TripRequest
    itinerary: dict
    flights: Optional[dict] = None
    hotels: Optional[dict] = None


class ItineraryResponse(BaseModel):
    id: Optional[str] = None
    trip_request: TripRequest
    itinerary: dict
    flights: Optional[dict] = None
    hotels: Optional[dict] = None
