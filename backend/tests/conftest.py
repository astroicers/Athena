"""Athena backend test fixtures."""

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend for tests."""
    return "asyncio"
