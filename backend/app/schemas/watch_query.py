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
    schedule: str = "daily"  # daily, weekly, every_6h, every_12h

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


class WatchQueryUpdate(BaseModel):
    name: str | None = None
    threshold_cents: int | None = None
    is_active: bool | None = None
    schedule: str | None = None
    urls: list[str] | None = None  # if provided, replaces all URLs


class WatchQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    threshold_cents: int
    is_active: bool
    schedule: str
    retailer_urls: list[RetailerUrlResponse]
    created_at: datetime
    updated_at: datetime
