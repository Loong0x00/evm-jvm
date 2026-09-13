#!/bin/bash
# Generated-only Boolean gate; intentionally does not take an original-JAR argument.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../.." && pwd)
stamp=${1:-$(date -u +%Y%m%dT%H%M%SZ)}
base="$root/build/java-diff-mc-boolean-$stamp"
export PYTHONDONTWRITEBYTECODE=1
: "${NODE_PATH:?set absolute NODE_PATH to the pinned solc 0.8.30 modules}"
case "$NODE_PATH" in /*) ;; *) echo 'NODE_PATH must be absolute' >&2; exit 2;; esac
python3 "$root/evidence/java-evm/minecraft-entry/boolean-preflight/rebuild.py" "$base-build"
python3 "$root/evidence/java-evm/minecraft-entry/boolean-preflight/tools/monitor_process_tree.py" "$base-monitor.json" \
  python3 "$root/evidence/java-evm/minecraft-entry/boolean-preflight/smoke.py" "$base-build" "$base-smoke"
python3 "$root/evidence/java-evm/minecraft-entry/boolean-preflight/archive.py" "$base-build" "$base-smoke" "$base-monitor.json"
