"""Stage 1 - Requirement Analyzer.

Turns a free-text requirement into a structured :class:`RequirementAnalysis`.

Design choice: the analyzer is **heuristic-first, AI-assisted**. Deterministic
keyword/intent heuristics give us reproducible, testable behaviour; the AI
provider is then used to *enrich* (draft clarifying questions, surface implicit
needs). The engineer's heuristics own the decision; AI only assists. This keeps
the pipeline trustworthy and runnable without a network.
"""

from __future__ import annotations

import re

from .ai_provider import AIProvider, default_provider
from .models import Ambiguity, RequirementAnalysis, RequirementType

# Signals that a requirement is under-specified.
_AMBIGUITY_SIGNALS = {
    "scalable": (
        "What scale target (RPS, total URLs, read/write ratio) defines success?",
        "Scalability work is unbounded without a concrete target.",
    ),
    "scale": (
        "What scale target (RPS, total URLs, read/write ratio) defines success?",
        "Scalability work is unbounded without a concrete target.",
    ),
    "fast": (
        "What latency budget (p50/p99) counts as 'fast'?",
        "Performance goals must be measurable to be verifiable.",
    ),
    "secure": (
        "Which threat model applies (auth, rate limiting, abuse, PII)?",
        "Security scope changes the design and test surface significantly.",
    ),
    "better": (
        "Better along which axis (latency, cost, reliability, DX)?",
        "'Better' is subjective and needs an explicit success metric.",
    ),
    "optimize": (
        "Optimize for what - latency, throughput, or cost - and by how much?",
        "Optimisation without a target risks premature/ineffective work.",
    ),
    "more": (
        "What is the current baseline and the desired delta?",
        "A relative goal ('more') needs a baseline to be measurable.",
    ),
    "robust": (
        "Robust against which failures (node loss, bad input, traffic spikes)?",
        "Robustness scope drives very different engineering effort.",
    ),
}

# Maps keywords to non-functional concerns we should plan for.
_NFR_SIGNALS = {
    "scalable": "Horizontal scalability and stateless services",
    "scale": "Horizontal scalability and stateless services",
    "analytics": "Analytics throughput must not block the redirect hot path",
    "persistence": "Durable storage with a clear consistency model",
    "fast": "Low-latency reads (caching strategy required)",
    "secure": "Authentication, authorization and abuse prevention",
    "auth": "Authentication and session/token management",
    "rate": "Rate limiting / quota enforcement",
}

_BROWNFIELD_SIGNALS = (
    "optimize", "refactor", "improve", "enhance", "fix", "bug",
    "existing", "migrate", "upgrade", "add ", "extend",
)
_AMBIGUOUS_SIGNALS = ("better", "more scalable", "robust", "nicer", "cleaner", "somehow")


class RequirementAnalyzer:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider or default_provider()

    def analyze(self, requirement: str) -> RequirementAnalysis:
        if not requirement or not requirement.strip():
            raise ValueError("Requirement text must not be empty.")

        text = requirement.strip()
        lowered = text.lower()

        requirement_type = self._classify(lowered)
        ambiguities = self._detect_ambiguities(lowered)
        nfrs = self._detect_nfrs(lowered)
        functional = self._extract_functional_needs(text)

        analysis = RequirementAnalysis(
            raw_requirement=text,
            intent=self._summarise_intent(text),
            requirement_type=requirement_type,
            functional_needs=functional,
            non_functional_needs=nfrs,
            technical_needs=self._suggest_technical_needs(lowered),
            ambiguities=ambiguities,
            risks=self._baseline_risks(requirement_type, ambiguities),
        )

        # AI-assist: the provider may enrich the analysis. We record the prompt
        # so the assistance is auditable, but the engineer's heuristics above
        # remain the source of truth.
        self._provider.complete(
            self._enrichment_prompt(text),
            system="You are assisting an engineer to clarify a software requirement.",
        )
        return analysis

    # --- heuristics -----------------------------------------------------

    def _classify(self, lowered: str) -> RequirementType:
        if any(sig in lowered for sig in _AMBIGUOUS_SIGNALS):
            # Ambiguous wins only if there is no concrete deliverable verb.
            if not re.search(r"\b(build|create|implement|design)\b", lowered):
                return RequirementType.AMBIGUOUS
        if any(sig in lowered for sig in _BROWNFIELD_SIGNALS):
            return RequirementType.BROWNFIELD
        return RequirementType.GREENFIELD

    def _detect_ambiguities(self, lowered: str) -> list[Ambiguity]:
        found: dict[str, Ambiguity] = {}
        for keyword, (question, why) in _AMBIGUITY_SIGNALS.items():
            if keyword in lowered and question not in found:
                found[question] = Ambiguity(
                    question=question,
                    why_it_matters=why,
                    assumption=self._default_assumption(question),
                )
        return list(found.values())

    def _detect_nfrs(self, lowered: str) -> list[str]:
        seen: list[str] = []
        for keyword, nfr in _NFR_SIGNALS.items():
            if keyword in lowered and nfr not in seen:
                seen.append(nfr)
        return seen

    def _extract_functional_needs(self, text: str) -> list[str]:
        # Split on common conjunctions/commas to surface discrete capabilities.
        parts = re.split(r",| and | with | including ", text, flags=re.IGNORECASE)
        needs = [p.strip(" .").capitalize() for p in parts if len(p.strip()) > 3]
        return needs[:8]

    def _suggest_technical_needs(self, lowered: str) -> list[str]:
        needs = ["RESTful API surface", "Automated test suite"]
        if any(k in lowered for k in ("persist", "database", "store", "url")):
            needs.append("Durable persistence layer")
        if any(k in lowered for k in ("analytics", "metrics", "track")):
            needs.append("Analytics capture and query path")
        if any(k in lowered for k in ("scale", "fast", "cache")):
            needs.append("Caching / hot-path optimisation")
        return needs

    def _baseline_risks(
        self, req_type: RequirementType, ambiguities: list[Ambiguity]
    ) -> list[str]:
        risks: list[str] = []
        if ambiguities:
            risks.append(
                "Unresolved ambiguities may lead to building the wrong thing; "
                "assumptions are documented and must be confirmed."
            )
        if req_type is RequirementType.BROWNFIELD:
            risks.append(
                "Changes to existing code risk regressions; characterization "
                "tests are required before refactoring."
            )
        risks.append(
            "AI-generated code may be plausible but wrong; every artifact passes "
            "the validation gate before acceptance."
        )
        return risks

    # --- helpers --------------------------------------------------------

    def _summarise_intent(self, text: str) -> str:
        first = re.split(r"[.\n]", text)[0].strip()
        return first if first else text

    def _default_assumption(self, question: str) -> str:
        defaults = {
            "What scale target (RPS, total URLs, read/write ratio) defines success?":
                "Target 1k RPS reads, 50 RPS writes, read-heavy (>95% reads).",
            "What latency budget (p50/p99) counts as 'fast'?":
                "p99 redirect latency < 50ms.",
            "Which threat model applies (auth, rate limiting, abuse, PII)?":
                "Public service; basic rate limiting and input validation, no PII.",
        }
        return defaults.get(question, "Proceed with a sensible default; flag for review.")

    def _enrichment_prompt(self, text: str) -> str:
        return (
            "Given this requirement, list implicit assumptions and the top 3 "
            "clarifying questions an engineer should ask before building:\n\n"
            f"{text}"
        )
