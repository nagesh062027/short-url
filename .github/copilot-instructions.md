# Copilot Instructions — AI-Assisted Software Engineering Prototype

Always-on context for working in this repository. Keep responses aligned with the
project's core principle: **AI assists the engineer within tasks; the engineer
owns execution and quality.**

## What this repo is

Two cohesive parts:

1. **The prototype pipeline** — `src/ai_eng/`: an engineer-led, 5-stage pipeline
   (`analyzer → decomposer → executor → validator → output`, wired by
   `orchestrator.py`) that turns a natural-language requirement into a validated
   engineering summary. CLI entry: `python -m ai_eng "<requirement>"`.
2. **The URL shortener demo** — `examples/url_shortener/`: a layered FastAPI +
   SQLite + LRU-cache + analytics service that the pipeline plans and validates.

## Project structure

| Path | Purpose |
| --- | --- |
| `src/ai_eng/` | Pipeline stages + `models.py` (typed dataclasses), `ai_provider.py`, `knowledge.py` (task templates) |
| `examples/url_shortener/app/` | Layered demo: `shortener`, `storage`, `cache`, `analytics`, `service`, `main`, `schemas` |
| `examples/url_shortener/tests/` | Demo tests (pytest) |
| `tests/` | Pipeline tests |
| `docs/` | `approach.md`, `evaluation.md`, `examples/{greenfield,brownfield,ambiguous}.md` |
| `scripts/` | `run_demo.ps1` / `run_demo.sh` |

## Build & test commands

```powershell
pip install -r requirements.txt           # runtime + test toolchain
python -m pytest -q                        # all tests (currently 56)
python -m pytest --cov=ai_eng --cov=app    # with coverage
python -m ai_eng "<requirement>"           # run the pipeline (gate exits non-zero on failure)
```

`pyproject.toml` sets `pythonpath = ["src", "examples/url_shortener"]`, so tests
import `ai_eng.*` and `app.*` without an editable install.

## Conventions (follow these)

- **Typed dataclasses** are the contract between pipeline stages (`models.py`).
  Don't pass ad-hoc dicts between stages.
- **Layering in the demo is strict:** HTTP (`main.py`) is thin → `service.py` owns
  rules → `storage.py` is the only module with SQL. Keep business logic out of the
  HTTP layer. Pure logic (`shortener.py`) stays I/O-free.
- **Planning is deterministic.** Decomposition comes from engineer-authored
  templates in `knowledge.py`, never from live LLM output.
- **AI is offline-first.** The default provider is deterministic; live LLM is
  opt-in via `OPENAI_API_KEY`. Never make tests or the pipeline require network.
- **Parameterized SQL only.** No string-built queries with user input.
- **Validate, don't trust.** Any new code must ship with tests; the `Validator`
  gate checks artifacts/syntax/tests/security and (opt-in) runs the suite.
- **No new runtime dependencies** without a clear reason — the demo intentionally
  uses stdlib `sqlite3` and an in-process cache.

## When extending

- Adding a requirement type → add a template to `knowledge.py` and a selector in
  `decomposer.py`; cover it in `tests/test_decomposer.py`. See the
  `/add-requirement-template` skill.
- Touching the demo → update/extend tests in `examples/url_shortener/tests/` and
  keep the public API (`schemas.py`) stable unless asked.
- Always run `python -m pytest -q` before declaring work done.
