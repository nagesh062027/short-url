"""FastAPI HTTP layer for the URL shortener.

The HTTP layer is thin: it validates input via Pydantic, delegates to
:class:`ShortenerService`, and maps domain exceptions to HTTP status codes. All
business logic lives in the service, which keeps endpoints trivial and testable.

``create_app`` is a factory so tests can inject an in-memory repository and a
deterministic base URL.
"""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from .cache import LRUCache
from .schemas import (
    AnalyticsResponse,
    CreateUrlRequest,
    HealthResponse,
    UrlListResponse,
    UrlResponse,
)
from .service import (
    AliasTakenError,
    InvalidAliasError,
    InvalidUrlError,
    NotFoundError,
    ShortenerService,
)
from .storage import Repository

# Paths that must never be treated as short codes by the catch-all redirect.
_RESERVED = {"health", "docs", "redoc", "openapi.json", "favicon.ico", "api"}


def create_app(
    repository: Repository | None = None,
    base_url: str | None = None,
) -> FastAPI:
    app = FastAPI(
        title="URL Shortener",
        version="1.0.0",
        description="Scalable URL shortener with persistence and analytics.",
    )

    repo = repository or Repository(os.environ.get("URL_SHORTENER_DB", "urls.db"))
    resolved_base = base_url or os.environ.get("BASE_URL", "http://localhost:8000")
    service = ShortenerService(repo, LRUCache(), base_url=resolved_base)
    app.state.service = service

    def get_service() -> ShortenerService:
        return app.state.service

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    def health(svc: ShortenerService = Depends(get_service)) -> HealthResponse:
        return HealthResponse(status="ok", cached_entries=len(svc._cache))

    @app.post(
        "/api/urls",
        response_model=UrlResponse,
        status_code=201,
        tags=["urls"],
    )
    def create_url(
        body: CreateUrlRequest, svc: ShortenerService = Depends(get_service)
    ) -> UrlResponse:
        try:
            result = svc.create(body.url, body.custom_alias)
        except (InvalidUrlError, InvalidAliasError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AliasTakenError as exc:
            raise HTTPException(
                status_code=409, detail=f"Alias already in use: {exc}"
            ) from exc
        return UrlResponse(
            short_code=result.short_code,
            short_url=svc.short_url(result.short_code),
            long_url=result.long_url,
            created_at=result.created_at,
        )

    @app.get("/api/urls", response_model=UrlListResponse, tags=["urls"])
    def list_urls(
        limit: int = 50,
        offset: int = 0,
        svc: ShortenerService = Depends(get_service),
    ) -> UrlListResponse:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        records = svc.list_recent(limit=limit, offset=offset)
        items = [
            UrlResponse(
                short_code=r.short_code,
                short_url=svc.short_url(r.short_code),
                long_url=r.long_url,
                created_at=r.created_at,
            )
            for r in records
        ]
        return UrlListResponse(items=items, count=len(items))

    @app.get("/api/urls/{short_code}", response_model=UrlResponse, tags=["urls"])
    def get_url(
        short_code: str, svc: ShortenerService = Depends(get_service)
    ) -> UrlResponse:
        try:
            record = svc.get(short_code)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Unknown short code.") from exc
        return UrlResponse(
            short_code=record.short_code,
            short_url=svc.short_url(record.short_code),
            long_url=record.long_url,
            created_at=record.created_at,
        )

    @app.get(
        "/api/analytics/{short_code}",
        response_model=AnalyticsResponse,
        tags=["analytics"],
    )
    def get_analytics(
        short_code: str, svc: ShortenerService = Depends(get_service)
    ) -> AnalyticsResponse:
        try:
            summary = svc.analytics(short_code)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Unknown short code.") from exc
        return AnalyticsResponse(
            short_code=summary.short_code,
            total_clicks=summary.total_clicks,
            last_clicked=summary.last_clicked,
            clicks_by_day=summary.clicks_by_day,
            top_referrers=summary.top_referrers,
        )

    @app.get("/{short_code}", tags=["redirect"])
    def redirect(
        short_code: str,
        request: Request,
        svc: ShortenerService = Depends(get_service),
    ) -> RedirectResponse:
        if short_code in _RESERVED:
            raise HTTPException(status_code=404, detail="Not found.")
        try:
            long_url = svc.resolve(
                short_code,
                record_click=True,
                referrer=request.headers.get("referer"),
                user_agent=request.headers.get("user-agent"),
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Unknown short code.") from exc
        return RedirectResponse(url=long_url, status_code=302)

    return app


# Module-level app for `uvicorn app.main:app`.
app = create_app()
