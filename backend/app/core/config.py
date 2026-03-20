from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_path: Path = Path("data/prices.db")
    busy_timeout: int = 5000  # milliseconds
    debug: bool = False

    # App
    app_name: str = "Price Scraper"

    # Best Buy API (optional — bypasses bot detection entirely)
    # Register free at https://developer.bestbuy.com
    # Set PRICE_SCRAPER_BESTBUY_API_KEY=<your_key> in .env to enable
    bestbuy_api_key: str | None = None

    model_config = {
        "env_file": ".env",
        "env_prefix": "PRICE_SCRAPER_",
    }


settings = Settings()
