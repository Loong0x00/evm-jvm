#!/bin/bash
set -euo pipefail
p=evidence/java-evm/minecraft-entry/parent-f780f1a13
b=build/java-diff-mc-entry-parent-arraycopy-fixed-f780f1a13
o=build/java-diff-mc-entry-parent-arraycopy-official13-f780f1a13
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
python3 -c 'import json; j=json.load(open("build/arraycopy-parent-watchdog.json")); assert j["exit"]==0 and j["limit"] is None'
python3 "$p/verify-bootstrap.py" build/java-diff-mc-entry-parent-arraycopy-bootstrap-f780f1a13
python3 "$p/replay.py" "$b" build/java-diff-mc-entry-parent-arraycopy-edges-f780f1a13 edges
python3 "$p/frontier.py" "$b" "$o" /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official13-bindings.json"
node "$p/verify_original.js" "$o" official "$b"
