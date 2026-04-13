"""Shared pytest fixtures for repo2xml tests."""

import pytest

from repo2xml.bundler import get_version


@pytest.fixture(autouse=True)
def _clear_version_cache() -> None:
    """Reset cached package version between tests to avoid cross-test leakage."""
    get_version.cache_clear()
