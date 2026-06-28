"""Unit tests for the SQLite repository (persistence)."""

from __future__ import annotations

import pytest
from app.storage import AliasTakenError, Repository


def test_create_url_generates_unique_codes(repo: Repository) -> None:
    a = repo.create_url("https://a.example")
    b = repo.create_url("https://b.example")
    assert a.short_code != b.short_code
    assert a.long_url == "https://a.example"


def test_get_by_code_round_trips(repo: Repository) -> None:
    record = repo.create_url("https://example.com")
    fetched = repo.get_by_code(record.short_code)
    assert fetched is not None
    assert fetched.long_url == "https://example.com"


def test_get_by_code_returns_none_for_unknown(repo: Repository) -> None:
    assert repo.get_by_code("nope") is None


def test_custom_alias_is_used_verbatim(repo: Repository) -> None:
    record = repo.create_url("https://example.com", custom_code="promo")
    assert record.short_code == "promo"
    assert repo.get_by_code("promo") is not None


def test_duplicate_alias_raises(repo: Repository) -> None:
    repo.create_url("https://example.com", custom_code="dup")
    with pytest.raises(AliasTakenError):
        repo.create_url("https://other.example", custom_code="dup")


def test_list_urls_orders_newest_first(repo: Repository) -> None:
    repo.create_url("https://first.example")
    second = repo.create_url("https://second.example")
    listed = repo.list_urls()
    assert listed[0].short_code == second.short_code


def test_click_recording_and_counting(repo: Repository) -> None:
    record = repo.create_url("https://example.com")
    repo.record_click(record.short_code, referrer="https://news.example", user_agent="UA")
    repo.record_click(record.short_code)
    assert repo.count_clicks(record.short_code) == 2
    clicks = repo.get_clicks(record.short_code)
    assert clicks[0].referrer == "https://news.example"


def test_persistence_survives_new_connection(tmp_path) -> None:
    db = str(tmp_path / "urls.db")
    first = Repository(db)
    record = first.create_url("https://durable.example")

    reopened = Repository(db)
    fetched = reopened.get_by_code(record.short_code)
    assert fetched is not None
    assert fetched.long_url == "https://durable.example"
