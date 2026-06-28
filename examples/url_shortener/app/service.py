"""Business rules / orchestration for the URL shortener.

The service is the single place that enforces validation and wires together
storage, cache and analytics. Keeping these rules out of the HTTP layer means
they are reusable (CLI, batch jobs) and unit-testable without a web server.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .analytics import Analytics, AnalyticsSummary
from .cache import LRUCache
from .storage import AliasTakenError, Repository, UrlRecord

_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
_ALLOWED_SCHEMES = {"http", "https"}


class InvalidUrlError(ValueError):
    """Raised when the supplied long URL is not a valid http(s) URL."""


class InvalidAliasError(ValueError):
    """Raised when a custom alias does not meet the format rules."""


class NotFoundError(KeyError):
    """Raised when a short code does not resolve to a stored URL."""


@dataclass(frozen=True)
class ShortenResult:
    short_code: str
    long_url: str
    created_at: str


class ShortenerService:
    def __init__(
        self,
        repository: Repository,
        cache: LRUCache | None = None,
        base_url: str = "http://localhost:8000",
    ) -> None:
        self._repo = repository
        # NB: use an explicit None check, not `cache or LRUCache()` - LRUCache
        # defines __len__, so an empty (but valid) injected cache is falsy and
        # would be silently replaced.
        self._cache = cache if cache is not None else LRUCache()
        self._analytics = Analytics(repository)
        self._base_url = base_url.rstrip("/")

    # --- commands -------------------------------------------------------

    def create(self, long_url: str, custom_alias: str | None = None) -> ShortenResult:
        normalized = self._validate_url(long_url)
        if custom_alias is not None:
            self._validate_alias(custom_alias)
        record = self._repo.create_url(normalized, custom_alias)
        # Warm the cache so the first redirect is already a hit.
        self._cache.set(record.short_code, record.long_url)
        return self._to_result(record)

    def resolve(self, short_code: str, *, record_click: bool = False,
                referrer: str | None = None, user_agent: str | None = None) -> str:
        """Return the long URL for ``short_code`` or raise ``NotFoundError``.

        ``record_click`` is set by the redirect endpoint so analytics are
        captured; pure lookups (e.g. detail views) leave it ``False``.
        """

        long_url = self._cache.get(short_code)
        if long_url is None:
            record = self._repo.get_by_code(short_code)
            if record is None:
                raise NotFoundError(short_code)
            long_url = record.long_url
            self._cache.set(short_code, long_url)

        if record_click:
            self._repo.record_click(short_code, referrer, user_agent)
        return long_url

    # --- queries --------------------------------------------------------

    def get(self, short_code: str) -> UrlRecord:
        record = self._repo.get_by_code(short_code)
        if record is None:
            raise NotFoundError(short_code)
        return record

    def list_recent(self, limit: int = 50, offset: int = 0) -> list[UrlRecord]:
        return self._repo.list_urls(limit=limit, offset=offset)

    def analytics(self, short_code: str) -> AnalyticsSummary:
        # Confirm the code exists so analytics for a typo'd code 404s cleanly.
        self.get(short_code)
        return self._analytics.summary(short_code)

    def short_url(self, short_code: str) -> str:
        return f"{self._base_url}/{short_code}"

    # --- validation -----------------------------------------------------

    def _validate_url(self, long_url: str) -> str:
        candidate = (long_url or "").strip()
        if not candidate:
            raise InvalidUrlError("URL must not be empty.")
        parsed = urlparse(candidate)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES or not parsed.netloc:
            raise InvalidUrlError(
                "URL must be an absolute http(s) URL, e.g. https://example.com."
            )
        return candidate

    def _validate_alias(self, alias: str) -> None:
        if not _ALIAS_PATTERN.match(alias):
            raise InvalidAliasError(
                "Alias must be 3-32 chars of letters, digits, '-' or '_'."
            )

    def _to_result(self, record: UrlRecord) -> ShortenResult:
        return ShortenResult(
            short_code=record.short_code,
            long_url=record.long_url,
            created_at=record.created_at,
        )


__all__ = [
    "ShortenerService",
    "ShortenResult",
    "InvalidUrlError",
    "InvalidAliasError",
    "NotFoundError",
    "AliasTakenError",
]
