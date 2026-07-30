#!/bin/bash
# =============================================================================
# Aegis Framework - Test & Coverage Runner.
# Activates the local virtual environment, runs pytest and outputs code coverage.
# =============================================================================

source .venv/bin/activate

echo "🧪 [Aegis Shell] Launching automated unit testing & coverage matrix..."
pytest --cov=core --cov=broker_adapters --cov=market_feeds --cov=strategies --cov=bots --cov-report=term-missing tests/ "$@"
