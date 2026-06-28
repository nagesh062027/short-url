"""Tests for the Task Decomposer and the TaskGraph ordering."""

from __future__ import annotations

import pytest
from ai_eng.analyzer import RequirementAnalyzer
from ai_eng.decomposer import TaskDecomposer
from ai_eng.models import Task, TaskGraph


def _graph_for(requirement: str) -> TaskGraph:
    analysis = RequirementAnalyzer().analyze(requirement)
    return TaskDecomposer().decompose(analysis)


def test_url_shortener_uses_specific_template() -> None:
    graph = _graph_for("Build a scalable URL shortener with analytics")
    ids = {task.id for task in graph.tasks}
    assert {"T1", "T5", "T8"}.issubset(ids)  # has analytics + docs tasks


def test_generic_template_for_unknown_requirement() -> None:
    graph = _graph_for("Build a weather widget")
    assert len(graph.tasks) == 4


def test_topological_order_respects_dependencies() -> None:
    graph = _graph_for("Build a URL shortener")
    order = [task.id for task in graph.topological_order()]
    for task in graph.tasks:
        for dep in task.depends_on:
            assert order.index(dep) < order.index(task.id)


def test_cyclic_graph_is_rejected() -> None:
    a = Task(id="A", name="A", description="", depends_on=["B"])
    b = Task(id="B", name="B", description="", depends_on=["A"])
    with pytest.raises(ValueError):
        TaskGraph(tasks=[a, b]).topological_order()
