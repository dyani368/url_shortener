import pytest 
from app.cache import redis
from unittest.mock import patch, AsyncMock

import json

class TestRedis:

    @pytest.fixture(autouse=True)
    def mock_redis(self):
        with patch("app.cache.redis.redis_client", new_callable=AsyncMock) as mock:
            self.mock_redis = mock
            yield mock

    def test_get_cache_key(self):
        assert redis.get_cache_key("abc") == "short:abc"
    
    @pytest.mark.asyncio
    async def test_get_cache_value_miss(self, mock_redis):
        mock_redis.get.return_value = None

        result = await redis.get_cache_value("abc")
        mock_redis.get.assert_called_once_with("short:abc")

        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_cache_value_hit(self, mock_redis):
        mock_redis.get.return_value = '{"id":1, "long_url": "https://docs.python.org/3/library/unittest.mock.html"}'
        result = await redis.get_cache_value("abc")

        mock_redis.get.assert_called_once_with("short:abc")

        assert result == {"id":1, "long_url": "https://docs.python.org/3/library/unittest.mock.html"}

    @pytest.mark.asyncio
    async def test_set_cache_value(self, mock_redis):
        await redis.set_cache_value("abc","https://docs.python.org/3/library/unittest.mock.html",1,60)
        expected_json = json.dumps({"id": 1, "long_url": "https://docs.python.org/3/library/unittest.mock.html"})

        mock_redis.setex.assert_called_once_with("short:abc",60,expected_json)
    
    @pytest.mark.asyncio
    async def test_delete_cached_url(self, mock_redis):
        await redis.delete_cached_url("abc")
        mock_redis.delete.assert_called_once_with("short:abc")
