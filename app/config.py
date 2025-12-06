from pydantic import BaseSettings

class Settings(BaseSettings):
OPENAI_API_KEY: str
DATABASE_URL: str

```
class Config:
    env_file = ".env"  # Only used locally; Railway uses actual env vars
```

settings = Settings()
