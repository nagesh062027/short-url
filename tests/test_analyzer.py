"""Tests for the Requirement Analyzer."""

from __future__ import annotations

import pytest
from ai_eng.analyzer import RequirementAnalyzer
from ai_eng.models import RequirementType


@pytest.fixture
def analyzer() -> RequirementAnalyzer:
    return RequirementAnalyzer()


def test_empty_requirement_raises(analyzer: RequirementAnalyzer) -> None:
    with pytest.raises(ValueError):
        analyzer.analyze("   ")


def test_url_shortener_is_greenfield(analyzer: RequirementAnalyzer) -> None:
    result = analyzer.analyze(
        "Build a scalable URL shortener service with APIs, persistence, and analytics"
    )
    assert result.requirement_type is RequirementType.GREENFIELD
    assert any("scal" in n.lower() for n in result.non_functional_needs)


def test_optimize_is_brownfield(analyzer: RequirementAnalyzer) -> None:
    result = analyzer.analyze("Optimize database queries for analytics")
    assert result.requirement_type is RequirementType.BROWNFIELD


def test_vague_requirement_is_ambiguous(analyzer: RequirementAnalyzer) -> None:
    result = analyzer.analyze("Make the service more scalable")
    assert result.requirement_type is RequirementType.AMBIGUOUS
    assert result.ambiguities, "Expected clarifying questions for a vague requirement"


def test_ambiguities_carry_assumptions(analyzer: RequirementAnalyzer) -> None:
    result = analyzer.analyze("Make it faster and more secure")
    assert all(a.assumption for a in result.ambiguities)


def test_risks_always_flag_ai_validation(analyzer: RequirementAnalyzer) -> None:
    result = analyzer.analyze("Build a URL shortener")
    assert any("validation gate" in r for r in result.risks)
