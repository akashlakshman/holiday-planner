from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

# Always resolve .env relative to this file (backend/.env)
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    # AI providers
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_ai_provider: str = "gemini"

    # RapidAPI (Sky Scrapper flights + Booking.com hotels)
    rapidapi_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:5500"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


settings = Settings()
