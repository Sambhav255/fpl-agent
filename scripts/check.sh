#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$ROOT/backend" && uv run pytest && uv run ruff check . && uv run mypy src)
(cd "$ROOT/apps/web" && npm run lint && npm run typecheck && npm run test && npm run build && npm run test:e2e)
