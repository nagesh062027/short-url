"""Integration tests for the HTTP API via FastAPI's test client."""

from __future__ import annotations


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_redirect(client) -> None:
    created = client.post("/api/urls", json={"url": "https://example.com/page"})
    assert created.status_code == 201
    code = created.json()["short_code"]

    redirect = client.get(f"/{code}")
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/page"


def test_redirect_unknown_code_returns_404(client) -> None:
    assert client.get("/doesnotexist").status_code == 404


def test_create_rejects_invalid_url(client) -> None:
    response = client.post("/api/urls", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_custom_alias_round_trip(client) -> None:
    response = client.post(
        "/api/urls", json={"url": "https://example.com", "custom_alias": "promo"}
    )
    assert response.status_code == 201
    assert response.json()["short_code"] == "promo"
    assert client.get("/promo").status_code == 302


def test_duplicate_alias_conflicts(client) -> None:
    payload = {"url": "https://example.com", "custom_alias": "dup"}
    assert client.post("/api/urls", json=payload).status_code == 201
    assert client.post("/api/urls", json=payload).status_code == 409


def test_invalid_alias_format_rejected(client) -> None:
    response = client.post(
        "/api/urls", json={"url": "https://example.com", "custom_alias": "a!"}
    )
    assert response.status_code == 422


def test_list_urls(client) -> None:
    client.post("/api/urls", json={"url": "https://one.example"})
    client.post("/api/urls", json={"url": "https://two.example"})
    response = client.get("/api/urls")
    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_analytics_endpoint_tracks_clicks(client) -> None:
    code = client.post(
        "/api/urls", json={"url": "https://example.com"}
    ).json()["short_code"]

    client.get(f"/{code}", headers={"referer": "https://news.example"})
    client.get(f"/{code}")

    analytics = client.get(f"/api/analytics/{code}")
    assert analytics.status_code == 200
    body = analytics.json()
    assert body["total_clicks"] == 2
    assert body["last_clicked"] is not None


def test_analytics_unknown_code_404(client) -> None:
    assert client.get("/api/analytics/missing").status_code == 404


def test_openapi_schema_served(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/urls" in response.json()["paths"]
