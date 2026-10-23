#!/usr/bin/env bash
# 下载 CopyNCE Descriptor 权重到 ./weights/
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/weights/descriptor_vits_224.pth.tar"
FILE_ID="1fWChrrOovX8JOcNNCgrj6liXR2L8yKEu"
WEB="https://drive.google.com/file/d/${FILE_ID}/view?usp=drive_link"

if [[ -f "$DEST" && -s "$DEST" ]]; then
  echo "权重已存在: $DEST"
  exit 0
fi

mkdir -p "$ROOT/weights"
echo "尝试 gdown 下载 Descriptor 权重..."
if command -v docker >/dev/null 2>&1 && docker image inspect copynce-descriptor:latest >/dev/null 2>&1; then
  docker run --rm -v "$ROOT/weights:/weights" copynce-descriptor:latest \
    python -c "import gdown; gdown.download(id='${FILE_ID}', output='/weights/descriptor_vits_224.pth.tar', quiet=False)"
elif python3 -c 'import gdown' 2>/dev/null; then
  python3 -m gdown --id "$FILE_ID" -O "$DEST"
else
  echo "自动下载失败。请浏览器打开并保存为:"
  echo "  $DEST"
  echo "  $WEB"
  exit 1
fi

if [[ ! -s "$DEST" ]]; then
  echo "下载结果为空，请手动下载: $WEB" >&2
  exit 1
fi
echo "已保存: $DEST"
