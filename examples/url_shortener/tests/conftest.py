"""Shared pytest fixtures for the URL shortener tests."""

from __future__ import annotations

from typing import Iterator

import pytest
from app.main import create_app
from app.service import ShortenerService
from app.storage import Repository

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore


@pytest.fixture
def repo() -> Iterator[Repository]:
    repository = Repository(":memory:")
    yield repository
    repository.close()


@pytest.fixture
def service(repo: Repository) -> ShortenerService:
    return ShortenerService(repo, base_url="http://test")


@pytest.fixture
def client(repo: Repository):
    if TestClient is None:  # pragma: no cover
        pytest.skip("fastapi/httpx not installed")
    app = create_app(repository=repo, base_url="http://test")
    return TestClient(app, follow_redirects=False)
