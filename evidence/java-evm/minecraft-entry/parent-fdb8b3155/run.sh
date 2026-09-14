#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-fdb8b3155
b=build/java-diff-mc-class-as-subclass-parent-build2-fdb8b3155
python3 "$p/rebuild.py" "$b"
python3 "$p/as_subclass_smoke.py" "$b" build/java-diff-mc-class-as-subclass-parent-focused2-fdb8b3155
python3 "$p/integer_smoke.py" "$b" build/java-diff-mc-class-as-subclass-parent-integer2-fdb8b3155
python3 "$p/smoke_fast.py" "$b" build/java-diff-mc-class-as-subclass-parent-retained2-fdb8b3155
w=build/java-diff-mc-class-as-subclass-parent-official24b-fdb8b3155
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official22-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-class-as-subclass-parent-q1b-fdb8b3155
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original24.json"
