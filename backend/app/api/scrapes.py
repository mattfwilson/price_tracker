"""Scrape and price history API endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["scrapes"])

# Browser manager instance (initialized lazily by scrape endpoints in Plan 03-03)
_browser_manager = None
