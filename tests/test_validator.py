"""Tests for the Validator quality gate."""

from __future__ import annotations

from pathlib import Path

from ai_eng.models import AssistLevel, Task, TaskGraph
from ai_eng.validator import Validator


def test_missing_artifact_fails_gate(tmp_path: Path) -> None:
    graph = TaskGraph(tasks=[Task(id="T1", name="x", description="", artifacts=["nope.py"])])
    result = Validator(tmp_path).validate(graph)
    assert not result.passed
    assert any(c.name == "artifacts_exist" and not c.passed for c in result.checks)


def test_syntax_error_is_detected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("def broken(:\n", encoding="utf-8")
    graph = TaskGraph(tasks=[Task(id="T1", name="x", description="", artifacts=["bad.py"])])
    result = Validator(tmp_path).validate(graph)
    assert any(c.name == "syntax" and not c.passed for c in result.checks)


def test_security_scan_flags_eval(tmp_path: Path) -> None:
    risky = tmp_path / "risky.py"
    risky.write_text("x = eval('2+2')\n", encoding="utf-8")
    graph = TaskGraph(tasks=[Task(id="T1", name="x", description="", artifacts=["risky.py"])])
    result = Validator(tmp_path).validate(graph)
    assert any(c.name == "security_scan" and not c.passed for c in result.checks)


def test_missing_tests_fail_gate(tmp_path: Path) -> None:
    src = tmp_path / "ok.py"
    src.write_text("x = 1\n", encoding="utf-8")
    graph = TaskGraph(tasks=[Task(id="T1", name="x", description="", artifacts=["ok.py"])])
    result = Validator(tmp_path).validate(graph)
    assert any(c.name == "tests_present" and not c.passed for c in result.checks)


def test_clean_plan_passes(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "test_ok.py").write_text("def test_add():\n    assert True\n", encoding="utf-8")
    graph = TaskGraph(
        tasks=[
            Task(id="T1", name="impl", description="", assist_level=AssistLevel.HIGH,
                 artifacts=["ok.py"]),
            Task(id="T2", name="tests", description="", artifacts=["test_ok.py"],
                 depends_on=["T1"]),
        ]
    )
    result = Validator(tmp_path).validate(graph)
    assert result.passed
