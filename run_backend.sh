#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".env" ]; then
  echo "Error: .env not found."
  echo "Run: bash setup.sh"
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "Error: venv not found."
  echo "Run: bash setup.sh"
  exit 1
fi

source venv/bin/activate

# Export every variable from .env so FastAPI can read it with os.getenv().
set -a
source .env
set +a

echo "Starting FastAPI backend..."
echo "API:  http://127.0.0.1:8000"
echo "Docs: http://127.0.0.1:8000/docs"

exec python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
