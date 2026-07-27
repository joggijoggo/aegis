#!/bin/bash
"""Aegis Framework - Lint Execution Runner.

Activates the local virtual environment and executes code compliance checks.
"""

# Active local virtual environment isolation layers
source .venv/bin/activate

echo "🛡️ [Aegis Shell] Launching code style and compliance scans..."
ruff check core/ tests/ "$@"
