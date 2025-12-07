import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---- ENV VARS ----
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    THE_ODDS_API_KEY: str = os.getenv("THE_ODDS_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    class Config:
        extra = "allow"  # allow extra vars (Railway adds many)


# Create global settings instance
settings = Settings()

# Debug print (safe)
print("DEBUG DATABASE_URL:", repr(settings.DATABASE_URL))
