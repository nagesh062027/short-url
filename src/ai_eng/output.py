"""Stage 5 - Output Generator.

Renders the :class:`EngineeringSummary` into the two artifacts a reviewer wants:
a human-readable Markdown report and a machine-readable JSON document. The
Markdown mirrors the assignment's "Final Engineering Output" structure:
implementation approach, generated artifacts, risks/validation, assumptions and
limitations.
"""

from __future__ import annotations

import json

from .models import EngineeringSummary, to_serialisable


class OutputGenerator:
    def to_json(self, summary: EngineeringSummary) -> str:
        return json.dumps(to_serialisable(summary), indent=2)

    def to_markdown(self, summary: EngineeringSummary) -> str:
        a = summary.analysis
        lines: list[str] = []
        add = lines.append

        add("# Engineering Summary")
        add("")
        add(f"**Requirement:** {a.raw_requirement}")
        add("")
        add(f"**Interpreted intent:** {a.intent}")
        add("")
        add(f"**Requirement type:** {a.requirement_type.value}")
        add("")

        add("## 1. Implementation Approach")
        add("")
        add("| Task | Name | AI assist | Depends on | Artifacts |")
        add("| --- | --- | --- | --- | --- |")
        for task in summary.task_graph.topological_order():
            deps = ", ".join(task.depends_on) or "-"
            arts = ", ".join(task.artifacts) or "-"
            add(f"| {task.id} | {task.name} | {task.assist_level.value} | {deps} | {arts} |")
        add("")

        if a.ambiguities:
            add("## 2. Ambiguities & Resolutions")
            add("")
            for amb in a.ambiguities:
                add(f"- **Q:** {amb.question}")
                add(f"  - _Why it matters:_ {amb.why_it_matters}")
                add(f"  - _Assumption:_ {amb.assumption}")
            add("")

        add("## 3. AI-Assisted Execution Log")
        add("")
        for note in summary.execution.notes:
            add(f"- {note}")
        add("")

        add("## 4. Validation Results")
        add("")
        add("| Check | Result | Detail |")
        add("| --- | --- | --- |")
        for check in summary.validation.checks:
            status = "PASS" if check.passed else "FAIL"
            add(f"| {check.name} | {status} | {check.detail} |")
        add("")
        gate = "PASSED" if summary.validation.passed else "FAILED"
        add(f"**Quality gate: {gate}**")
        add("")

        if a.risks:
            add("## 5. Risks")
            add("")
            for risk in a.risks:
                add(f"- {risk}")
            add("")

        if summary.assumptions:
            add("## 6. Assumptions")
            add("")
            for item in summary.assumptions:
                add(f"- {item}")
            add("")

        if summary.limitations:
            add("## 7. Limitations")
            add("")
            for item in summary.limitations:
                add(f"- {item}")
            add("")

        return "\n".join(lines)
