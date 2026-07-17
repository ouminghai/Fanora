"""Optional Redis/Valkey cache with an in-memory fallback."""

import time
from typing import Protocol

from app.core.config import settings
from app.core.logging import logger

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore[assignment,misc]


class Cache(Protocol):
    backend_name: str

    async def initialize(self) -> None: ...

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def close(self) -> None: ...


class InMemoryCache:
    backend_name = "memory"

    def __init__(self, default_ttl: int) -> None:
        self._default_ttl = default_ttl
        self._values: dict[str, tuple[float, str]] = {}

    async def initialize(self) -> None:
        logger.info("cache_initialized", backend=self.backend_name)

    async def get(self, key: str) -> str | None:
        entry = self._values.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            self._values.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._values[key] = (time.monotonic() + (ttl or self._default_ttl), value)

    async def delete(self, key: str) -> None:
        self._values.pop(key, None)

    async def close(self) -> None:
        self._values.clear()


class RedisCache:
    backend_name = "redis"

    def __init__(self, url: str, default_ttl: int) -> None:
        self._url = url
        self._default_ttl = default_ttl
        self._client = None

    async def initialize(self) -> None:
        if Redis is None:
            raise RuntimeError("Install the 'cache' extra to enable Redis/Valkey")
        self._client = Redis.from_url(self._url, decode_responses=True)
        await self._client.ping()
        logger.info("cache_initialized", backend=self.backend_name)

    async def get(self, key: str) -> str | None:
        if not self._client:
            return None
        value = await self._client.get(key)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if self._client:
            await self._client.set(key, value, ex=ttl or self._default_ttl)

    async def delete(self, key: str) -> None:
        if self._client:
            await self._client.delete(key)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class CacheService:
    """Keeps the cache interface stable when Redis is unavailable."""

    def __init__(self) -> None:
        self._backend: Cache = InMemoryCache(settings.cache_ttl_seconds)

    @property
    def backend_name(self) -> str:
        return self._backend.backend_name

    async def initialize(self) -> None:
        if settings.cache_url:
            candidate = RedisCache(settings.cache_url, settings.cache_ttl_seconds)
            try:
                await candidate.initialize()
                self._backend = candidate
                return
            except Exception:
                logger.exception("distributed_cache_unavailable_using_memory")
        await self._backend.initialize()

    async def get(self, key: str) -> str | None:
        return await self._backend.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self._backend.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        await self._backend.delete(key)

    async def close(self) -> None:
        await self._backend.close()


cache_service = CacheService()
