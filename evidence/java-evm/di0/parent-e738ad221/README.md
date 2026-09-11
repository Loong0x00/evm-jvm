# Parent DI0 optimization replay, additional failure and explicit yield refinement

Not DI0 acceptance. All fixture ZIP/DEFLATE bytes are generated trusted test inputs,
not server bytes. Go/Java decompression is a TEST oracle only; EVM runs alone in the
actual decoder path over accepted AS0/ZI0. Production freeze is in
JAVA_EVM_MC_DI0_PLAN.md; rationale in JAVA_EVM_MC_DI0_IMPLEMENTATION_PREFLIGHT.md.

- Root reports replay e738ad221/eaf473946 worker source, freshly rebuilt exact
  artifactac27469d5aaf531c9bebc49e78899bc4507f42eabee281d8609a0e4c3b7d085b.
 37 original,29 tree/Java8,4 same-binding pairs and3 full quantum sweeps passed.
 `run.sh` records the actual parent command; sources/build instructions are in
 `../budget-preflight/README.md`. `verify.py` here checks THESE fresh parent reports.
- `headers64/`: independent64-block extension. Unmodified optimized q128 genuinely
  OOGs at100M; q1/q8/q64 and Java8 all succeed. Strict exit1 is EXPECTED HISTORICAL
  FAILURE, not acceptance. `source.go.txt` is its complete reproducible fixture driver;
  replace budget trees.go with it and use DI0_ARTIFACT/DI0_TREE_OUT to fresh locations.
- `yield/`: parent disposable source refinement, upper-bound units/25M reserve after
  positive progress. Pinned artifact/source/runtime/init hashes in artifact-summary.
  The37/29/4 enlarged cases pass, including budget-yield and true70K first-action OOG
  with a completed CHANGED SSTORE observed by TEST instrumentation. An initial60K
  trial was too early to prove that write; its failed proof gate is retained in
  initial-lowgas.log/watchdog. To recreate that failed trial only, change70000/70_000
  to60000/60_000 in the archived parent replay Go copy. It is not counted as a pass.
- `yield/long-performance-report.json`:6 same-binding pairs,5 completeq1..q128 sweeps,
  including64 AND129 empty dynamic blocks (128/258 actions). All input/work/output/
  CRC/pages/final/trie-state comparisons pass. Maximum observed call75586130gas;
  this is not a universal worst-case theorem.

Persistence.finalRoot is a TRIE root, not resource F. Actual4-process60-publication
sequence and dynamic-cache fresh-process chains remain checked. PID/RSS/elapsed/
LevelDB layout are environmental observations. No post-failure state is used as output.

## Fresh reconstruction without archived report reuse

From repository root, pinned solc must be available in jvmevm/runtime/node_modules:

```
python3 evidence/java-evm/di0/parent-e738ad221/verify.py
python3 evidence/java-evm/watchdog.py \
  build/java-diff-UNIQUE.log build/java-diff-UNIQUE-watchdog.json \
  python3 evidence/java-evm/di0/parent-e738ad221/reproduce-yield.py \
  build/java-diff-di0-yield-UNIQUE
```

Choose NEW names; reconstruction refuses an existing workspace, rebuilds pinned
artifact and four real binaries, regenerates inputs, executes37/29/4 cases,6pairs/
5sweeps and Java8u504 oracles, then strictly checks freshly written reports. It never
writes this archive. Sources are this directory and the tracked budget-preflight
sources, not old ignored workspaces. Expected whole run is a few minutes, ordinary
100M EVM calls,20min4GiB outer watchdog. Build DBs/binaries are disposable.

`reconstruction.log`/`reconstruction-watchdog.json` capture the parent's actual fresh
run of this reconstruction script; its reports are copied under `reconstruction/`.
