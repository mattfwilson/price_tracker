"""Pydantic schemas for app settings API serialization."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppSettingsUpdate(BaseModel):
    default_schedule: str | None = None


class AppSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    default_schedule: str
    updated_at: datetime
