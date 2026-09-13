#!/bin/bash
# One fresh LOCAL384 generated-only candidate gate. No original payload is accepted.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules
p=evidence/java-evm/minecraft-entry/linked-hash-set-preflight
tag=${1:?fresh tag required}
b=build/java-diff-mc-linked-hash-set-${tag}
s=build/java-diff-mc-linked-hash-set-${tag}-smoke
[ ! -e "$b" ] && [ ! -e "$s" ]
python3 "$p/rebuild.py" "$b"
python3 "$p/smoke.py" "$b" "$s"
