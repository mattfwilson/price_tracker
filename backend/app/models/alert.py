from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    scrape_result_id: Mapped[int] = mapped_column(ForeignKey("scrape_results.id"))
    watch_query_id: Mapped[int] = mapped_column(ForeignKey("watch_queries.id"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    scrape_result: Mapped["ScrapeResult"] = relationship(
        back_populates="alert",
    )
    watch_query: Mapped["WatchQuery"] = relationship(
        back_populates="alerts",
    )
