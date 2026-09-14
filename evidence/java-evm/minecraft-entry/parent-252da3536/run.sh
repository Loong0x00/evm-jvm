#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-252da3536
b=build/java-diff-mc-classcount26-parent-build1-252da3536
python3 "$p/rebuild.py" "$b"
python3 evidence/java-evm/minecraft-entry/classcount26-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount26-parent-fixtures-252da3536
python3 evidence/java-evm/minecraft-entry/classcount26-preflight/tools/gate.py "$b" build/java-diff-mc-classcount26-parent-fixtures-252da3536 build/java-diff-mc-classcount26-parent-gate1-252da3536
python3 evidence/java-evm/minecraft-entry/reentrant-locks-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount26-parent-lock-fixtures-252da3536
python3 evidence/java-evm/minecraft-entry/reentrant-locks-preflight/tools/gate.py "$b" build/java-diff-mc-classcount26-parent-lock-fixtures-252da3536 build/java-diff-mc-classcount26-parent-lock1-252da3536
w=build/java-diff-mc-classcount26-parent-official26a-252da3536
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/original26-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-classcount26-parent-q1a-252da3536
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original26.json"
