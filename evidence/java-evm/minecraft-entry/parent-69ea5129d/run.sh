#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-69ea5129d
b=build/java-diff-mc-class-for-name-parent-build2-69ea5129d
python3 "$p/rebuild.py" "$b"
python3 "$p/smoke.py" "$b" build/java-diff-mc-class-for-name-parent-smoke2-69ea5129d
w=build/java-diff-mc-class-for-name-parent-official22b-69ea5129d
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official22-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-class-for-name-parent-q1b-69ea5129d
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original22.json"
