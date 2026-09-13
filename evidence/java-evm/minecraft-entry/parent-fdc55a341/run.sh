#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-fdc55a341
b=build/java-diff-mc-resource-enumeration-parent-build-fdc55a341
python3 "$p/rebuild.py" "$b"
python3 "$p/smoke.py" "$b" build/java-diff-mc-resource-enumeration-parent-smoke-fdc55a341
w=build/java-diff-mc-resource-enumeration-parent-official22-fdc55a341
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official22-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-resource-enumeration-parent-q1-fdc55a341
node "$p/verify_receipts.js" "$b" "$w" 1 official
