from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RetailerUrl(Base, TimestampMixin):
    __tablename__ = "retailer_urls"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_query_id: Mapped[int] = mapped_column(ForeignKey("watch_queries.id"))
    url: Mapped[str] = mapped_column(String(2048))

    watch_query: Mapped["WatchQuery"] = relationship(
        back_populates="retailer_urls",
    )
    scrape_results: Mapped[list["ScrapeResult"]] = relationship(
        back_populates="retailer_url",
        cascade="all, delete-orphan",
    )
