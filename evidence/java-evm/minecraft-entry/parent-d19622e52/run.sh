#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-d19622e52
b=build/java-diff-mc-classloader-type-parent-build-d19622e52
w=build/java-diff-mc-classloader-type-parent-official22-d19622e52
python3 "$p/rebuild.py" "$b"
python3 "$p/smoke.py" "$b" build/java-diff-mc-classloader-type-parent-smoke-d19622e52
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official22-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-classloader-type-parent-q1-d19622e52
node "$p/verify_receipts.js" "$b" "$w" 1 official
