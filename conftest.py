"""
Root conftest.py for AST-Healer.

Executed by pytest before any test collection. Handles two things:
1. Injects the google.antigravity stub into sys.path so CI can import
   main.py and app.py without the real Gemini SDK installed.
2. Auto-skips any test marked @pytest.mark.requires_api_key when
   GEMINI_API_KEY is absent.
"""

import os
import sys
from pathlib import Path

# Inject the google.antigravity stub BEFORE any project module is imported.
# The stub lives at tests/mocks/ and is only activated when the real package is not already installed.
try:
    import google.antigravity  # noqa: F401 — real package found, nothing to do
except ImportError:
    stub_path = str(Path(__file__).parent / "tests" / "mocks")
    if stub_path not in sys.path:
        sys.path.insert(0, stub_path)

# Custom markers
import pytest  # noqa: E402 — must come after path manipulation


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_api_key: skip this test when GEMINI_API_KEY is not set",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip LLM integration tests in CI when no API key is present."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        skip = pytest.mark.skip(
            reason="GEMINI_API_KEY not set — skipping LLM integration tests"
        )
        for item in items:
            if "requires_api_key" in item.keywords:
                item.add_marker(skip)
