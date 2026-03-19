from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_query_id: Mapped[int] = mapped_column(ForeignKey("watch_queries.id"))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    watch_query: Mapped["WatchQuery"] = relationship(
        back_populates="scrape_jobs",
    )
    scrape_results: Mapped[list["ScrapeResult"]] = relationship(
        back_populates="scrape_job",
        cascade="all, delete-orphan",
    )
