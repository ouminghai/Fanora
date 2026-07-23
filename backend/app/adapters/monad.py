"""Centralized Monad contract reads and operator-signed writes."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from web3 import Web3
from web3.contract import Contract

from app.core.config import settings


class ChainConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ConfirmedContractTransaction:
    transaction_hash: str
    block_number: int
    confirmations: int
    event_args: dict[str, Any]


def _load_abi(name: str) -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[3] / "shared" / "contracts" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))["abi"]


def bytes32_from_hex(value: str) -> bytes:
    """Convert a prefixed or unprefixed 32-byte hex value for contract calls."""
    normalized = value[2:] if value.startswith("0x") else value
    if len(normalized) != 64:
        raise ChainConfigurationError("Contract operation id must be exactly 32 bytes")
    try:
        return bytes.fromhex(normalized)
    except ValueError as error:
        raise ChainConfigurationError("Contract operation id must be hexadecimal") from error


class MonadContractAdapter:
    def __init__(self) -> None:
        self._write_lock = asyncio.Lock()
        self.membership_gateway_abi = _load_abi("FanoraMembershipGateway")
        self.identity_abi = _load_abi("FanoraMembershipIdentity")
        self.collectibles_abi = _load_abi("FanoraCollectibles")

    @staticmethod
    def operation_hash(value: str) -> str:
        return Web3.keccak(text=value).hex()

    @property
    def identity_configured(self) -> bool:
        return bool(settings.membership_identity_contract_address and settings.identity_minter_private_key)

    @property
    def identity_uri_manager_configured(self) -> bool:
        return bool(settings.membership_identity_contract_address and settings.identity_uri_manager_private_key)

    @property
    def membership_gateway_configured(self) -> bool:
        return bool(settings.membership_payment_contract_address and settings.membership_treasury_manager_private_key)

    @property
    def collectibles_configured(self) -> bool:
        return bool(
            settings.collectibles_contract_address
            and settings.collectible_type_manager_private_key
            and settings.collectible_minter_private_key
        )

    def _web3(self) -> Web3:
        web3 = Web3(Web3.HTTPProvider(settings.monad_rpc_url, request_kwargs={"timeout": 50}))
        if not web3.is_connected():
            raise ChainConfigurationError("Monad RPC is unavailable")
        if int(web3.eth.chain_id) != settings.monad_chain_id:
            raise ChainConfigurationError("Monad RPC chain id does not match configuration")
        return web3

    def _contract(self, web3: Web3, address: str, abi: list[dict[str, Any]]) -> Contract:
        if not Web3.is_address(address):
            raise ChainConfigurationError("Contract address is not configured")
        return web3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)

    def _send(
        self,
        *,
        private_key: str,
        contract_address: str,
        abi: list[dict[str, Any]],
        build_call: Callable[[Contract], Any],
        event_name: str,
    ) -> ConfirmedContractTransaction:
        if not private_key:
            raise ChainConfigurationError("Operator private key is not configured")
        web3 = self._web3()
        account = web3.eth.account.from_key(private_key)
        contract = self._contract(web3, contract_address, abi)
        call = build_call(contract)
        transaction = call.build_transaction(
            {
                "from": account.address,
                "nonce": web3.eth.get_transaction_count(account.address, "pending"),
                "chainId": settings.monad_chain_id,
                "gasPrice": web3.eth.gas_price,
            }
        )
        transaction["gas"] = int(web3.eth.estimate_gas(transaction) * 1.2)
        signed = account.sign_transaction(transaction)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=settings.chain_transaction_timeout_seconds,
            poll_latency=2,
        )
        if int(receipt["status"]) != 1:
            raise RuntimeError("Contract transaction reverted")
        current_block = int(web3.eth.block_number)
        confirmations = max(current_block - int(receipt["blockNumber"]) + 1, 0)
        events = getattr(contract.events, event_name)().process_receipt(receipt)
        event_args = dict(events[0]["args"]) if events else {}
        return ConfirmedContractTransaction(
            transaction_hash=Web3.to_hex(tx_hash),
            block_number=int(receipt["blockNumber"]),
            confirmations=confirmations,
            event_args=event_args,
        )

    async def mint_identity(
        self, wallet: str, level_id: int, metadata_uri: str, operation_hash: str
    ) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.identity_minter_private_key,
                contract_address=settings.membership_identity_contract_address,
                abi=self.identity_abi,
                build_call=lambda contract: contract.functions.mintIdentity(
                    Web3.to_checksum_address(wallet), level_id, metadata_uri, bytes32_from_hex(operation_hash)
                ),
                event_name="IdentityMinted",
            )

    async def update_membership_level(
        self, token_id: int, level_id: int, metadata_uri: str, operation_hash: str
    ) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.identity_level_manager_private_key,
                contract_address=settings.membership_identity_contract_address,
                abi=self.identity_abi,
                build_call=lambda contract: contract.functions.updateMembershipLevel(
                    token_id, level_id, metadata_uri, bytes32_from_hex(operation_hash)
                ),
                event_name="MembershipLevelUpdated",
            )

    async def update_identity_metadata(
        self, token_id: int, metadata_uri: str, operation_hash: str
    ) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.identity_uri_manager_private_key,
                contract_address=settings.membership_identity_contract_address,
                abi=self.identity_abi,
                build_call=lambda contract: contract.functions.updateIdentityMetadata(
                    token_id, metadata_uri, bytes32_from_hex(operation_hash)
                ),
                event_name="IdentityMetadataUpdated",
            )

    async def membership_gateway_balance(self) -> int:
        def load() -> int:
            web3 = self._web3()
            return int(web3.eth.get_balance(Web3.to_checksum_address(settings.membership_payment_contract_address)))

        if not settings.membership_payment_contract_address:
            raise ChainConfigurationError("Membership payment contract is not configured")
        return await asyncio.to_thread(load)

    async def membership_fee(self) -> int:
        def load() -> int:
            web3 = self._web3()
            contract = self._contract(
                web3,
                settings.membership_payment_contract_address,
                self.membership_gateway_abi,
            )
            return int(contract.functions.membershipFee().call())

        if not settings.membership_payment_contract_address:
            raise ChainConfigurationError("Membership payment contract is not configured")
        return await asyncio.to_thread(load)

    async def set_membership_fee(self, amount: int) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.membership_treasury_manager_private_key,
                contract_address=settings.membership_payment_contract_address,
                abi=self.membership_gateway_abi,
                build_call=lambda contract: contract.functions.setMembershipFee(amount),
                event_name="MembershipFeeUpdated",
            )

    async def withdraw_membership_fees(self, amount: int | None = None) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.membership_treasury_manager_private_key,
                contract_address=settings.membership_payment_contract_address,
                abi=self.membership_gateway_abi,
                build_call=(
                    (lambda contract: contract.functions.withdrawAll())
                    if amount is None
                    else (lambda contract: contract.functions.withdraw(amount))
                ),
                event_name="FundsWithdrawn",
            )

    async def create_token_type(self, payload: dict[str, Any]) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.collectible_type_manager_private_key,
                contract_address=settings.collectibles_contract_address,
                abi=self.collectibles_abi,
                build_call=lambda contract: contract.functions.createTokenType(
                    payload["token_id"],
                    payload["category"],
                    payload["metadata_uri"],
                    payload["max_supply"],
                    payload["per_wallet_limit"],
                    payload["mint_start"],
                    payload["mint_end"],
                    payload["transferable"],
                ),
                event_name="TokenTypeCreated",
            )

    async def update_collectible_metadata(self, token_id: int, metadata_uri: str) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.collectible_uri_manager_private_key,
                contract_address=settings.collectibles_contract_address,
                abi=self.collectibles_abi,
                build_call=lambda contract: contract.functions.updateTokenMetadata(token_id, metadata_uri),
                event_name="TokenMetadataUpdated",
            )

    async def mint_collectible(
        self, wallet: str, token_id: int, amount: int, claim_hash: str
    ) -> ConfirmedContractTransaction:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._send,
                private_key=settings.collectible_minter_private_key,
                contract_address=settings.collectibles_contract_address,
                abi=self.collectibles_abi,
                build_call=lambda contract: contract.functions.mintCollectible(
                    Web3.to_checksum_address(wallet), token_id, amount, bytes32_from_hex(claim_hash)
                ),
                event_name="CollectibleMinted",
            )


monad_contract_adapter = MonadContractAdapter()
