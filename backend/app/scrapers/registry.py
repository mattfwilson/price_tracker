"""Domain-based extractor registry."""

from __future__ import annotations

from urllib.parse import urlparse

from app.scrapers.base import BaseExtractor

_REGISTRY: dict[str, BaseExtractor] = {}


def register_extractor(extractor: BaseExtractor) -> None:
    """Register an extractor for its declared domain patterns."""
    for domain in extractor.domain_patterns:
        _REGISTRY[domain] = extractor


def get_extractor(url: str) -> BaseExtractor:
    """Resolve the correct extractor for a URL by hostname."""
    hostname = urlparse(url).hostname or ""
    extractor = _REGISTRY.get(hostname) or _REGISTRY.get(
        hostname.removeprefix("www.")
    )
    if not extractor:
        raise ValueError(f"No extractor registered for domain: {hostname}")
    return extractor
