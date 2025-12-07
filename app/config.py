# app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    ODDS_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

