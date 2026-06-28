"""Knowledge base of engineer-authored task templates.

The decomposer is *engineer-led*: rather than asking an LLM to invent a plan
(which is non-deterministic and hard to validate), we encode the engineer's
decomposition as reviewable templates here. AI assistance happens *inside* each
task during execution. For the mandatory URL-shortener requirement we map
directly onto the real artifacts that live in ``examples/url_shortener`` so the
plan and the shipped code stay in lock-step.
"""

from __future__ import annotations

from .models import AssistLevel, Task

_URL_SHORTENER_KEYWORDS = ("url shortener", "short url", "shorten", "bit.ly", "tinyurl")


def is_url_shortener(requirement: str) -> bool:
    lowered = requirement.lower()
    return any(keyword in lowered for keyword in _URL_SHORTENER_KEYWORDS)


def url_shortener_tasks() -> list[Task]:
    """The engineer's decomposition for the mandatory use case."""

    base = "examples/url_shortener/app"
    tests = "examples/url_shortener/tests"
    return [
        Task(
            id="T1",
            name="Project scaffold & API contract",
            description=(
                "Define the FastAPI app, request/response schemas and the public "
                "REST contract (create, redirect, analytics, health)."
            ),
            assist_level=AssistLevel.LOW,
            artifacts=[f"{base}/main.py", f"{base}/schemas.py"],
            validation_focus=["Schema validation", "OpenAPI contract present"],
        ),
        Task(
            id="T2",
            name="Persistence layer",
            description=(
                "Durable storage for URL mappings and click events using a "
                "repository pattern over SQLite (swappable for Postgres)."
            ),
            assist_level=AssistLevel.HIGH,
            depends_on=["T1"],
            artifacts=[f"{base}/storage.py"],
            validation_focus=["CRUD correctness", "Schema migrations idempotent"],
        ),
        Task(
            id="T3",
            name="Short-code generation",
            description=(
                "Collision-resistant Base62 short-code generation from a numeric id "
                "plus reverse decoding, kept pure and unit-testable."
            ),
            assist_level=AssistLevel.MEDIUM,
            depends_on=["T1"],
            artifacts=[f"{base}/shortener.py"],
            validation_focus=["Round-trip encode/decode", "No collisions in range"],
        ),
        Task(
            id="T4",
            name="Core API endpoints",
            description=(
                "Implement create-short-URL, redirect (302) and listing endpoints, "
                "wiring storage + code generation together with validation."
            ),
            assist_level=AssistLevel.HIGH,
            depends_on=["T2", "T3"],
            artifacts=[f"{base}/main.py", f"{base}/service.py"],
            validation_focus=["Happy path", "404 for unknown codes", "URL validation"],
        ),
        Task(
            id="T5",
            name="Analytics capture & query",
            description=(
                "Record click events (timestamp, referrer, UA) off the hot path and "
                "expose an aggregated analytics endpoint."
            ),
            assist_level=AssistLevel.HIGH,
            depends_on=["T2", "T4"],
            artifacts=[f"{base}/analytics.py"],
            validation_focus=["Click counts accurate", "Redirect latency unaffected"],
        ),
        Task(
            id="T6",
            name="Caching hot path",
            description=(
                "Add an in-process LRU cache for code->URL lookups (Redis-swappable) "
                "to keep redirects fast under read-heavy load."
            ),
            assist_level=AssistLevel.MEDIUM,
            depends_on=["T4"],
            artifacts=[f"{base}/cache.py"],
            validation_focus=["Cache hit/miss correctness", "Invalidation on write"],
        ),
        Task(
            id="T7",
            name="Unit & integration tests",
            description=(
                "pytest suite covering encoding, storage, analytics and the HTTP API "
                "end-to-end via the FastAPI test client."
            ),
            assist_level=AssistLevel.MEDIUM,
            depends_on=["T4", "T5", "T6"],
            artifacts=[
                f"{tests}/test_shortener.py",
                f"{tests}/test_storage.py",
                f"{tests}/test_api.py",
                f"{tests}/test_analytics.py",
            ],
            validation_focus=["Coverage of hot paths", "Edge cases asserted"],
        ),
        Task(
            id="T8",
            name="Documentation",
            description=(
                "README with run/usage instructions plus the auto-generated OpenAPI "
                "schema served at /docs."
            ),
            assist_level=AssistLevel.LOW,
            depends_on=["T7"],
            artifacts=["examples/url_shortener/README.md"],
            validation_focus=["Run steps accurate", "Endpoints documented"],
        ),
    ]


def generic_tasks(intent: str) -> list[Task]:
    """Fallback decomposition for requirements without a specific template."""

    return [
        Task(
            id="T1",
            name="Clarify scope & define contract",
            description=(
                f"Translate '{intent}' into an explicit interface/contract and "
                "acceptance criteria before writing code."
            ),
            assist_level=AssistLevel.LOW,
            validation_focus=["Acceptance criteria are measurable"],
        ),
        Task(
            id="T2",
            name="Implement core logic",
            description="Build the primary capability behind a small, testable seam.",
            assist_level=AssistLevel.HIGH,
            depends_on=["T1"],
            validation_focus=["Correctness", "Input validation"],
        ),
        Task(
            id="T3",
            name="Write tests",
            description="Unit + integration tests, including edge and failure cases.",
            assist_level=AssistLevel.MEDIUM,
            depends_on=["T2"],
            validation_focus=["Coverage", "Negative paths"],
        ),
        Task(
            id="T4",
            name="Document & review",
            description="Usage docs and a self code-review against the contract.",
            assist_level=AssistLevel.LOW,
            depends_on=["T3"],
            validation_focus=["Docs match behaviour"],
        ),
    ]
