"""
Pytest configuration for AST-Healer.

Tests that invoke the Gemini API are skipped automatically in CI
when GEMINI_API_KEY is not set as a repository secret.
"""

import os
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_api_key: mark test as requiring GEMINI_API_KEY to run",
    )


def pytest_collection_modifyitems(config, items):
    """Skip LLM tests when API key is absent."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        skip_marker = pytest.mark.skip(
            reason="GEMINI_API_KEY not set — skipping LLM integration tests"
        )
        for item in items:
            if "requires_api_key" in item.keywords:
                item.add_marker(skip_marker)
