# Architecture Overview

## 1. Goals & guiding principle

The system demonstrates **AI-assisted, engineer-owned** software development. The
single principle that drives every design decision:

> *AI assists the engineer within tasks; the engineer owns execution and quality.*

Concretely that means:

- **Determinism by default.** The pipeline must produce the same result on any
  machine, in CI, offline. So planning is template-driven and the default AI
  provider is deterministic. Live LLMs are opt-in.
- **Auditability.** Every place AI contributes is recorded (the prompt and the
  artifacts it touched) so a reviewer can see *where* to apply scrutiny.
- **Nothing accepted on trust.** AI output passes a concrete validation gate
  before it is considered done.

## 2. System components

```
┌──────────────────────────────────────────────────────────────┐
│                        Pipeline (orchestrator)                │
│                                                                │
│  Requirement ─▶ Analyzer ─▶ Decomposer ─▶ Executor ─▶ Validator│
│                     │            │            │           │    │
│                     ▼            ▼            ▼           ▼    │
│              RequirementAnalysis TaskGraph ExecutionResult ValidationResult
│                                                                │
│                          └────────────▶ OutputGenerator ──────┴─▶ Markdown + JSON
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼  (pluggable)
                         AIProvider
                    ┌───────────┴───────────┐
              OfflineProvider          OpenAIProvider
            (deterministic, default)   (opt-in, API key)
```

| Component | File | Responsibility | AI integration |
| --- | --- | --- | --- |
| **Analyzer** | `analyzer.py` | Classify requirement; extract intent, NFRs, ambiguities, risks | Heuristics decide; AI *enriches* clarifying questions |
| **Decomposer** | `decomposer.py` + `knowledge.py` | Select an engineer-authored task template; produce a dependency-ordered graph | None — plans are deterministic and reviewable |
| **Executor** | `executor.py` | Build a precise prompt per task; record AI suggestion + artifacts | AI assists *inside* each task; engineer owns acceptance |
| **Validator** | `validator.py` | Quality gate: artifacts exist, syntax, tests present, security scan, optional test run | Validates AI output; never trusts it |
| **Output** | `output.py` | Render the engineering summary (Markdown + JSON) | None |
| **Provider** | `ai_provider.py` | Abstraction over AI access | The single integration seam |

The data contract between stages is a set of typed dataclasses in `models.py`
(`RequirementAnalysis`, `TaskGraph`, `ExecutionResult`, `ValidationResult`,
`EngineeringSummary`), which keeps each stage independently testable.

## 3. Where AI integrates (and where it deliberately does not)

| Task type | AI assist level | Why |
| --- | --- | --- |
| Clarifying questions | enrichment | AI is good at surfacing implicit assumptions; engineer keeps the deterministic baseline. |
| Planning / decomposition | **none** | Plans must be reproducible, dependency-correct, and reviewable. LLM planning is non-deterministic and hard to validate. |
| Implementation of a task | high | Boilerplate and well-scoped logic are where AI accelerates the most — and where the validation gate focuses. |
| Validation | **none** | The gate is the engineer's objective check on AI output. |

This split is the core engineering judgement: **AI accelerates execution within a
task; it does not own the plan or the acceptance decision.**

## 4. The URL shortener (demo) architecture

```
HTTP (FastAPI)  ──▶  ShortenerService  ──▶  Repository (SQLite)
   main.py            service.py              storage.py
      │                  │   │  │
      │                  │   │  └─▶ Analytics (read-side aggregation)  analytics.py
      │                  │   └────▶ LRUCache (hot-path reads)          cache.py
      │                  └────────▶ shortener.encode/decode (Base62)   shortener.py
      └─ schemas.py (request/response contract → OpenAPI)
```

Layering rules:

- **HTTP layer is thin** — validates input, calls the service, maps domain
  exceptions to status codes. No business logic.
- **Service owns rules** — URL/alias validation, cache warming, click recording.
- **Repository owns SQL** — the only module that knows about the database.
- **Pure logic is isolated** — Base62 encoding has no I/O, so it is exhaustively
  unit-testable.

## 5. Key design decisions & trade-offs

| Decision | Rationale | Trade-off / mitigation |
| --- | --- | --- |
| **Template-driven planning** (not LLM planning) | Deterministic, reviewable, dependency-correct plans | Novel requirements fall back to a generic 4-step plan; extend `knowledge.py` to add templates |
| **Offline AI provider by default** | Reproducibility; runs in CI / air-gapped | Offline mode doesn't generate novel code; it records the assistance seam. Live provider is one env var away |
| **Key-based Base62 short codes** | Unique by construction, no collision loop, short codes | Sequential codes are guessable; add a salt/`hashids` if enumeration is a concern |
| **SQLite default persistence** | Zero-config, durable, good enough to prove the design | Single-writer; repository pattern localizes a Postgres swap |
| **In-process LRU cache** | Removes a DB round-trip on the hot path with no infra | Not shared across instances; swap for Redis behind the same interface |
| **Click capture on write path, aggregation on read** | Keeps redirects fast; analytics can scale separately | Synchronous insert adds a small write; can move to a queue if needed |

## 6. Failure handling & safety

- The `TaskGraph` rejects cyclic/unsatisfiable dependencies early (`ValueError`)
  rather than producing an unexecutable plan.
- The validator's security scan flags `eval`/`exec`, `shell=True`, and hardcoded
  secrets in any artifact before acceptance.
- The CLI exits non-zero when the quality gate fails, so CI can gate on it.
- The URL shortener validates that inputs are absolute `http(s)` URLs and that
  custom aliases match a strict charset, preventing open-redirect-style abuse via
  malformed schemes.

## 7. Extensibility

- **New requirement domains:** add a template function in `knowledge.py` and a
  selector in `decomposer.py`.
- **New validation checks:** add a `CheckResult`-returning method to `Validator`.
- **A different AI vendor:** implement the `AIProvider` protocol and return it
  from `default_provider()`.
