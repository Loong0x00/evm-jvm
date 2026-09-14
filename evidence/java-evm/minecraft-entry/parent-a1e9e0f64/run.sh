#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-a1e9e0f64;b=build/java-diff-mc-classcount27-parent-build1-a1e9e0f64
python3 "$p/rebuild.py" "$b"
python3 evidence/java-evm/minecraft-entry/classcount27-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount27-parent-fixtures-a1e9e0f64
python3 evidence/java-evm/minecraft-entry/classcount27-preflight/tools/gate.py "$b" build/java-diff-mc-classcount27-parent-fixtures-a1e9e0f64 build/java-diff-mc-classcount27-parent-gate1-a1e9e0f64
w=build/java-diff-mc-classcount27-parent-official27a-a1e9e0f64
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/original27-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-classcount27-parent-q1a-a1e9e0f64
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original27.json"
