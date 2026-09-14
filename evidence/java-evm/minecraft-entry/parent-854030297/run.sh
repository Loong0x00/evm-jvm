#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-854030297
b=build/java-diff-mc-concurrent-queue-parent-build1-854030297
python3 "$p/rebuild.py" "$b"
python3 evidence/java-evm/minecraft-entry/concurrent-linked-queue-preflight/tools/generate_fixtures.py build/java-diff-mc-concurrent-queue-parent-fixtures-854030297
python3 evidence/java-evm/minecraft-entry/concurrent-linked-queue-preflight/tools/gate.py "$b" build/java-diff-mc-concurrent-queue-parent-fixtures-854030297 build/java-diff-mc-concurrent-queue-parent-gate1-854030297
python3 "$p/queue_oom.py" "$b" build/java-diff-mc-concurrent-queue-parent-oom1-854030297
w=build/java-diff-mc-concurrent-queue-parent-official26a-854030297
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/original26-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-concurrent-queue-parent-q1a-854030297
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original26.json"
