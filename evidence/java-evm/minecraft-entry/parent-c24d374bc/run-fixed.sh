#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-c24d374bc
bad=build/java-diff-mc-properties-parent-candidate-c24d374bc
fixed=build/java-diff-mc-properties-parent-fixed-c24d374bc
python3 "$p/probe.py" "$bad" build/java-diff-mc-properties-parent-regression2-c24d374bc candidate
python3 "$p/rebuild.py" "$fixed" repaired
python3 "$p/probe.py" "$fixed" build/java-diff-mc-properties-parent-smoke-c24d374bc repaired
python3 "$p/frontier.py" "$fixed" build/java-diff-mc-properties-parent-official20-c24d374bc /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official20-bindings.json" 7
node evidence/java-evm/minecraft-entry/parent-f780f1a13/verify_receipts.js "$fixed" build/java-diff-mc-properties-parent-official20-c24d374bc official
