#!/bin/bash
set -euo pipefail
p=evidence/java-evm/minecraft-entry/parent-f780f1a13
export PYTHONDONTWRITEBYTECODE=1
python3 "$p/rebuild.py" build/java-diff-mc-entry-parent-arraycopy-bad-f780f1a13 candidate
python3 "$p/replay.py" build/java-diff-mc-entry-parent-arraycopy-bad-f780f1a13 build/java-diff-mc-entry-parent-arraycopy-repro-f780f1a13 candidate
python3 "$p/rebuild.py" build/java-diff-mc-entry-parent-arraycopy-fixed-f780f1a13 repaired
python3 "$p/replay.py" build/java-diff-mc-entry-parent-arraycopy-fixed-f780f1a13 build/java-diff-mc-entry-parent-arraycopy-smoke-f780f1a13 repaired
