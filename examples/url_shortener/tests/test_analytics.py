"""Unit tests for analytics aggregation and the caching hot path."""

from __future__ import annotations

from app.analytics import Analytics
from app.cache import LRUCache
from app.service import ShortenerService
from app.storage import Repository


def test_summary_for_no_clicks(repo: Repository) -> None:
    record = repo.create_url("https://example.com")
    summary = Analytics(repo).summary(record.short_code)
    assert summary.total_clicks == 0
    assert summary.last_clicked is None


def test_summary_aggregates_clicks_and_referrers(repo: Repository) -> None:
    record = repo.create_url("https://example.com")
    repo.record_click(record.short_code, referrer="https://a.example")
    repo.record_click(record.short_code, referrer="https://a.example")
    repo.record_click(record.short_code, referrer="https://b.example")

    summary = Analytics(repo).summary(record.short_code)
    assert summary.total_clicks == 3
    assert summary.last_clicked is not None
    assert summary.top_referrers[0] == ("https://a.example", 2)
    assert sum(summary.clicks_by_day.values()) == 3


def test_resolve_uses_cache_after_first_lookup(repo: Repository) -> None:
    cache = LRUCache()
    service = ShortenerService(repo, cache=cache, base_url="http://test")
    result = service.create("https://example.com")

    # create() warms the cache, so resolving is an immediate hit.
    cache.clear()
    assert service.resolve(result.short_code) == "https://example.com"  # miss -> loads
    assert service.resolve(result.short_code) == "https://example.com"  # hit
    assert cache.hits >= 1


def test_lru_evicts_least_recently_used() -> None:
    cache = LRUCache(capacity=2)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.get("a")          # 'a' becomes most-recently used
    cache.set("c", "3")     # evicts 'b'
    assert cache.get("b") is None
    assert cache.get("a") == "1"
    assert cache.get("c") == "3"
