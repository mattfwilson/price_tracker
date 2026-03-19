"""Get and update the app settings singleton row."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings


async def get_app_settings(db: AsyncSession) -> AppSettings:
    """Get the singleton app settings row (id=1)."""
    stmt = select(AppSettings).where(AppSettings.id == 1)
    result = await db.execute(stmt)
    return result.scalar_one()


async def update_app_settings(db: AsyncSession, **kwargs) -> AppSettings:
    """Update app settings fields. Supported: default_schedule."""
    settings = await get_app_settings(db)

    allowed_fields = {"default_schedule"}
    for key, value in kwargs.items():
        if key in allowed_fields and value is not None:
            setattr(settings, key, value)

    await db.flush()
    return settings
