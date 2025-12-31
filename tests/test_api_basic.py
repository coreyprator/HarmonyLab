"""
Basic API tests for HarmonyLab backend.
Tests run against the deployed Cloud Run instance.
These are integration tests - skip during CI.
"""
import pytest
import httpx
import os

API_URL = "https://harmonylab-wmrla7fhwa-uc.a.run.app"

# Skip all tests in this file during CI
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Integration tests require deployed API"
)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Health check may timeout during CI due to database warmup")
async def test_health_check():
    """Test the health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


@pytest.mark.asyncio
async def test_api_docs_accessible():
    """Test that API documentation is accessible."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/docs")
        assert response.status_code == 200
