from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    DEBUG: bool = True

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()