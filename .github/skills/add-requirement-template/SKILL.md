---
name: add-requirement-template
description: 'Add or modify a requirement decomposition template in the AI-assisted engineering pipeline. Use when introducing a new requirement type, changing how an existing requirement is broken into tasks, wiring a selector into the decomposer, or generating the artifacts/tests a plan names. Triggers: add requirement template, new requirement type, change task breakdown, extend the decomposer, modify the spec, plan a new feature.'
argument-hint: 'the requirement text or template name to add/modify'
---

# Add or Modify a Requirement Template

Planning in this project is **deterministic and engineer-led**: task breakdowns
live as reviewable templates in `src/ai_eng/knowledge.py`, not LLM output. This
skill walks through adding or changing one safely.

## When to use
- A new class of requirement needs its own task breakdown (e.g. "auth", "scaling").
- An existing breakdown should change (add/remove/reorder tasks or dependencies).
- You want the pipeline to recognize a new keyword and emit a specific plan.

## Key files
- `src/ai_eng/knowledge.py` — the templates (`url_shortener_tasks`, `generic_tasks`).
- `src/ai_eng/decomposer.py` — selects a template based on the requirement.
- `src/ai_eng/models.py` — `Task`, `TaskGraph`, `AssistLevel` (the contract).
- `tests/test_decomposer.py` — where new templates are covered.

## Procedure

1. **See the current plan first:**
   ```powershell
   python -m ai_eng "<your requirement>"
   ```
   If it returns the generic 4-step plan, a dedicated template adds value.

2. **Add a template function** in `knowledge.py`. Return a list of `Task` with:
   - unique `id`s (e.g. `T1`, `T2`…),
   - a clear `name` + `description`,
   - an honest `assist_level` (`none`/`low`/`medium`/`high` — signals review focus),
   - correct `depends_on` (must form a DAG; the graph rejects cycles),
   - real `artifacts` paths the plan will produce/validate,
   - a `validation_focus` list (what the validator/tests should check).

   Also add a keyword matcher, mirroring `is_url_shortener`:
   ```python
   _AUTH_KEYWORDS = ("authentication", "auth", "login", "sign in")

   def is_auth(requirement: str) -> bool:
       lowered = requirement.lower()
       return any(k in lowered for k in _AUTH_KEYWORDS)

   def auth_tasks() -> list[Task]:
       return [ Task(id="T1", name="...", description="...",
                     assist_level=AssistLevel.LOW, artifacts=[...],
                     validation_focus=[...]), ... ]
   ```

3. **Wire the selector** in `decomposer.py` (order matters — most specific first):
   ```python
   if knowledge.is_url_shortener(analysis.raw_requirement):
       tasks = knowledge.url_shortener_tasks()
   elif knowledge.is_auth(analysis.raw_requirement):
       tasks = knowledge.auth_tasks()
   else:
       tasks = knowledge.generic_tasks(analysis.intent)
   ```

4. **Cover it with a test** in `tests/test_decomposer.py`: assert the right
   template is chosen and that `topological_order()` respects dependencies.
   ```python
   def test_auth_uses_specific_template():
       graph = _graph_for("Add user authentication to the URL shortener")
       assert {"T1", "T2"}.issubset({t.id for t in graph.tasks})
   ```

5. **Produce the artifacts the plan names** (if this requirement is being built,
   not just planned). Follow repo conventions and add their tests. The validator's
   `artifacts_exist` check fails if a named artifact is missing — so either create
   the files or keep `artifacts` limited to what exists.

6. **Validate:**
   ```powershell
   python -m pytest -q
   python -m ai_eng "<your requirement>" --run-tests   # expect: Quality gate: PASSED
   ```

## Gotchas
- **Artifacts must exist.** The gate checks every `artifacts` path. Listing a file
  you haven't created will fail `artifacts_exist`.
- **Keep it a DAG.** A dependency cycle raises `ValueError` at decomposition time.
- **`assist_level` is documentation, not enforcement** — set it honestly so
  reviewers know where AI did the heavy lifting.
- **Don't add an LLM call to planning.** Keep templates deterministic.

## Reference
Worked scenarios that show this end-to-end:
`docs/examples/greenfield.md`, `docs/examples/brownfield.md`, `docs/examples/ambiguous.md`.
