from app.models.base import Base
from app.models.watch_query import WatchQuery
from app.models.retailer_url import RetailerUrl
from app.models.scrape_result import ScrapeResult
from app.models.scrape_job import ScrapeJob
from app.models.alert import Alert
from app.models.app_settings import AppSettings

__all__ = [
    "Base",
    "WatchQuery",
    "RetailerUrl",
    "ScrapeResult",
    "ScrapeJob",
    "Alert",
    "AppSettings",
]
