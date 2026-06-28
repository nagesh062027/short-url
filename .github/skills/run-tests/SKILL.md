---
name: run-tests
description: 'Run and validate the AI-assisted engineering project: full pytest suite, coverage report, and the end-to-end pipeline quality gate. Use when asked to test the project, check coverage, validate the build, confirm the gate passes, or verify changes did not break anything.'
argument-hint: 'optional: a path or test node to focus on'
---

# Run & Validate the Project

## When to use
- Verify the whole repo is green (prototype + URL shortener demo).
- Get a coverage report.
- Confirm the pipeline quality gate passes end-to-end.
- Re-run a single failing test while debugging.

## Procedure

1. **Install deps** (skip if already installed):
   ```powershell
   pip install -r requirements.txt
   ```

2. **Run the full suite** (currently 56 tests):
   ```powershell
   python -m pytest -q
   ```
   To focus on one area, pass a path, e.g. `python -m pytest examples/url_shortener/tests -q`.

3. **Coverage** (overall is ~89%):
   ```powershell
   python -m pytest --cov=ai_eng --cov=app --cov-report=term-missing
   ```

4. **End-to-end quality gate** — runs the pipeline and executes the suite as part
   of validation. Must print `Quality gate: PASSED` and exit 0:
   ```powershell
   python -m ai_eng "Build a scalable URL shortener service with APIs, persistence, and analytics" --run-tests
   ```

5. **Catch resource leaks** (optional): add `-W error::ResourceWarning` to step 2.

Or run everything at once with the bundled helper:
```powershell
./.github/skills/run-tests/scripts/run-tests.ps1
```

## Interpreting results
- `N passed` with exit 0 → green.
- A failing test: re-run it with `-v`, read the named test + source, and report the
  root cause and the file/line to fix. Do not silently weaken assertions.
- `__main__.py` showing 0% coverage is expected — the CLI is exercised via
  subprocess, not in-process unit tests.
- The only expected warning is Starlette's `TestClient` httpx deprecation (upstream).

## Notes
- Never set `OPENAI_API_KEY` for tests — the pipeline must pass offline/deterministically.
- `pyproject.toml` already puts `src` and `examples/url_shortener` on `pythonpath`.
