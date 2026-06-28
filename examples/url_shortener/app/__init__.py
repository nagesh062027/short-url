"""URL shortener demo package.

A small but production-shaped FastAPI service that was planned by the
``ai_eng`` pipeline (see ``examples/url_shortener/requirement.txt``). The package
is intentionally layered so each concern is independently testable:

* :mod:`app.shortener` - pure Base62 encode/decode.
* :mod:`app.storage`   - SQLite repository (persistence).
* :mod:`app.cache`     - LRU cache for the redirect hot path.
* :mod:`app.analytics` - click capture + aggregation.
* :mod:`app.service`   - orchestration / business rules.
* :mod:`app.main`      - HTTP layer (FastAPI).
"""
