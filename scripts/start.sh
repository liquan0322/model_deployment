#!/usr/bin/env bash
# 一键启动 CopyNCE Descriptor（会先停其它特征服务，避免抢 GPU）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZSN="$(cd "$ROOT/.." && pwd)"

echo "==> 停止其它特征服务（若在运行）..."
for peer in anypattern peicd; do
  if [[ -f "$ZSN/$peer/docker-compose.yml" ]]; then
    (cd "$ZSN/$peer" && docker compose stop) || true
  fi
done

echo "==> 启动 CopyNCE Descriptor..."
cd "$ROOT"
docker compose up -d
docker compose ps
echo "==> CopyNCE 入口: localhost:49890  (desc: 49891/49892/49893)"
