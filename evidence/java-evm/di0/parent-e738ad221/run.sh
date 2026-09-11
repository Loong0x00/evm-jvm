#!/bin/bash
set -euo pipefail
repo=$(pwd)
w="$repo/build/java-diff-mc-di0-parent-e738ad221"
e="$repo/evidence/java-evm/di0/parent-e738ad221"
(cd "$w" && ./replay DI0Inflate.json) > "$e/execution-report.json"
DI0_ARTIFACT="$w/DI0Inflate.json" DI0_TREE_OUT="$e/trees" "$w/trees" > "$e/trees/evm.json"
(cd "$w" && ./performance DI0Inflate.json) > "$e/performance-report.json"
/usr/lib/jvm/java-8-openjdk/bin/java -Xms16m -Xmx256m -XX:MaxMetaspaceSize=128m -Xss1m -cp "$w/java8" InflateOracle "$e/trees/generated" > "$e/trees/java8.json"
