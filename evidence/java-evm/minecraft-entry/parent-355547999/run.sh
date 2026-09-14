#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-355547999
b=build/java-diff-mc-reentrant-locks-parent-build1-355547999
python3 "$p/rebuild.py" "$b"
python3 evidence/java-evm/minecraft-entry/reentrant-locks-preflight/tools/generate_fixtures.py build/java-diff-mc-reentrant-locks-parent-fixtures-355547999
python3 evidence/java-evm/minecraft-entry/reentrant-locks-preflight/tools/gate.py "$b" build/java-diff-mc-reentrant-locks-parent-fixtures-355547999 build/java-diff-mc-reentrant-locks-parent-gate1-355547999
python3 evidence/java-evm/minecraft-entry/class-new-instance-preflight/tools/generate_fixtures.py build/java-diff-mc-reentrant-locks-parent-newinstance-fixtures-355547999
python3 evidence/java-evm/minecraft-entry/class-new-instance-preflight/tools/gate.py "$b" build/java-diff-mc-reentrant-locks-parent-newinstance-fixtures-355547999 build/java-diff-mc-reentrant-locks-parent-newinstance1-355547999
python3 "$p/checkpoint_new_instance.py" build/java-diff-mc-reentrant-locks-parent-newinstance1-355547999/success-q1 build/java-diff-mc-reentrant-locks-parent-newinstance1-355547999/reports/success-q1 build/java-diff-mc-reentrant-locks-parent-newinstance1-355547999/checkpoint-states.json
python3 "$p/cow_oom.py" "$b" build/java-diff-mc-reentrant-locks-parent-cow-oom1-355547999
python3 "$p/oom_new_instance.py" "$b" build/java-diff-mc-reentrant-locks-parent-newinstance-oom1-355547999
python3 "$p/failure_new_instance.py" "$b" build/java-diff-mc-reentrant-locks-parent-newinstance-failures1-355547999
python3 "$p/as_subclass_smoke.py" "$b" build/java-diff-mc-reentrant-locks-parent-focused1-355547999
python3 "$p/integer_smoke.py" "$b" build/java-diff-mc-reentrant-locks-parent-integer1-355547999
python3 "$p/smoke_fast.py" "$b" build/java-diff-mc-reentrant-locks-parent-retained1-355547999
w=build/java-diff-mc-reentrant-locks-parent-official25a-355547999
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/original25-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-reentrant-locks-parent-q1a-355547999
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original25.json"
