"""Command-line entry point for the pipeline.

Usage::

    python -m ai_eng "Build a scalable URL shortener service ..."
    python -m ai_eng --run-tests --json out.json "<requirement>"

By default it prints the Markdown engineering summary to stdout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .orchestrator import Pipeline
from .output import OutputGenerator


def _repo_root() -> Path:
    # src/ai_eng/__main__.py -> repo root is two levels above src.
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai-eng",
        description="Engineer-led, AI-assisted requirement-to-output pipeline.",
    )
    parser.add_argument("requirement", help="The requirement text to process.")
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Execute the project's pytest suite as part of validation.",
    )
    parser.add_argument(
        "--json",
        metavar="PATH",
        help="Also write the machine-readable JSON summary to PATH.",
    )
    parser.add_argument(
        "--root",
        metavar="PATH",
        default=str(_repo_root()),
        help="Repository root used to resolve artifacts (default: auto-detected).",
    )
    args = parser.parse_args(argv)

    pipeline = Pipeline(args.root)
    summary = pipeline.run(args.requirement, run_tests=args.run_tests)

    generator = OutputGenerator()
    print(generator.to_markdown(summary))

    if args.json:
        Path(args.json).write_text(generator.to_json(summary), encoding="utf-8")
        print(f"\n[wrote JSON summary to {args.json}]", file=sys.stderr)

    # Exit non-zero if the quality gate failed, so CI can depend on it.
    return 0 if summary.validation.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
