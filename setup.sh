#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "=== AI-Powered Face Authentication: local setup ==="

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found."
  echo "Install Python 3.12+ and run this script again."
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_BIN" -m venv venv
fi

source venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing project dependencies..."
python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  echo "Creating local .env..."
  LOCAL_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
  cat > .env <<EOF
FACE_AUTH_API_KEY=$LOCAL_KEY
PUBLIC_DEMO_MODE=true
COOKIE_SECURE=false
CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
EOF
  echo "Created .env with a new local API key."
else
  echo ".env already exists; leaving it unchanged."
fi

mkdir -p database

echo
echo "Setup complete."
echo "Start backend:  bash run_backend.sh"
echo "Start frontend: bash run_frontend.sh"
