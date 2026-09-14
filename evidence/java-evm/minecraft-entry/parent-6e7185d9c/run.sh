#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-6e7185d9c
b=build/java-diff-mc-java-version-split-parent-build3-6e7185d9c
python3 "$p/rebuild.py" "$b"
fresh=build/java-diff-mc-java-version-split-parent-smoke5-6e7185d9c
python3 "$p/smoke_fast.py" "$b" "$fresh"
node "$p/verify_receipts.js" "$b" build/java-diff-mc-java-version-split-parent-smoke3-6e7185d9c 1 q1 > "$p/verified-existing-q1.json"
python3 "$p/verify_existing_q1.py" build/java-diff-mc-java-version-split-parent-smoke3-6e7185d9c "$fresh" > "$p/q1-fresh-equivalence.json"
w=build/java-diff-mc-java-version-split-parent-official22c-6e7185d9c
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official22-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-java-version-split-parent-q1c-6e7185d9c
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original22.json"
