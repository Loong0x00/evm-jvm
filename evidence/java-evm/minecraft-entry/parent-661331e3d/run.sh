#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-661331e3d
b=build/java-diff-mc-integer-parent-build2-661331e3d
python3 "$p/rebuild.py" "$b"
python3 "$p/integer_smoke.py" "$b" build/java-diff-mc-integer-parent-focused2-661331e3d
python3 "$p/smoke_fast.py" "$b" build/java-diff-mc-integer-parent-retained2-661331e3d
w=build/java-diff-mc-integer-parent-official22b-661331e3d
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official22-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-integer-parent-q1b-661331e3d
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original22.json"
