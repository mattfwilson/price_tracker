"""Pydantic schemas for scrape health API responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UrlHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    retailer_url_id: int
    url: str
    domain: str
    watch_query_id: int
    watch_query_name: str
    status: str  # "healthy" | "degraded" | "failing"
    success_count: int
    window_size: int
    last_success_at: datetime | None
    consecutive_failures: int
    last_error_type: str | None


class HealthListResponse(BaseModel):
    urls: list[UrlHealthResponse]
