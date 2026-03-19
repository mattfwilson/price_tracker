"""Tests for scrape and price history API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.skip(reason="Plan 03-03")
@pytest.mark.asyncio
async def test_trigger_scrape(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-03")
@pytest.mark.asyncio
async def test_trigger_scrape_404(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-03")
@pytest.mark.asyncio
async def test_get_history(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-03")
@pytest.mark.asyncio
async def test_get_history_empty(client: AsyncClient):
    pass
