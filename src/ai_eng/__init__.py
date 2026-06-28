"""AI-Assisted Software Engineering prototype.

An engineer-led pipeline that transforms a natural-language requirement into a
validated, production-quality engineering summary. AI assists within each task;
the engineer owns execution and quality.
"""

from .models import (
    Ambiguity,
    AssistLevel,
    EngineeringSummary,
    RequirementAnalysis,
    RequirementType,
    Task,
    TaskGraph,
    ValidationResult,
)
from .orchestrator import Pipeline

__all__ = [
    "Pipeline",
    "Ambiguity",
    "AssistLevel",
    "EngineeringSummary",
    "RequirementAnalysis",
    "RequirementType",
    "Task",
    "TaskGraph",
    "ValidationResult",
]

__version__ = "0.1.0"
