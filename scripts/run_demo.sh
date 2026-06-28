#!/usr/bin/env bash
# Runs the AI-assisted engineering demo end-to-end.
# Usage:  ./scripts/run_demo.sh
set -euo pipefail

# Move to the repository root (parent of this script's folder).
cd "$(dirname "$0")/.."

echo "==> Installing dependencies"
python -m pip install -q -r requirements.txt

export PYTHONPATH="src"
REQUIREMENT="Build a scalable URL shortener service with APIs, persistence, and analytics"

echo
echo "==> Running the prototype pipeline on the mandatory requirement"
python -m ai_eng "$REQUIREMENT" --json summary.json

echo
echo "==> Running the full test suite (prototype + URL shortener)"
python -m pytest -q

echo
echo "==> Done. See summary.json for the machine-readable engineering summary."
echo "    Start the demo API with:  cd examples/url_shortener && uvicorn app.main:app --reload"
