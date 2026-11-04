# Placeholder — run setup.sh once to regenerate paths for this machine.
#   bash esmfold2/setup.sh && source esmfold2/env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
export ESMFOLD2_ROOT="${ESMFOLD2_ROOT:-$SCRIPT_DIR}"
export PYTHONPATH="${ESMFOLD2_ROOT}:${PYTHONPATH:-}"

if [[ -f "$ESMFOLD2_ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ESMFOLD2_ROOT/.venv/bin/activate"
fi
