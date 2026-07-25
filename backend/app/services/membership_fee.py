"""Fast, observable membership-fee reads with safe live verification."""

import asyncio
import time
from typing import Protocol

from app.adapters.monad import monad_contract_adapter
from app.core.cache import cache_service
from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import membership_fee_cache_total, membership_fee_rpc_duration_seconds


class FeeCache(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...


class FeeAdapter(Protocol):
    async def membership_fee(self) -> int: ...


class MembershipFeeService:
    """Serves status reads immediately while keeping mutations strongly verified."""

    def __init__(self, *, cache: FeeCache = cache_service, adapter: FeeAdapter = monad_contract_adapter) -> None:
        self._cache = cache
        self._adapter = adapter
        self._last_known_fee = settings.membership_fee_wei
        self._local_expires_at = 0.0
        self._refresh_task: asyncio.Task[int] | None = None
        self._context: tuple[str, int] | None = None

    def cache_key(self) -> str:
        address = settings.membership_payment_contract_address.lower() or "unconfigured"
        return f"membership-fee:{settings.monad_chain_id}:{address}"

    def _remember(self, fee: int) -> None:
        self._last_known_fee = fee
        self._local_expires_at = time.monotonic() + settings.membership_fee_cache_ttl_seconds

    def _sync_context(self) -> None:
        context = (self.cache_key(), settings.membership_fee_wei)
        if self._context == context:
            return
        self._context = context
        self._last_known_fee = settings.membership_fee_wei
        self._local_expires_at = 0.0

    async def _store(self, fee: int) -> None:
        self._remember(fee)
        try:
            await self._cache.set(
                self.cache_key(),
                str(fee),
                ttl=settings.membership_fee_cache_ttl_seconds,
            )
        except Exception:
            logger.warning("membership_fee_cache_write_failed")

    async def get_status_fee(self) -> int:
        """Return immediately from memory/cache/config and refresh stale data in the background."""

        self._sync_context()
        if not settings.membership_payment_contract_address:
            membership_fee_cache_total.labels("config").inc()
            return settings.membership_fee_wei
        if time.monotonic() < self._local_expires_at:
            membership_fee_cache_total.labels("memory").inc()
            return self._last_known_fee
        try:
            cached = await self._cache.get(self.cache_key())
        except Exception:
            cached = None
            logger.warning("membership_fee_cache_read_failed")
        if cached is not None:
            try:
                fee = int(cached)
            except ValueError:
                logger.warning("membership_fee_cache_value_invalid")
            else:
                self._remember(fee)
                membership_fee_cache_total.labels("shared").inc()
                return fee
        membership_fee_cache_total.labels("stale").inc()
        self._schedule_refresh()
        return self._last_known_fee

    def _schedule_refresh(self) -> None:
        if self._refresh_task is not None and not self._refresh_task.done():
            return
        self._refresh_task = asyncio.create_task(self.refresh())

    async def _read_rpc(self) -> int:
        started_at = time.perf_counter()
        result = "success"
        try:
            return await asyncio.wait_for(
                self._adapter.membership_fee(),
                timeout=settings.membership_fee_rpc_timeout_seconds,
            )
        except Exception:
            result = "error"
            raise
        finally:
            membership_fee_rpc_duration_seconds.labels(result).observe(time.perf_counter() - started_at)

    async def refresh(self) -> int:
        try:
            fee = await self._read_rpc()
        except Exception:
            membership_fee_cache_total.labels("refresh_error").inc()
            logger.warning("membership_fee_refresh_failed_using_stale_value")
            return self._last_known_fee
        await self._store(fee)
        membership_fee_cache_total.labels("refresh_success").inc()
        return fee

    async def wait_for_refresh(self) -> int:
        task = self._refresh_task
        if task is None:
            return self._last_known_fee
        return await asyncio.shield(task)

    async def get_live_fee(self) -> int:
        """Bypass status caches for payment/free-membership authorization."""

        self._sync_context()
        if not settings.membership_payment_contract_address:
            return settings.membership_fee_wei
        fee = await self._read_rpc()
        await self._store(fee)
        return fee

    async def set_fee(self, fee: int) -> None:
        self._sync_context()
        await self._store(fee)


membership_fee_service = MembershipFeeService()
