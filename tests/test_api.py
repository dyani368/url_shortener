from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware import rate_limiter
from app.services import analytics_service
from app.cache import redis


@pytest.fixture
def client(monkeypatch):
    async def allow_request(*, keys, args):
        return [1, 99]

    monkeypatch.setattr(rate_limiter, "rate_limit_script", allow_request)
    monkeypatch.setattr(redis, "get_cache_value", AsyncMock(return_value=None))
    monkeypatch.setattr(redis, "set_cache_value", AsyncMock())
    monkeypatch.setattr(analytics_service, "calculate_analytics", AsyncMock())
    test_client = TestClient(app)
    yield test_client
    test_client.close()


def _url(*, expiry=None):
    return SimpleNamespace(
        id=7,
        long_url="https://example.com/destination",
        short_code="abc123",
        expiry_date=expiry or datetime.now(UTC) + timedelta(days=1),
    )


def _mock_database(monkeypatch, url):
    result = MagicMock()
    result.scalars.return_value.first.return_value = url
    session = AsyncMock()
    session.execute.return_value = result

    @asynccontextmanager
    async def session_context():
        yield session

    monkeypatch.setattr("app.main.SessionLocal", session_context)
    return session


def test_live_endpoint(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_url_list_requires_authentication(client):
    response = client.get("/api/urls")
    assert response.status_code == 401


def test_redirect_cache_hit(client, monkeypatch):
    monkeypatch.setattr(
        redis,
        "get_cache_value",
        AsyncMock(return_value={"id": 7, "long_url": "https://example.com/cached"}),
    )

    response = client.get("/abc123", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/cached"
    redis.get_cache_value.assert_awaited_once_with("abc123")


def test_redirect_cache_miss_loads_and_caches_database_url(client, monkeypatch):
    _mock_database(monkeypatch, _url())

    response = client.get("/abc123", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/destination"
    redis.set_cache_value.assert_awaited_once()
    assert redis.set_cache_value.await_args.args[3] > 0


def test_redirect_survives_cache_read_failure(client, monkeypatch):
    from redis.exceptions import ConnectionError

    monkeypatch.setattr(redis, "get_cache_value", AsyncMock(side_effect=ConnectionError("Redis down")))
    _mock_database(monkeypatch, _url())

    response = client.get("/abc123", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/destination"


def test_redirect_survives_cache_write_failure(client, monkeypatch):
    from redis.exceptions import ConnectionError

    _mock_database(monkeypatch, _url())
    monkeypatch.setattr(redis, "set_cache_value", AsyncMock(side_effect=ConnectionError("Redis down")))

    response = client.get("/abc123", follow_redirects=False)

    assert response.status_code == 307


@pytest.mark.parametrize(
    ("database_url", "expected_status"),
    [
        (None, 404),
        (_url(expiry=datetime.now(UTC) - timedelta(seconds=1)), 410),
    ],
)
def test_redirect_handles_missing_and_expired_urls(client, monkeypatch, database_url, expected_status):
    _mock_database(monkeypatch, database_url)

    response = client.get("/abc123", follow_redirects=False)

    assert response.status_code == expected_status
