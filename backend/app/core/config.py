from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_path: Path = Path("data/prices.db")
    busy_timeout: int = 5000  # milliseconds
    debug: bool = False

    # App
    app_name: str = "Price Scraper"

    model_config = {
        "env_file": ".env",
        "env_prefix": "PRICE_SCRAPER_",
    }


settings = Settings()
