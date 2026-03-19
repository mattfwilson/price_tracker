"""Pydantic response schemas for scrape endpoints."""

from datetime import datetime

from pydantic import BaseModel


class ScrapeResultResponse(BaseModel):
    """Individual scrape result with computed price delta."""

    product_name: str
    price_cents: int
    retailer_name: str
    listing_url: str
    scraped_at: datetime
    direction: str  # "new" | "higher" | "lower" | "unchanged"
    delta_cents: int
    pct_change: float


class ScrapeJobResponse(BaseModel):
    """Response for on-demand scrape trigger."""

    job_id: int
    status: str  # "success" | "failed" | "partial_success"
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    results: list[ScrapeResultResponse]


class HistoryRecordResponse(BaseModel):
    """Single history record for a retailer URL."""

    id: int
    product_name: str
    price_cents: int
    retailer_name: str
    listing_url: str
    scraped_at: datetime
    direction: str
    delta_cents: int
    pct_change: float
