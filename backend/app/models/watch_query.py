from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WatchQuery(Base, TimestampMixin):
    __tablename__ = "watch_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    # Price threshold in integer cents (e.g., 1999 = $19.99)
    threshold_cents: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule: Mapped[str] = mapped_column(String(50), default="daily")

    retailer_urls: Mapped[list["RetailerUrl"]] = relationship(
        back_populates="watch_query",
        cascade="all, delete-orphan",
    )
    scrape_jobs: Mapped[list["ScrapeJob"]] = relationship(
        back_populates="watch_query",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="watch_query",
        cascade="all, delete-orphan",
    )
