# P24 local raw72 / q65536 amendment

This isolated stage amends only the local P24 Solidity profile copied from
`../parent-max-objects-4096` (basis commit `320e595338462e5abdbb38c5086a275547b9139c`).
The historical parent directory is unchanged.

## Exact scope

- Engine admission: at most **72 raw classfiles** and **513,384 aggregate bytes**.
- `maxJvmSteps`: **1..65,536**. `maxInternalSteps` remains **1..4,096**.
- Coordinator arrays, constructor bounds, and aggregate byte checks match those limits.
- Only the corresponding raw-count/raw-byte `_configRoot` leaves change. All **97 bootstrap
  leaves/images** remain byte-identical; the P24 label and bootstrap root
  `e5fd9b703bccd28948443e9027362ea6ff9f46a4f4d53f88c523fa4a8b5d75e6` are retained.
- Other caps, accounting, 25,000,000-gas commit reserve, and semantics are unchanged.
  The local observer keeps the 30-second owned-call watchdog and uses the previously
  authorized 1,000,000,000 ordinary-gas budget. The engine runtime is over EIP-170;
  this is a **LOCAL Execute/Call profile**, not a standard deployment claim.

`tools/build.py` compares normalized Solidity against the historical P24 sources,
checks the 97 ordered bootstrap leaves, compiles with the pinned offline solc 0.8.30
build scripts, and verifies driver limits/hash pins. Its reproducible output records
source/artifact hashes and unchanged caps in `pins.json` and `source-audit.json`.

## Generated-only validation

`tools/generate_fixtures.py` creates the only guest classfiles used here. They exercise
raw71/raw72/raw73 admission, exact 513,384/over-boundary 513,385 aggregate bytes, and a
generated 819-iteration loop. Class padding is opaque generated class-attribute data;
no original class/JAR, host Java execution, or Minecraft code is used.

The archived run `results/gate-20261020T120340Z/` records:

- Raw71 controls and raw72 positives at q1/q7/q4096, with fresh-process reopen checks.
- Direct raw72 engine execution and an exact 72-class/513,384-byte engine positive.
- Coordinator raw73 refusal (`MR0Error(2)`) and 513,384-byte positive versus 513,385-byte
  atomic `MR0Error(12)` refusal; engine raw73/513,385 typed `LinkError(1, detail)` refusals.
- Typed atomic engine refusals for q65537, zero JVM/internal budgets, and internal budget
  4097; the Go driver's ordinary raw73 guard refuses before creating a world.
- q4096 versus q65536 execution of the generated loop. q65536 completes **4,101 JVM
  instructions in one slice** (under the 30-second watchdog and 1B gas); q4096 completes
  in 4,096 + 5 instructions. Final machine roots, VFS roots, results/counters, and opaque
  MR01 checkpoint payloads match.
- Nine successful public coordinator receipts independently re-encoded and checked for
  nested ABI, checkpoint hash, event, counter-chain, and exact class-read ranges. Archived
  checkpoint blobs permit repeating the verifier without retaining LevelDB worlds.

The ordinary generated gate completed in 40.755 seconds. Its observer explicitly reports
that this is not full Session acceptance. It does **not** validate untouched/original
72-class inputs, general Java compatibility, Minecraft startup, EULA, world generation,
or `Done`.

## Reproduction

Run from the repository root with the already-installed offline toolchain and pinned
`jvmevm/runtime/node_modules`:

```sh
python3 evidence/java-evm/minecraft-entry/raw72-q65536/tools/generate_fixtures.py \
  build/java-diff-mc-raw72-q65536-fixtures-repro1
python3 evidence/java-evm/minecraft-entry/raw72-q65536/tools/build.py \
  build/java-diff-mc-raw72-q65536-build-repro1
python3 evidence/java-evm/minecraft-entry/raw72-q65536/tools/gate.py \
  build/java-diff-mc-raw72-q65536-build-repro1 \
  build/java-diff-mc-raw72-q65536-fixtures-repro1 \
  build/java-diff-mc-raw72-q65536-gate-repro1
```

All generated ordinary-gas cases share a 1,200-second total gate deadline; each owned EVM
call retains its 30-second watchdog. The archive is tamper-evident and independently
rechecked with:

```sh
(cd evidence/java-evm/minecraft-entry/raw72-q65536/results/gate-20261020T120340Z \
  && sha256sum -c SHA256SUMS)
NODE_PATH="$PWD/jvmevm/runtime/node_modules" node \
  evidence/java-evm/minecraft-entry/raw72-q65536/tools/verify_receipts.js \
  "$PWD/evidence/java-evm/minecraft-entry/raw72-q65536/results/gate-20261020T120340Z" \
  "$PWD/evidence/java-evm/minecraft-entry/raw72-q65536/results/gate-20261020T120340Z/worlds" \
  1 raw71-q1 raw71-q7 raw71-q4096 raw72-q1 raw72-q7 raw72-q4096 \
  quantum-loop-q4096 quantum-loop-q65536
```

No remote push was performed or authorized by this stage.
