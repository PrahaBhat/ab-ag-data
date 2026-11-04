#!/bin/bash
#SBATCH -J esmfold2_abag
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 02:00:00
#SBATCH -o logs/esmfold2-%j.out
#SBATCH -e logs/esmfold2-%j.err

set -euo pipefail

# Repo root (directory containing esmfold2/ and the CSV)
REPO_ROOT="${REPO_ROOT:-$SLURM_SUBMIT_DIR}"
cd "$REPO_ROOT"

source "$REPO_ROOT/esmfold2/env.sh"

mkdir -p "$REPO_ROOT/esmfold2/logs"

# Optional overrides (export before sbatch):
#   FOLD_LIMIT=100  FOLD_OFFSET=0  MAX_TOTAL_LENGTH=2000
FOLD_LIMIT="${FOLD_LIMIT:-10}"
FOLD_OFFSET="${FOLD_OFFSET:-0}"
RUN_NAME="${RUN_NAME:-vista_${SLURM_JOB_ID}}"
OUT_DIR="$REPO_ROOT/esmfold2/outputs/$RUN_NAME"
MANIFEST="$REPO_ROOT/esmfold2/manifests/${RUN_NAME}.jsonl"

python "$ESMFOLD2_ROOT/bin/manifest_csv.py" \
  --output "$MANIFEST" \
  --offset "$FOLD_OFFSET" \
  --limit "$FOLD_LIMIT"

python "$ESMFOLD2_ROOT/bin/fold_csv.py" \
  --manifest-only "$MANIFEST" \
  --output-dir "$OUT_DIR" \
  --skip-existing

echo "Outputs: $OUT_DIR"
