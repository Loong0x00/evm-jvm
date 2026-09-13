#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-b6d030f95
b=build/java-diff-mc-system-property-parent-build-b6d030f95
python3 "$p/rebuild.py" "$b"
python3 "$p/smoke.py" "$b" build/java-diff-mc-system-property-parent-smoke-b6d030f95
w=build/java-diff-mc-system-property-parent-official22-b6d030f95
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official22-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-system-property-parent-q1-b6d030f95
node "$p/verify_receipts.js" "$b" "$w" 1 official
