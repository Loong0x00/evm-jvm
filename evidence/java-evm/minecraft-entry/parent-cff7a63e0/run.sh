#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-cff7a63e0
b=build/java-diff-mc-classcount25-parent-build1-cff7a63e0
python3 "$p/rebuild.py" "$b"
python3 "$p/as_subclass_smoke.py" "$b" build/java-diff-mc-classcount25-parent-focused1-cff7a63e0
python3 "$p/integer_smoke.py" "$b" build/java-diff-mc-classcount25-parent-integer1-cff7a63e0
python3 "$p/smoke_fast.py" "$b" build/java-diff-mc-classcount25-parent-retained1-cff7a63e0
w=build/java-diff-mc-classcount25-parent-official25a-cff7a63e0
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/original25-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-classcount25-parent-q1a-cff7a63e0
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original25.json"
