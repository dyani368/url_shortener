import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# 1. We mock the redis client BEFORE importing the middleware 
# so it doesn't crash on register_script()
with patch("app.cache.redis.redis_client") as imported_mock_redis:
    from app.middleware import rate_limiter

class TestRateLimiter:
    
    @pytest.mark.asyncio
    async def test_bypass_docs(self):
        mock_request = MagicMock()
        mock_request.url.path = "/docs"

        mock_call_next = AsyncMock(return_value=MagicMock())

        response = await rate_limiter.check_request(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    @patch("app.middleware.rate_limiter.rate_limit_script", new_callable=AsyncMock)
    async def test_allowed_request(self, mock_script):
        # rate_limit_script() returns [1, 99] → allowed=1, tokens_left=99
        mock_script.return_value = [1, 99]

        mock_request = MagicMock()
        mock_request.url.path = "/abc"          # redirect path
        mock_request.client.host = "127.0.0.1"

        mock_call_next = AsyncMock(return_value=MagicMock(headers={}))

        response = await rate_limiter.check_request(mock_request, mock_call_next)

        mock_call_next.assert_called_once()
        assert response.headers["X-RateLimit-Remaining"] == "99"


    @pytest.mark.asyncio
    @patch("app.middleware.rate_limiter.rate_limit_script", new_callable=AsyncMock)
    async def test_blocked_request(self, mock_script):
        # rate_limit_script() returns [0, 0] → blocked
        mock_script.return_value = [0, 0]

        mock_request = MagicMock()
        mock_request.url.path = "/abc"
        mock_request.client.host = "127.0.0.1"

        mock_call_next = AsyncMock()

        response = await rate_limiter.check_request(mock_request, mock_call_next)

        mock_call_next.assert_not_called()       # should NOT pass through
        assert response.status_code == 429

    @pytest.mark.asyncio
    @patch("app.middleware.rate_limiter.rate_limit_script", new_callable=AsyncMock)
    async def test_backend_failure_returns_503(self, mock_script):
        from redis.exceptions import ConnectionError

        mock_script.side_effect = ConnectionError("Redis unavailable")
        mock_request = MagicMock()
        mock_request.url.path = "/abc"
        mock_request.client.host = "127.0.0.1"
        mock_call_next = AsyncMock()

        response = await rate_limiter.check_request(mock_request, mock_call_next)

        assert response.status_code == 503
        assert response.headers["Retry-After"] == "1"
        mock_call_next.assert_not_called()
