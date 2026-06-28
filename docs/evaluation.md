# Evaluation: How Output Quality Was Validated

The prototype treats **validation as a first-class stage**, not an afterthought.
Nothing AI produces is accepted on trust. This document describes the checks, the
test strategy, and the limitations we are honest about.

## 1. The quality gate

`Validator` ([src/ai_eng/validator.py](../src/ai_eng/validator.py)) runs these
checks over the artifacts a plan claims to deliver:

| Check | What it proves | Failure mode it catches |
| --- | --- | --- |
| `artifacts_exist` | Every promised file is real | Hallucinated/forgotten files |
| `syntax` | All Python artifacts parse | Malformed AI output |
| `tests_present` | The plan ships tests for its code | Untested code slipping through |
| `security_scan` | No `eval`/`exec`/`shell=True`/hardcoded secrets | Risky AI idioms |
| `tests_pass` (opt-in) | The suite actually passes | Behavioural defects |

The gate passes only if **all** checks pass; the CLI exits non-zero otherwise so
CI can depend on it.

## 2. Test strategy

The repository has two test suites, both run by `pytest -q`:

**Prototype tests** (`tests/`):
- `test_analyzer.py` — requirement classification, ambiguity + assumption output.
- `test_decomposer.py` — template selection, topological ordering, cycle rejection.
- `test_validator.py` — each gate check, positive and negative.
- `test_orchestrator.py` — end-to-end pipeline + Markdown/JSON rendering.

**URL shortener tests** (`examples/url_shortener/tests/`):
- `test_shortener.py` — exhaustive Base62 round-trips, uniqueness, error cases.
- `test_storage.py` — CRUD, custom aliases, duplicate-alias conflict, durability
  across reconnects.
- `test_analytics.py` — click aggregation, referrer ranking, **cache hit/miss and
  LRU eviction**.
- `test_api.py` — HTTP round-trips: create, 302 redirect, 404, validation 422,
  alias 409, listing, analytics, OpenAPI schema served.

Current status: **56 tests passing.**

```powershell
pytest -q
pytest --cov=ai_eng --cov=app            # coverage report
```

## 3. A real defect the gate/tests caught

While building the service, an AI-idiomatic default `self._cache = cache or LRUCache()`
was used. Because `LRUCache` implements `__len__`, an *empty but valid* injected
cache is falsy, so the injected cache was silently discarded and replaced.

`test_resolve_uses_cache_after_first_lookup` failed (`cache.hits == 0`), exposing
it. The fix is an explicit identity check:

```python
self._cache = cache if cache is not None else LRUCache()
```

This is the methodology in action: a plausible-looking AI suggestion was wrong,
and a test — not trust — caught it. The engineer owns the fix.

## 4. Security & performance awareness

- **Input validation:** the service only accepts absolute `http(s)` URLs and
  strictly-formatted aliases, mitigating open-redirect and injection vectors.
- **No raw SQL string-building with user input:** all queries are parameterized.
- **Static scan:** the gate flags dangerous constructs in any artifact.
- **Hot-path performance:** redirects are served from an LRU cache; analytics
  aggregation is kept off the redirect path. Click capture is a single indexed
  insert.

## 5. Known limitations

- The **offline AI provider is deterministic**: it documents the assistance seam
  rather than generating novel code. Live generation requires `OPENAI_API_KEY`.
- **Planning is template-based.** Requirements without a matching template get a
  generic 4-step plan; richer plans require adding a template to `knowledge.py`.
- **Coverage is meaningful but not exhaustive.** Concurrency under heavy load and
  multi-instance cache coherency are reasoned about (see ARCHITECTURE.md) but not
  load-tested.
- **SQLite** is a single-writer engine; the design (repository pattern) supports a
  Postgres swap, but that migration is not implemented here.
- **Ambiguous requirements** proceed on documented assumptions that must be
  confirmed by a stakeholder before shipping.
