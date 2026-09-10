# MC-DI0 decoder budget preflight evidence

Disposable, generated-fixture-only evidence based on Git revision `36ad7d298`.
This is not a DI0 freeze/acceptance or production source. It contains no official
JAR bytes and proves no Java/ClassLoader/Minecraft/EULA/listener/Done behavior.
`JAVA_EVM_MC_DI0_BUDGET_RESULTS.md` gives the measured result and boundary.

## Contents

- `DI0OutputPages.sol`: optimized disposable Solidity source (compile as
  `DI0Inflate.sol`), starting from persistence source SHA `d117856...`.
- `compile.js.txt`: pinned solc 0.8.30 optimizer/viaIR/Cancun/metadata-off build.
- `replay.go.txt`, `persistence.go.txt`: original 37-case strict replay, refusal/
  rollback/page checks, 60-publication disk replay, and added dynamic-cache fresh
  process replay. Host code supplies no decode tables, offsets, CRC, or plaintext.
- `trees.go.txt`, `trees/generated/`: parent 22 tree cases plus alternate ordering,
  mixed cache transitions, and reserved fixed symbols/distances.
- `performance.go.txt`: same-binding q1/q128 comparisons and exhaustive q1..q128
  sweeps for the former blockers and mixed cache transition.
- `InflateOracle.java`: HOST-TEST-ONLY Java8 oracle for generated fixtures.
- `execution-report.json`, `trees/{evm,java8}.json`, `performance-report.json`:
  strict outputs. `verify.py` rejects valid OOGs and oracle mismatches.
- `artifact-summary.json`, watchdog files, `compile.log`, `SHA256SUMS`.

## Reproduce

From repository root (never overwrite this evidence directory):

```sh
set -eu
work=build/java-diff-mc-di0-budget-preflight-replay-$(date +%s)
mkdir -p "$work" evidence/java-evm/di0/budget-preflight/trees/generated
cp jvmevm/artifactstore/zi0/runtime/package{,-lock}.json "$work"/
cp evidence/java-evm/di0/budget-preflight/DI0OutputPages.sol "$work/DI0Inflate.sol"
cp evidence/java-evm/di0/budget-preflight/compile.js.txt "$work/compile.js"
cp evidence/java-evm/di0/budget-preflight/{replay.go.txt,persistence.go.txt,trees.go.txt,performance.go.txt} "$work"/
mv "$work/replay.go.txt" "$work/replay.go"
mv "$work/persistence.go.txt" "$work/persistence.go"
(cd "$work" && npm ci --ignore-scripts --no-audit --no-fund && node compile.js)
(cd "$work" && go build -trimpath -o replay replay.go persistence.go)
(cd "$work" && ./replay DI0Inflate.json > execution-report.json)

python3 - "$work/replay.go" "$work/tree-base.go" <<'PY'
import sys
s=open(sys.argv[1]).read().replace('func main() {','func originalMain() {',1)
open(sys.argv[2],'w').write(s)
PY
cp "$work/trees.go.txt" "$work/trees.go"
go build -trimpath -o "$work/tree-replay" "$work/tree-base.go" "$work/persistence.go" "$work/trees.go"
DI0_ARTIFACT="$work/DI0Inflate.json" DI0_TREE_OUT="$work/tree-fixtures" "$work/tree-replay" > "$work/trees-report.json"

python3 - "$work/trees.go.txt" "$work/perf-trees.go" <<'PY'
import sys
s=open(sys.argv[1]).read().replace('func main() {','func treesMain() {',1)
open(sys.argv[2],'w').write(s)
PY
cp "$work/performance.go.txt" "$work/performance.go"
(cd "$work" && go build -trimpath -o performance tree-base.go persistence.go perf-trees.go performance.go && ./performance DI0Inflate.json > performance-report.json)

mkdir "$work/java8"
/usr/lib/jvm/java-8-openjdk/bin/javac -d "$work/java8" evidence/java-evm/di0/budget-preflight/InflateOracle.java
/usr/lib/jvm/java-8-openjdk/bin/java -Xms16m -Xmx256m -XX:MaxMetaspaceSize=128m -Xss1m -cp "$work/java8" InflateOracle "$work/tree-fixtures/generated" > "$work/java8.json"
python3 evidence/java-evm/di0/budget-preflight/verify.py
```

The archived combined gate additionally used `timeout --signal=KILL 1200` and
`ulimit -v 4194304`; its exact command is in `watchdog.json`. Compiler/source/
runtime/artifact hashes, EVM gas, output/root/state values, selectors, and generated
oracles are deterministic. PIDs, elapsed time, RSS, LevelDB bytes, and persistence
trie roots can vary by environment. The ignored artifact/database remain reproducible
intermediates; all authoritative sources, fixtures, reports, and commands are tracked.
