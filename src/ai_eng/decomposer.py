"""Stage 2 - Task Decomposer (engineer-led).

Selects an engineer-authored decomposition template for the requirement and
returns a dependency-ordered :class:`TaskGraph`. The decomposer deliberately
does *not* delegate planning to an LLM: plans must be deterministic, reviewable
and dependency-correct. AI assistance is applied later, inside each task.
"""

from __future__ import annotations

from . import knowledge
from .models import RequirementAnalysis, TaskGraph


class TaskDecomposer:
    def decompose(self, analysis: RequirementAnalysis) -> TaskGraph:
        if knowledge.is_url_shortener(analysis.raw_requirement):
            tasks = knowledge.url_shortener_tasks()
        else:
            tasks = knowledge.generic_tasks(analysis.intent)

        graph = TaskGraph(tasks=tasks)
        # Validate the plan is executable before handing it on. This converts a
        # latent planning bug into an explicit, early failure.
        graph.topological_order()
        return graph
