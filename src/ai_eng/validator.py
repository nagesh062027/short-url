"""Stage 4 - Validator & Quality Gate.

Nothing AI produces is accepted on trust. The validator runs concrete,
repeatable checks over the artifacts a plan claims to deliver:

* **Artifact presence** - every promised file actually exists.
* **Syntax** - all Python artifacts compile.
* **Tests present** - the plan includes tests for its code.
* **Static security scan** - flags risky patterns (eval/exec, shell=True,
  hardcoded secrets) so they are reviewed before acceptance.
* **Test execution** (opt-in) - runs the demo's pytest suite and reports the
  result, which is the strongest evidence of correctness.

Each check is small and independently testable; the gate passes only if all
checks pass.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

from .models import CheckResult, TaskGraph, ValidationResult

# Patterns that warrant a human look before accepting AI-written code.
_SECURITY_PATTERNS = {
    r"\beval\s*\(": "Use of eval() can execute arbitrary code.",
    r"\bexec\s*\(": "Use of exec() can execute arbitrary code.",
    r"shell\s*=\s*True": "subprocess with shell=True risks command injection.",
    r"(?i)(api_key|secret|password)\s*=\s*[\"'][^\"']+[\"']":
        "Possible hardcoded secret.",
}


class Validator:
    def __init__(self, repo_root: Path | str) -> None:
        self._root = Path(repo_root)

    def validate(self, graph: TaskGraph, *, run_tests: bool = False) -> ValidationResult:
        checks: list[CheckResult] = []
        artifacts = self._collect_artifacts(graph)

        checks.append(self._check_artifacts_exist(artifacts))
        checks.append(self._check_syntax(artifacts))
        checks.append(self._check_tests_present(graph))
        checks.append(self._check_security(artifacts))
        if run_tests:
            checks.append(self._run_pytest())

        return ValidationResult(checks=checks)

    # --- individual checks ----------------------------------------------

    def _collect_artifacts(self, graph: TaskGraph) -> list[Path]:
        seen: list[Path] = []
        for task in graph.tasks:
            for rel in task.artifacts:
                path = self._root / rel
                if path not in seen:
                    seen.append(path)
        return seen

    def _check_artifacts_exist(self, artifacts: list[Path]) -> CheckResult:
        missing = [str(p) for p in artifacts if not p.exists()]
        if missing:
            return CheckResult(
                "artifacts_exist", False, f"Missing: {', '.join(missing)}"
            )
        return CheckResult(
            "artifacts_exist", True, f"All {len(artifacts)} artifacts present."
        )

    def _check_syntax(self, artifacts: list[Path]) -> CheckResult:
        errors: list[str] = []
        checked = 0
        for path in artifacts:
            if path.suffix != ".py" or not path.exists():
                continue
            checked += 1
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                errors.append(f"{path.name}: {exc.msg} (line {exc.lineno})")
        if errors:
            return CheckResult("syntax", False, "; ".join(errors))
        return CheckResult("syntax", True, f"{checked} Python files parse cleanly.")

    def _check_tests_present(self, graph: TaskGraph) -> CheckResult:
        test_files = [
            rel
            for task in graph.tasks
            for rel in task.artifacts
            if "test" in Path(rel).name.lower()
        ]
        if not test_files:
            return CheckResult(
                "tests_present", False, "No test artifacts found in the plan."
            )
        return CheckResult(
            "tests_present", True, f"{len(test_files)} test file(s) planned."
        )

    def _check_security(self, artifacts: list[Path]) -> CheckResult:
        findings: list[str] = []
        for path in artifacts:
            if path.suffix != ".py" or not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for pattern, message in _SECURITY_PATTERNS.items():
                if re.search(pattern, text):
                    findings.append(f"{path.name}: {message}")
        if findings:
            return CheckResult("security_scan", False, "; ".join(findings))
        return CheckResult("security_scan", True, "No risky patterns detected.")

    def _run_pytest(self) -> CheckResult:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=self._root,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            return CheckResult("tests_pass", False, "pytest is not installed.")
        except subprocess.TimeoutExpired:
            return CheckResult("tests_pass", False, "Test run timed out.")

        tail = (proc.stdout or proc.stderr).strip().splitlines()
        summary = tail[-1] if tail else "no output"
        return CheckResult("tests_pass", proc.returncode == 0, summary)
