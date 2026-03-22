"""Pydantic schemas for watch query API serialization and validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class RetailerUrlCreate(BaseModel):
    url: str


class RetailerUrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    created_at: datetime


class WatchQueryCreate(BaseModel):
    name: str  # 1-255 chars
    threshold_cents: int  # positive integer
    urls: list[str]  # at least 1 URL
    schedule: str = "daily"  # daily, weekly, every_1h, every_3h, every_6h, every_12h
    pct_drop_threshold: float | None = None
    alert_cooldown_hours: int = 24

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("name must be 1-255 characters")
        return v

    @field_validator("threshold_cents")
    @classmethod
    def threshold_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("threshold_cents must be positive")
        return v

    @field_validator("urls")
    @classmethod
    def urls_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("at least one URL required")
        return v

    @field_validator("pct_drop_threshold")
    @classmethod
    def pct_threshold_range(cls, v: float | None) -> float | None:
        if v is not None and (v <= 0 or v > 100):
            raise ValueError("pct_drop_threshold must be >0 and <=100")
        return v

    @field_validator("alert_cooldown_hours")
    @classmethod
    def cooldown_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("alert_cooldown_hours must be >= 0")
        return v


class WatchQueryUpdate(BaseModel):
    name: str | None = None
    threshold_cents: int | None = None
    is_active: bool | None = None
    schedule: str | None = None
    urls: list[str] | None = None  # if provided, replaces all URLs
    pct_drop_threshold: float | None = None
    alert_cooldown_hours: int | None = None


class WatchQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    threshold_cents: int
    is_active: bool
    schedule: str
    pct_drop_threshold: float | None = None
    alert_cooldown_hours: int
    retailer_urls: list[RetailerUrlResponse]
    created_at: datetime
    updated_at: datetime


class LatestScrapeResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_name: str
    price_cents: int
    listing_url: str
    scraped_at: datetime
    direction: str  # "new" | "higher" | "lower" | "unchanged"
    delta_cents: int
    pct_change: float


class RetailerUrlWithLatest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    created_at: datetime
    latest_result: LatestScrapeResult | None = None


class WatchQueryDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    threshold_cents: int
    is_active: bool
    schedule: str
    pct_drop_threshold: float | None = None
    alert_cooldown_hours: int
    is_all_time_low: bool = False
    retailer_urls: list[RetailerUrlWithLatest]
    last_job_status: str | None = None
    last_job_error: str | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
