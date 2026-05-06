"""Shared test fixtures for ProofFlow MCP server tests."""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
