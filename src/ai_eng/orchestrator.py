"""Orchestrator - wires the five pipeline stages together.

This is the single entry point a caller uses to turn a requirement string into a
validated :class:`EngineeringSummary`. Each stage is injected so it can be unit
tested or swapped (e.g. a different AI provider) without touching the pipeline.
"""

from __future__ import annotations

from pathlib import Path

from .ai_provider import AIProvider, default_provider
from .analyzer import RequirementAnalyzer
from .decomposer import TaskDecomposer
from .executor import AIAssistedExecutor
from .models import EngineeringSummary, RequirementType
from .validator import Validator


class Pipeline:
    def __init__(
        self,
        repo_root: Path | str,
        provider: AIProvider | None = None,
    ) -> None:
        self._repo_root = Path(repo_root)
        provider = provider or default_provider()
        self._analyzer = RequirementAnalyzer(provider)
        self._decomposer = TaskDecomposer()
        self._executor = AIAssistedExecutor(provider)
        self._validator = Validator(self._repo_root)

    def run(self, requirement: str, *, run_tests: bool = False) -> EngineeringSummary:
        analysis = self._analyzer.analyze(requirement)
        graph = self._decomposer.decompose(analysis)
        execution = self._executor.execute(graph, analysis)
        validation = self._validator.validate(graph, run_tests=run_tests)

        return EngineeringSummary(
            analysis=analysis,
            task_graph=graph,
            execution=execution,
            validation=validation,
            assumptions=[amb.assumption for amb in analysis.ambiguities if amb.assumption],
            limitations=self._limitations(analysis.requirement_type),
        )

    def _limitations(self, req_type: RequirementType) -> list[str]:
        limits = [
            "Default AI provider is deterministic/offline; live LLM assistance is "
            "opt-in via OPENAI_API_KEY and is not required to reproduce results.",
            "The decomposer uses engineer-authored templates; novel requirements "
            "fall back to a generic 4-step plan.",
        ]
        if req_type is RequirementType.AMBIGUOUS:
            limits.append(
                "Ambiguous requirements proceed on documented assumptions that must "
                "be confirmed by a stakeholder before shipping."
            )
        return limits
