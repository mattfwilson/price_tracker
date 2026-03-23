"""ScrapeUrlAttempt model for tracking per-URL scrape health."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScrapeUrlAttempt(Base):
    """Records every scrape attempt (success or failure) per retailer URL.

    Does NOT use TimestampMixin -- only scraped_at is needed, not created_at/updated_at.
    """

    __tablename__ = "scrape_url_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_url_id: Mapped[int] = mapped_column(ForeignKey("retailer_urls.id"), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    retailer_url: Mapped["RetailerUrl"] = relationship()
