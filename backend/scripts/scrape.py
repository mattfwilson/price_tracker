#!/usr/bin/env python
"""CLI validation script for scraping pipeline. Print-only, no DB writes."""
import asyncio
import sys
import os

# Add backend/ to sys.path so app.scrapers is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.base import ScrapeError
from app.scrapers.registry import get_extractor
from app.scrapers.browser import BrowserManager

# Trigger extractor registration by importing the scrapers package
import app.scrapers  # noqa: F401


async def main(urls: list[str]) -> None:
    browser_manager = BrowserManager()
    await browser_manager.start()
    try:
        for url in urls:
            print(f"\nURL: {url}")
            try:
                extractor = get_extractor(url)
                page = await browser_manager.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    data = await extractor.extract(page, url)
                    print(f"  Retailer:  {data.retailer_name}")
                    print(f"  Product:   {data.product_name}")
                    print(f"  Price:     ${data.price_cents / 100:.2f} ({data.price_cents} cents)")
                    print(f"  Listing:   {data.listing_url}")
                finally:
                    await page.close()
            except ScrapeError as e:
                print(f"  ERROR [{e.failure_type.value}]: {e.message}")
            except ValueError as e:
                print(f"  ERROR [UNKNOWN_RETAILER]: {e}")
    finally:
        await browser_manager.stop()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/scrape.py URL1 [URL2 ...]")
        sys.exit(1)
    asyncio.run(main(sys.argv[1:]))
