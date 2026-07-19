#!/bin/bash
# Forward-accrual: re-fetch trailing 60d of native 5m for the whole universe.
# Run weekly (cron or by hand): bash tools/accrue5m.sh
cd "$(dirname "$0")/.." && app/.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "app")
exec(open("tools/fetch5m.py").read().replace('if out.exists(): continue', 'pass  # refresh: merge windows'))
PY
