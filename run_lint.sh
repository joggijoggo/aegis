#!/bin/bash

# Active local virtual environment isolation layers
source .venv/bin/activate

echo "🛡️ [Aegis Shell] Launching code style and compliance scans..."
ruff check aegis/ tests/ "$@" && mypy aegis/ --check-untyped-defs
