#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/frontend"

echo "Starting frontend..."
echo "Open: http://localhost:5500"

exec python3 -m http.server 5500
