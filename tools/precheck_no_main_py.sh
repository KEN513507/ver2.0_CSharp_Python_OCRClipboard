#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${repo_root}/src/python/ocr_worker/main.py"

if [[ -f "${target}" ]]; then
  echo "禁止: src/python/ocr_worker/main.py が存在します。__main__.py を使用してください。" >&2
  exit 1
fi
