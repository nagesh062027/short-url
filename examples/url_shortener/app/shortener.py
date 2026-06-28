"""Base62 short-code encoding.

Short codes are derived deterministically from a database row id. Using the
monotonically increasing primary key guarantees uniqueness without a collision
check, while Base62 keeps codes short and URL-safe.

A fixed offset is added so the very first ids still produce codes of a pleasant
length (>= 2 chars) and small sequential ids are not trivially guessable as
"1", "2", ...

These functions are pure and side-effect free, which makes them trivial to unit
test exhaustively.
"""

from __future__ import annotations

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE = len(_ALPHABET)
_INDEX = {char: i for i, char in enumerate(_ALPHABET)}

# Offset keeps early codes a sensible length and avoids 1-char codes.
ID_OFFSET = 1000


def encode(number: int) -> str:
    """Encode a non-negative integer id into a Base62 short code."""

    if number < 0:
        raise ValueError("Cannot encode a negative number.")

    number += ID_OFFSET
    if number == 0:
        return _ALPHABET[0]

    chars: list[str] = []
    while number > 0:
        number, remainder = divmod(number, _BASE)
        chars.append(_ALPHABET[remainder])
    return "".join(reversed(chars))


def decode(code: str) -> int:
    """Decode a Base62 short code back into the original id."""

    if not code:
        raise ValueError("Cannot decode an empty code.")

    number = 0
    for char in code:
        if char not in _INDEX:
            raise ValueError(f"Invalid character in code: {char!r}")
        number = number * _BASE + _INDEX[char]
    return number - ID_OFFSET
