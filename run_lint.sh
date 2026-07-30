#!/bin/bash

# Active local virtual environment isolation layers
source .venv/bin/activate

echo "🛡️ [Aegis Shell] Launching code style and compliance scans..."
ruff check strategies/ broker_adapters/ market_feeds/ strategies/ bots/ core/ tests/ "$@"
