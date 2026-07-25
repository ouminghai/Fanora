import asyncio

from app.core.config import settings
from app.services.membership_fee import MembershipFeeService


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self.values[key] = value


class BlockingFeeAdapter:
    def __init__(self, fee: int) -> None:
        self.fee = fee
        self.calls = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def membership_fee(self) -> int:
        self.calls += 1
        self.started.set()
        await self.release.wait()
        return self.fee


async def test_status_fee_returns_fallback_without_waiting_for_rpc(monkeypatch):
    monkeypatch.setattr(settings, "membership_payment_contract_address", "0x" + "12" * 20)
    monkeypatch.setattr(settings, "membership_fee_wei", 0)
    cache = FakeCache()
    adapter = BlockingFeeAdapter(25)
    service = MembershipFeeService(cache=cache, adapter=adapter)

    fee = await asyncio.wait_for(service.get_status_fee(), timeout=0.1)

    assert fee == 0
    await asyncio.wait_for(adapter.started.wait(), timeout=0.1)
    adapter.release.set()
    await service.wait_for_refresh()
    assert cache.values[service.cache_key()] == "25"
    assert await service.get_status_fee() == 25


async def test_status_fee_cache_hit_does_not_call_rpc(monkeypatch):
    monkeypatch.setattr(settings, "membership_payment_contract_address", "0x" + "34" * 20)
    cache = FakeCache()
    adapter = BlockingFeeAdapter(99)
    service = MembershipFeeService(cache=cache, adapter=adapter)
    cache.values[service.cache_key()] = "7"

    assert await service.get_status_fee() == 7
    assert adapter.calls == 0


async def test_live_fee_bypasses_cached_value_and_updates_cache(monkeypatch):
    monkeypatch.setattr(settings, "membership_payment_contract_address", "0x" + "56" * 20)
    monkeypatch.setattr(settings, "membership_fee_rpc_timeout_seconds", 1.0)
    cache = FakeCache()
    adapter = BlockingFeeAdapter(11)
    service = MembershipFeeService(cache=cache, adapter=adapter)
    cache.values[service.cache_key()] = "0"

    task = asyncio.create_task(service.get_live_fee())
    await asyncio.wait_for(adapter.started.wait(), timeout=0.1)
    adapter.release.set()

    assert await task == 11
    assert cache.values[service.cache_key()] == "11"
    assert adapter.calls == 1
