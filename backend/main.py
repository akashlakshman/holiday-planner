"""FastAPI application entry point for the Holiday Planner backend."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import flights, hotels, itinerary

app = FastAPI(
    title="Holiday Planner API",
    description="AI-powered holiday itinerary planner with live flight and hotel search.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(itinerary.router)
app.include_router(flights.router)
app.include_router(hotels.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "providers": {
            "gemini": bool(settings.gemini_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
        },
        "rapidapi": bool(settings.rapidapi_key),
        "supabase": bool(settings.supabase_url),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
