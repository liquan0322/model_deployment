#!/usr/bin/env bash
# 一键停止 CopyNCE Descriptor
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "==> 停止 CopyNCE Descriptor..."
docker compose stop
docker compose ps
echo "==> 已停止"
