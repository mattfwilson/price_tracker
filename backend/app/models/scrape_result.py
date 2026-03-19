from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScrapeResult(Base):
    """Scrape results are immutable -- no updated_at (no TimestampMixin)."""

    __tablename__ = "scrape_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_url_id: Mapped[int] = mapped_column(ForeignKey("retailer_urls.id"))
    scrape_job_id: Mapped[int] = mapped_column(ForeignKey("scrape_jobs.id"))
    product_name: Mapped[str] = mapped_column(String(500))
    # Price in integer cents (e.g., 1999 = $19.99)
    price_cents: Mapped[int] = mapped_column(Integer)
    listing_url: Mapped[str] = mapped_column(String(2048))
    retailer_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    retailer_url: Mapped["RetailerUrl"] = relationship(
        back_populates="scrape_results",
    )
    scrape_job: Mapped["ScrapeJob"] = relationship(
        back_populates="scrape_results",
    )
    alert: Mapped["Alert | None"] = relationship(
        back_populates="scrape_result",
        uselist=False,
    )
