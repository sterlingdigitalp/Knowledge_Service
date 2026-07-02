"""Diagnostics for live SearXNG integration tests."""

from __future__ import annotations

import pytest


def require_searxng_results(metadata: dict, *, endpoint: str) -> list:
    """Skip when SearXNG is reachable but all engines return no results."""
    results = metadata.get("results") or []
    if results:
        return results

    unresponsive = metadata.get("unresponsive_engines") or []
    pytest.skip(
        f"SearXNG at {endpoint} returned zero results. "
        f"Unresponsive engines: {unresponsive or 'none reported'}"
    )