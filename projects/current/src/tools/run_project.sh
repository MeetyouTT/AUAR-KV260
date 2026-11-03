#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [ "$#" -eq 0 ]; then
    set -- demo
fi
exec python3 -s tools/aura_project.py "$@"
