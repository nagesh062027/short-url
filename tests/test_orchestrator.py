"""End-to-end tests for the pipeline orchestrator and output generator."""

from __future__ import annotations

from pathlib import Path

from ai_eng.orchestrator import Pipeline
from ai_eng.output import OutputGenerator

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_produces_summary_for_url_shortener() -> None:
    pipeline = Pipeline(REPO_ROOT)
    summary = pipeline.run(
        "Build a scalable URL shortener service with APIs, persistence, and analytics"
    )
    assert summary.task_graph.tasks
    # The plan's artifacts really exist in the repo, so the gate passes
    # (without executing the test suite).
    assert summary.validation.passed, [
        (c.name, c.detail) for c in summary.validation.checks if not c.passed
    ]


def test_pipeline_records_ai_assistance() -> None:
    summary = Pipeline(REPO_ROOT).run("Build a URL shortener with analytics")
    assert any("AI provider in use" in note for note in summary.execution.notes)


def test_markdown_report_has_expected_sections() -> None:
    summary = Pipeline(REPO_ROOT).run("Build a URL shortener with analytics")
    markdown = OutputGenerator().to_markdown(summary)
    assert "# Engineering Summary" in markdown
    assert "Implementation Approach" in markdown
    assert "Validation Results" in markdown


def test_json_report_is_serialisable() -> None:
    import json

    summary = Pipeline(REPO_ROOT).run("Build a URL shortener")
    payload = json.loads(OutputGenerator().to_json(summary))
    assert payload["analysis"]["requirement_type"] == "greenfield"


def test_ambiguous_requirement_surfaces_assumptions() -> None:
    summary = Pipeline(REPO_ROOT).run("Make the service more scalable")
    assert summary.assumptions
    assert any("confirm" in limit.lower() for limit in summary.limitations)
