# DI0 output-page/persistence preflight evidence

Unaccepted disposable generated-fixture evidence at `094c51dbc`. It contains no
official server/JAR bytes and proves no Java/ClassLoader/Minecraft execution.
`JAVA_EVM_MC_DI0_PERSISTENCE_PREFLIGHT.md` states the boundary and measurements.

Files:

- `DI0OutputPages.sol`: sole disposable Solidity source; copied to the compiler as
  `DI0Inflate.sol`. It starts from parent corrected SHA `6a11700d...f349bead`.
- `compile.js.txt`: pinned solc 0.8.30 build.
- `replay.go.txt`: generated ZIPs, trusted Go fixture checks, EVM setup/cases and
  strict-selector/q/OOG controls. Go never supplies decode metadata or output pages.
- `persistence.go.txt`: per-mutation trie/code sync + manifest/file/directory fsync
  and four real child-process reopen stages.
- `execution-report.json`: 37 case records, gas, roots, output/page hashes, controls,
  durable sequence and process evidence.
- `artifact-summary.json`, `compile.log`, `repro.log`, `watchdog.json`, `SHA256SUMS`.

The code-bearing LevelDB, compiled EVM artifact, npm modules and replay executable
remain ignored intermediates. Reproduce into a fresh ignored directory:

```sh
set -eu
work=build/java-diff-mc-di0-persistence-preflight-replay-$(date +%s)
mkdir -p "$work"
cp jvmevm/artifactstore/zi0/runtime/package{,-lock}.json "$work"/
cp evidence/java-evm/di0/persistence-preflight/DI0OutputPages.sol "$work/DI0Inflate.sol"
cp evidence/java-evm/di0/persistence-preflight/compile.js.txt "$work/compile.js"
cp evidence/java-evm/di0/persistence-preflight/replay.go.txt "$work/replay.go"
cp evidence/java-evm/di0/persistence-preflight/persistence.go.txt "$work/persistence.go"
(cd "$work" && npm ci --ignore-scripts --no-audit --no-fund && node compile.js && \
  go build -trimpath -o replay replay.go persistence.go && \
  ./replay DI0Inflate.json > execution-report.replay.json)
```

For the same 20-minute/4GiB process-group watchdog, run from repository root:

```sh
python3 evidence/java-evm/watchdog.py "$work/run.log" "$work/watchdog.json" \
  bash -lc "cd '$work' && ./replay DI0Inflate.json"
```

Elapsed time, RSS, PIDs, LevelDB size and trie roots may vary with environment/run.
Compiler/source/runtime hashes, fixture ZIP hash, selectors, output hashes, call gas,
q1/q128 equality and generated outcomes are expected deterministic for the pinned
revision and toolchain. Never overwrite this historical run; archive a new directory.
