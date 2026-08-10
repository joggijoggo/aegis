#!/bin/bash
# =============================================================================
# Aegis Framework - Test & Coverage Runner.
# Activates the local virtual environment, runs pytest and outputs code coverage.
# =============================================================================

source .venv/bin/activate

echo "🧪 [Aegis Shell] Launching automated unit testing & coverage matrix..."
pytest -s --cov=aegis --cov-report=term-missing tests/ "$@"
