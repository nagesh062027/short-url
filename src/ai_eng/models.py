"""Domain models for the AI-assisted engineering pipeline.

These dataclasses are the contract that flows between every stage of the
pipeline: Analyzer -> Decomposer -> Executor -> Validator -> OutputGenerator.

Keeping them as plain dataclasses (instead of pipeline-stage-specific dicts)
gives us a single, typed, serialisable representation that is easy to test and
easy to render into the final engineering summary.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssistLevel(str, Enum):
    """How much an engineer should lean on AI for a given task.

    The level is advisory: it documents *intent*, so a reviewer can see where
    AI did heavy lifting (and therefore needs the most scrutiny).
    """

    NONE = "none"      # Pure engineering judgement; AI not used.
    LOW = "low"        # Boilerplate / scaffolding assistance.
    MEDIUM = "medium"  # AI drafts, engineer heavily edits.
    HIGH = "high"      # AI generates most of the implementation.


class RequirementType(str, Enum):
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"
    AMBIGUOUS = "ambiguous"


@dataclass
class Ambiguity:
    """A single unclear aspect of a requirement plus how we resolved it."""

    question: str
    why_it_matters: str
    assumption: str = ""  # The decision the engineer made to proceed.


@dataclass
class RequirementAnalysis:
    """Structured interpretation of a natural-language requirement."""

    raw_requirement: str
    intent: str
    requirement_type: RequirementType
    functional_needs: list[str] = field(default_factory=list)
    non_functional_needs: list[str] = field(default_factory=list)
    technical_needs: list[str] = field(default_factory=list)
    ambiguities: list[Ambiguity] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class Task:
    """One unit of work in the decomposition graph."""

    id: str
    name: str
    description: str
    assist_level: AssistLevel = AssistLevel.MEDIUM
    depends_on: list[str] = field(default_factory=list)
    # Filled in by the executor.
    ai_prompt: str = ""
    artifacts: list[str] = field(default_factory=list)
    validation_focus: list[str] = field(default_factory=list)


@dataclass
class TaskGraph:
    """A dependency-ordered collection of tasks."""

    tasks: list[Task] = field(default_factory=list)

    def by_id(self, task_id: str) -> Task:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"Unknown task id: {task_id}")

    def topological_order(self) -> list[Task]:
        """Return tasks so that every dependency precedes its dependents.

        Raises ``ValueError`` if the dependency graph contains a cycle, which
        protects us from silently producing an unexecutable plan.
        """

        resolved: list[Task] = []
        resolved_ids: set[str] = set()
        remaining = list(self.tasks)

        while remaining:
            progressed = False
            for task in list(remaining):
                if all(dep in resolved_ids for dep in task.depends_on):
                    resolved.append(task)
                    resolved_ids.add(task.id)
                    remaining.remove(task)
                    progressed = True
            if not progressed:
                stuck = ", ".join(t.id for t in remaining)
                raise ValueError(
                    f"Cyclic or unsatisfiable dependencies among tasks: {stuck}"
                )
        return resolved


@dataclass
class ExecutionResult:
    """The outcome of running the executor over a task graph."""

    tasks: list[Task] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class ValidationResult:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


@dataclass
class EngineeringSummary:
    """The final, structured deliverable of the pipeline."""

    analysis: RequirementAnalysis
    task_graph: TaskGraph
    execution: ExecutionResult
    validation: ValidationResult
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def to_serialisable(obj: Any) -> Any:
    """Recursively convert dataclasses/enums into JSON-friendly structures."""

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_serialisable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: to_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serialisable(v) for v in obj]
    return obj
