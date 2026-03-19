"""Alert Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    id: int
    watch_query_id: int
    watch_query_name: str
    product_name: str
    price_cents: int
    retailer_name: str
    listing_url: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertSSEPayload(BaseModel):
    alert_id: int
    watch_query_id: int
    watch_query_name: str
    product_name: str
    price_cents: int
    retailer_name: str
    listing_url: str
    created_at: datetime
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int
