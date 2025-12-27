"""
Tests for the health endpoint.

Basic sanity check that the testing infrastructure works correctly.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test that health endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_detailed_health(client: AsyncClient):
    """Test detailed health check."""
    response = await client.get("/health/detailed")
    # May return 200 or 503 depending on services
    assert response.status_code in [200, 503]
