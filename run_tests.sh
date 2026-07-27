#!/bin/bash
"""Aegis Framework - Test Execution Runner.

Activates the local virtual environment and runs the pytest matrix cleanly.
"""

# Active local virtual environment isolation layers
source .venv/bin/activate

echo "🧪 [Aegis Shell] Launching automated unit testing suite..."
pytest tests/ "$@"
