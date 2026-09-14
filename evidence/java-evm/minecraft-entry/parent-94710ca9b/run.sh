#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-94710ca9b
b=build/java-diff-mc-class-new-instance-parent-build1-94710ca9b
python3 "$p/rebuild.py" "$b"
python3 evidence/java-evm/minecraft-entry/class-new-instance-preflight/tools/generate_fixtures.py build/java-diff-mc-class-new-instance-parent-fixtures-94710ca9b
python3 evidence/java-evm/minecraft-entry/class-new-instance-preflight/tools/gate.py "$b" build/java-diff-mc-class-new-instance-parent-fixtures-94710ca9b build/java-diff-mc-class-new-instance-parent-gate1-94710ca9b
python3 "$p/checkpoint_new_instance.py" build/java-diff-mc-class-new-instance-parent-gate1-94710ca9b/success-q1 build/java-diff-mc-class-new-instance-parent-gate1-94710ca9b/reports/success-q1 build/java-diff-mc-class-new-instance-parent-gate1-94710ca9b/checkpoint-states.json
python3 "$p/oom_new_instance.py" "$b" build/java-diff-mc-class-new-instance-parent-oom1-94710ca9b
python3 "$p/failure_new_instance.py" "$b" build/java-diff-mc-class-new-instance-parent-failures1-94710ca9b
python3 "$p/as_subclass_smoke.py" "$b" build/java-diff-mc-class-new-instance-parent-focused1-94710ca9b
python3 "$p/integer_smoke.py" "$b" build/java-diff-mc-class-new-instance-parent-integer1-94710ca9b
python3 "$p/smoke_fast.py" "$b" build/java-diff-mc-class-new-instance-parent-retained1-94710ca9b
w=build/java-diff-mc-class-new-instance-parent-official25a-94710ca9b
python3 "$p/frontier.py" "$b" "$w" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/original25-bindings.json" 7
python3 "$p/q1_after_failure.py" "$b" "$w" build/java-diff-mc-class-new-instance-parent-q1a-94710ca9b
node "$p/verify_receipts.js" "$b" "$w" 1 official > "$p/verified-original25.json"
