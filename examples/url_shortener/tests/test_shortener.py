"""Unit tests for Base62 short-code encoding (pure logic)."""

from __future__ import annotations

import pytest
from app import shortener


@pytest.mark.parametrize("number", [0, 1, 61, 62, 1000, 123456, 9_999_999])
def test_encode_decode_round_trip(number: int) -> None:
    assert shortener.decode(shortener.encode(number)) == number


def test_codes_are_unique_and_stable_for_sequential_ids() -> None:
    codes = [shortener.encode(i) for i in range(5000)]
    assert len(set(codes)) == len(codes)


def test_codes_are_url_safe() -> None:
    code = shortener.encode(987654)
    assert code.isalnum()


def test_encode_rejects_negative() -> None:
    with pytest.raises(ValueError):
        shortener.encode(-1)


def test_decode_rejects_empty() -> None:
    with pytest.raises(ValueError):
        shortener.decode("")


def test_decode_rejects_invalid_character() -> None:
    with pytest.raises(ValueError):
        shortener.decode("abc$")


def test_minimum_code_length_is_two() -> None:
    # The ID_OFFSET guarantees codes are at least two characters.
    assert all(len(shortener.encode(i)) >= 2 for i in range(100))
