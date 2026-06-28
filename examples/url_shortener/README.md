# URL Shortener Service

A scalable URL shortener with a REST API, durable persistence, and click
analytics. This service is the mandatory demo for the AI-assisted engineering
prototype and was planned by the `ai_eng` pipeline (see
[requirement.txt](requirement.txt)).

## Features

- Create short codes for long URLs (with optional custom aliases)
- HTTP 302 redirects from short code to original URL
- Durable persistence (SQLite by default, repository pattern is DB-agnostic)
- Click analytics: total clicks, clicks-by-day, top referrers, last click
- In-process LRU cache on the redirect hot path (Redis-swappable)
- Auto-generated OpenAPI docs at `/docs`

## Architecture (layers)

| Module | Responsibility |
| --- | --- |
| `app/shortener.py` | Pure Base62 encode/decode |
| `app/storage.py` | SQLite repository (persistence) |
| `app/cache.py` | Thread-safe LRU cache for hot-path reads |
| `app/analytics.py` | Click aggregation (read side) |
| `app/service.py` | Validation + business rules (orchestration) |
| `app/main.py` | FastAPI HTTP layer |

Short codes are derived from the row's auto-increment primary key via Base62,
so they are unique by construction and need no collision checks.

## Run it

From the repository root:

```powershell
pip install -r requirements.txt
cd examples/url_shortener
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs for interactive API documentation.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/urls` | Create a short URL. Body: `{ "url": "...", "custom_alias": "optional" }` |
| `GET` | `/api/urls` | List recent URLs (`?limit=&offset=`) |
| `GET` | `/api/urls/{code}` | Get details for a short code |
| `GET` | `/api/analytics/{code}` | Click analytics for a short code |
| `GET` | `/{code}` | Redirect (302) to the original URL and record a click |
| `GET` | `/health` | Liveness + cache size |

### Example

```powershell
# Create
curl -X POST http://localhost:8000/api/urls -H "Content-Type: application/json" -d '{ "url": "https://example.com/a/very/long/path" }'
# -> { "short_code": "g8", "short_url": "http://localhost:8000/g8", ... }

# Redirect
curl -i http://localhost:8000/g8        # HTTP/1.1 302 Found, Location: https://...

# Analytics
curl http://localhost:8000/api/analytics/g8
```

## Tests

```powershell
# from the repository root
pytest examples/url_shortener/tests -q
```

Coverage spans pure encoding, persistence, caching, analytics aggregation, and
full HTTP round-trips via FastAPI's test client.

## Scaling notes / trade-offs

- **Persistence:** SQLite is the zero-config default. Because all SQL is behind
  `Repository`, moving to PostgreSQL is a localized change.
- **Caching:** The LRU cache is in-process. For multi-instance deployments swap
  it for Redis behind the same `get/set/invalidate` interface.
- **Analytics:** Click capture is on the write path; aggregation is a separate
  read concern that can later move to a read replica or warehouse.
- **Code generation:** Key-based Base62 avoids the random-generate-and-check
  loop, trading guessability for simplicity (add a salt/hashids if needed).
