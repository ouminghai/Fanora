import pytest

from app.adapters.monad import ChainConfigurationError, bytes32_from_hex


def test_bytes32_from_hex_accepts_prefixed_and_unprefixed_values() -> None:
    expected = bytes.fromhex("12" * 32)

    assert bytes32_from_hex("12" * 32) == expected
    assert bytes32_from_hex("0x" + "12" * 32) == expected


@pytest.mark.parametrize("value", ["12" * 31, "12" * 33, "zz" * 32])
def test_bytes32_from_hex_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ChainConfigurationError):
        bytes32_from_hex(value)
