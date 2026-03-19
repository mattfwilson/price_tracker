"""Scrape service orchestration with retry logic and job management."""

from __future__ import annotations

import asyncio
import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.models.retailer_url import RetailerUrl
from app.models.scrape_job import ScrapeJob
from app.repositories.scrape_result import (
    create_scrape_job,
    create_scrape_result,
    get_latest_scrape_result,
    update_scrape_job,
)
from app.scrapers.base import FailureType, ScrapeData, ScrapeError
from app.scrapers.browser import BrowserManager
from app.scrapers.registry import get_extractor

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Determine if an exception should trigger a retry."""
    if isinstance(exc, ScrapeError):
        return exc.failure_type != FailureType.BLOCKED
    return True  # Unknown exceptions are retryable


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def scrape_single_url(
    browser_manager: BrowserManager, url: str
) -> ScrapeData:
    """Scrape a single URL with retry logic for transient failures."""
    extractor = get_extractor(url)
    page = await browser_manager.new_page()
    try:
        await asyncio.sleep(random.uniform(0.5, 2.0))  # human simulation delay
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return await extractor.extract(page, url)
    except ScrapeError:
        raise
    except TimeoutError:
        raise ScrapeError(FailureType.NETWORK_ERROR, "page load timeout")
    except Exception as e:
        raise ScrapeError(FailureType.NETWORK_ERROR, str(e))
    finally:
        await page.close()


async def run_scrape_job(
    session: AsyncSession,
    watch_query_id: int,
    browser_manager: BrowserManager,
) -> ScrapeJob:
    """Orchestrate a scrape job: iterate URLs, store results, handle partial success."""
    job = await create_scrape_job(session, watch_query_id)

    # Load retailer URLs for this watch query
    stmt = select(RetailerUrl).where(
        RetailerUrl.watch_query_id == watch_query_id
    )
    result = await session.execute(stmt)
    urls = list(result.scalars().all())

    successes = 0
    failures = 0
    error_messages: list[str] = []

    for retailer_url in urls:
        try:
            data = await scrape_single_url(browser_manager, retailer_url.url)
            await create_scrape_result(
                session,
                retailer_url_id=retailer_url.id,
                scrape_job_id=job.id,
                product_name=data.product_name,
                price_cents=data.price_cents,
                listing_url=data.listing_url,
                retailer_name=data.retailer_name,
            )
            successes += 1
        except (ScrapeError, Exception) as e:
            failures += 1
            error_messages.append(f"{retailer_url.url}: {e}\n")
            logger.warning("Scrape failed for %s: %s", retailer_url.url, e)

    # Determine final status
    if failures == 0:
        status = "success"
    elif successes == 0:
        status = "failed"
    else:
        status = "partial_success"

    error_msg = "".join(error_messages) if error_messages else None
    await update_scrape_job(session, job, status=status, error_message=error_msg)

    return job


async def calculate_price_delta(
    session: AsyncSession,
    retailer_url_id: int,
    current_price_cents: int,
    previous_price_cents: int | None = None,
) -> dict:
    """Calculate price change vs most recent previous scrape for this retailer URL.

    When previous_price_cents is provided, uses that value directly instead of
    querying the database. This allows the history endpoint to compute deltas
    for consecutive pairs without extra DB lookups.

    Returns dict with keys:
    - direction: "new" | "higher" | "lower" | "unchanged"
    - delta_cents: int (current - previous, 0 for new)
    - pct_change: float (percentage change, rounded to 2 decimals, 0.0 for new or zero previous)
    """
    if previous_price_cents is not None:
        prev_price = previous_price_cents
    else:
        previous = await get_latest_scrape_result(session, retailer_url_id)
        if previous is None:
            return {"direction": "new", "delta_cents": 0, "pct_change": 0.0}
        prev_price = previous.price_cents
    delta = current_price_cents - prev_price

    if prev_price == 0:
        pct = 0.0
    else:
        pct = round((delta / prev_price) * 100, 2)

    if delta > 0:
        direction = "higher"
    elif delta < 0:
        direction = "lower"
    else:
        direction = "unchanged"

    return {"direction": direction, "delta_cents": delta, "pct_change": pct}
