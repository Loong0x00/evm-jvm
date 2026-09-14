#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-1cdc3be88
b=build/java-diff-mc-copy-on-write-parent-build1-1cdc3be88
python3 "$p/rebuild.py" "$b"
python3 evidence/java-evm/minecraft-entry/copy-on-write-array-list-preflight/tools/generate_fixtures.py build/java-diff-mc-copy-on-write-parent-fixtures-1cdc3be88
python3 evidence/java-evm/minecraft-entry/copy-on-write-array-list-preflight/tools/gate.py "$b" build/java-diff-mc-copy-on-write-parent-fixtures-1cdc3be88 build/java-diff-mc-copy-on-write-parent-gate1-1cdc3be88
python3 "$p/cow_oom.py" "$b" build/java-diff-mc-copy-on-write-parent-oom1-1cdc3be88
python3 evidence/java-evm/minecraft-entry/class-new-instance-preflight/tools/generate_fixtures.py build/java-diff-mc-copy-on-write-parent-newinstance-fixtures-1cdc3be88
python3 evidence/java-evm/minecraft-entry/class-new-instance-preflight/tools/gate.py "$b" build/java-diff-mc-copy-on-write-parent-newinstance-fixtures-1cdc3be88 build/java-diff-mc-copy-on-write-parent-newinstance1-1cdc3be88
python3 "$p/checkpoint_new_instance.py" build/java-diff-mc-copy-on-write-parent-newinstance1-1cdc3be88/success-q1 build/java-diff-mc-copy-on-write-parent-newinstance1-1cdc3be88/reports/success-q1 build/java-diff-mc-copy-on-write-parent-newinstance1-1cdc3be88/checkpoint-states.json
python3 "$p/oom_new_instance.py" "$b" build/java-diff-mc-copy-on-write-parent-newinstance-oom1-1cdc3be88
python3 "$p/failure_new_instance.py" "$b" build/java-diff-mc-copy-on-write-parent-newinstance-failures1-1cdc3be88
python3 "$p/as_subclass_smoke.py" "$b" build/java-diff-mc-copy-on-write-parent-focused1-1cdc3be88
python3 "$p/integer_smoke.py" "$b" build/java-diff-mc-copy-on-write-parent-integer1-1cdc3be88
python3 "$p/smoke_fast.py" "$b" build/java-diff-mc-copy-on-write-parent-retained2-1cdc3be88
w=build/java-diff-mc-copy-on-write-parent-official25a-1cdc3be88
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/original25-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-copy-on-write-parent-q1a-1cdc3be88
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original25.json"
