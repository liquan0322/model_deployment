#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  proto/copynce_descriptor.proto

python - <<'PY'
from pathlib import Path
import re

path = Path("proto/copynce_descriptor_pb2_grpc.py")
text = path.read_text(encoding="utf-8")
text = re.sub(
    r"^import copynce_descriptor_pb2 as (.+)$",
    r"from proto import copynce_descriptor_pb2 as \1",
    text,
    flags=re.M,
)
path.write_text(text, encoding="utf-8")
print("ok", path)
PY
