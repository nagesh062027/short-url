# Example Scenario — Brownfield

**Requirement:** *"Optimize database queries for analytics."*

A brownfield scenario changes existing, working code. The risk is **regression**,
so the method leads with characterization tests before any change.

## 1. Analysis

The analyzer classifies this as **brownfield** (keyword: *optimize*) and flags an
ambiguity: *optimize for what, and by how much?* Documented assumption: reduce
analytics read latency on hot codes without changing API responses.

Baseline (current code, [analytics.py](../../examples/url_shortener/app/analytics.py)):

- `Analytics.summary()` calls `Repository.get_clicks()` which returns **all** click
  rows and aggregates them in Python.
- For a popular link with millions of clicks this loads every row to compute a
  count and a per-day histogram — O(rows) memory and time per request.

## 2. Refactoring plan (engineer-led)

| ID | Task | Depends on | AI assist | Validation focus |
| --- | --- | --- | --- | --- |
| B1 | Characterization tests pin current output | — | low | Lock current aggregates exactly |
| B2 | Add index `idx_clicks_code` (already present) + `idx_clicks_code_day` | B1 | low | Index used by query plan |
| B3 | Push aggregation into SQL (`COUNT`, `GROUP BY date`) | B1 | high | Identical results to B1 |
| B4 | Keep `top_referrers` as a `GROUP BY` query | B3 | medium | Same ranking/order |
| B5 | Re-run suite + compare | B3,B4 | medium | No behavioural change |

**Key discipline:** B1 comes first. We do not refactor code we have not pinned
with tests.

## 3. AI-assisted execution

**Task B3 prompt:**

```
Refactor Analytics.summary so aggregation happens in SQL instead of Python.
Add Repository methods:
  - count_clicks(code) -> int                      (COUNT(*))
  - clicks_by_day(code) -> dict[str,int]           (GROUP BY substr(clicked_at,1,10))
  - top_referrers(code, n) -> list[tuple[str,int]] (GROUP BY referrer ORDER BY n DESC)
Constraints: parameterized SQL only; results MUST equal the current Python
aggregation (the characterization tests in B1 must still pass unchanged).
```

**Engineer review of the AI draft:**
- Verify SQL is parameterized (no string interpolation of `code`).
- Confirm date bucketing matches the previous `clicked_at[:10]` semantics exactly,
  including timezone handling.
- Check the query plan actually uses the index (`EXPLAIN QUERY PLAN`).

## 4. Validation

```powershell
pytest examples/url_shortener/tests/test_analytics.py -q
```

The existing analytics tests act as the regression guard — `summary()` output must
be byte-for-byte identical. Because the public contract (`AnalyticsResponse`) is
unchanged, `test_api.py::test_analytics_endpoint_tracks_clicks` must also stay
green with no edits.

Before/after intent:

| | Before | After |
| --- | --- | --- |
| Rows transferred per request | all clicks | a handful of aggregate rows |
| Aggregation location | Python | SQLite (indexed) |
| API response | unchanged | unchanged |

## 5. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Subtle aggregation mismatch (e.g. date/tz) | Characterization tests pin exact output before refactor |
| Index not actually used | Inspect `EXPLAIN QUERY PLAN`; assert in a test |
| AI "improves" the API shape unprompted | Contract tests fail on any response change |
