#!/usr/bin/env bash
# One-shot local/GPU node runner after setup.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/.."

source "$ROOT/env.sh"

LIMIT="${LIMIT:-1}"
OUT="${OUT:-$ROOT/outputs/local_run}"

python "$ROOT/bin/manifest_csv.py" --limit "$LIMIT" --output "$ROOT/manifests/local_manifest.jsonl"
python "$ROOT/bin/fold_csv.py" \
  --manifest-only "$ROOT/manifests/local_manifest.jsonl" \
  --output-dir "$OUT"

echo "Wrote structures under $OUT"
