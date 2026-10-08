#!/usr/bin/env bash
set -euo pipefail
program_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x /workspace/.cloud-setup/gui-venv/bin/python ]]; then
  export XDG_CACHE_HOME=/workspace/.cloud-setup/cache
  exec /workspace/.cloud-setup/gui-venv/bin/python "$program_dir/valve_control.py" "$@"
fi
exec python3 "$program_dir/valve_control.py" "$@"
