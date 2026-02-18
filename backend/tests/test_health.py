"""
Tests for health check endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_root(client: AsyncClient):
    """Test API root returns app info."""
    response = await client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data or "message" in data
