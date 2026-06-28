"""Stage 3 - AI-Assisted Executor.

For each task (in dependency order) the executor:

1. Builds a precise, task-scoped AI prompt - this is the "clear prompting and
   task definition" the engineer is responsible for.
2. Invokes the AI provider to obtain a suggestion (offline by default).
3. Records the prompt and the artifacts the task is responsible for, so the
   assistance is fully auditable downstream.

The executor does not blindly trust AI output - it records *where* AI helped and
hands every artifact to the validator. The engineer owns acceptance.
"""

from __future__ import annotations

from .ai_provider import AIProvider, default_provider
from .models import ExecutionResult, RequirementAnalysis, Task, TaskGraph

_SYSTEM_PROMPT = (
    "You are a senior engineer's pair-programmer. Produce minimal, correct, "
    "well-tested code. State assumptions explicitly. Do not invent requirements."
)


class AIAssistedExecutor:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider or default_provider()

    def execute(
        self, graph: TaskGraph, analysis: RequirementAnalysis
    ) -> ExecutionResult:
        notes = [f"AI provider in use: {self._provider.name}"]
        for task in graph.topological_order():
            task.ai_prompt = self._build_prompt(task, analysis)
            # The suggestion is captured for the audit trail. In offline mode it
            # is deterministic; in live mode it would seed the engineer's edits.
            suggestion = self._provider.complete(task.ai_prompt, system=_SYSTEM_PROMPT)
            notes.append(
                f"{task.id} ({task.assist_level.value}): "
                f"{len(suggestion)} chars of AI assistance -> "
                f"{len(task.artifacts)} artifact(s)"
            )
        return ExecutionResult(tasks=graph.tasks, notes=notes)

    def _build_prompt(self, task: Task, analysis: RequirementAnalysis) -> str:
        deps = ", ".join(task.depends_on) if task.depends_on else "none"
        focus = "; ".join(task.validation_focus) if task.validation_focus else "n/a"
        return (
            f"Requirement: {analysis.intent}\n"
            f"Task {task.id}: {task.name}\n"
            f"Goal: {task.description}\n"
            f"Depends on: {deps}\n"
            f"Must satisfy (will be validated): {focus}\n"
            f"Constraints: production-quality, typed, unit-tested, no dead code.\n"
            f"Deliverables: {', '.join(task.artifacts) or 'code + tests'}"
        )
