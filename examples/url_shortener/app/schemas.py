"""Pydantic request/response schemas - the public API contract.

These models double as validation (incoming) and serialization (outgoing) and
are what FastAPI turns into the OpenAPI schema served at ``/docs``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateUrlRequest(BaseModel):
    url: str = Field(..., description="Absolute http(s) URL to shorten.",
                     examples=["https://example.com/some/long/path"])
    custom_alias: str | None = Field(
        default=None,
        description="Optional custom short code (3-32 chars: letters, digits, - _).",
        examples=["my-link"],
    )


class UrlResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    created_at: str


class UrlListResponse(BaseModel):
    items: list[UrlResponse]
    count: int


class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    last_clicked: str | None
    clicks_by_day: dict[str, int]
    top_referrers: list[tuple[str, int]]


class HealthResponse(BaseModel):
    status: str
    cached_entries: int


class ErrorResponse(BaseModel):
    detail: str
