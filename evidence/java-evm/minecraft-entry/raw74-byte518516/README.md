# P26 raw74 / 518516-byte LOCAL envelope candidate

This isolated stage starts from the exact accepted P26 raw73/516040 sources and
artifacts in `../parent-raw73-byte516040/artifacts`. It changes only the measured
resource envelope needed to admit one additional raw class (`fd.class`, 2,476
bytes in a separate parent EVM resource measurement). The parent owns the real
original74 binding replay; this stage uses generated Java-8 fixtures only.

## Frozen scope

- Engine: raw-class count **73 -> 74**, aggregate bytes **516,040 -> 518,516**;
  exactly the two constants and their two `_configRoot` leaves change.
- Coordinator: four fixed arrays and count guard **73 -> 74**; per-class and
  aggregate byte guards **516,040 -> 518,516**; the engine runtime-codehash pin
  matches this candidate.
- Observer: ordinary raw count **73 -> 74**, MR01 diagnostic class bound
  **170 -> 171**. Generated raw75 must refuse at the driver, coordinator and
  engine layers. Exact 518,516 succeeds; 518,517 refuses.
- P26 labels and all **97 bootstrap leaves/images** are retained; the computed
  root remains
  `9badb7b2e5fd2990b0285dcad078f36955841cc091e7f2eeb07f8401fbfb694d`.
- All unrelated limits remain fixed: q65536, internal/transfer/constant-pool
  4096, per-class 262,144, arrays/objects 4096, handles 8449, checkpoint 1 MiB,
  reserve 25,000,000, 30-second call watchdog, 128 frames and Java handlers.
- Engine runtime is 392,091 bytes, below the selected LOCAL cap 393,216. This
  oversized runtime is not a standard-chain deployment claim.

No historical parent files are edited. No original JAR/classes/resources,
world/checkpoint input, EULA action, original Java/Minecraft execution, or
Minecraft `Done` claim is included.

## Generated-only result

The durable run is `results/generated-gate-p26-v1/` (`SHA256SUMS`, source pins,
fixture manifest and public receipt chains). The ordinary 1,000,000,000-gas
suite completed in 51.45 seconds and independently verified 15 public slice
receipts. Raw71–74 each completed and reopened at q1/q7/q4096; raw74 also passed
a direct engine invocation. Both the engine and coordinator accepted the exact
518,516-byte/74-class witness and atomically refused 518,517. Driver,
coordinator and engine raw75 refusal probes passed. Invalid JVM/internal-budget
controls stayed typed and atomic. The q4096 and q65536 loop runs had identical
terminal MR01 payload, machine/VFS roots, results and counters; q65536 committed
4,101 JVM instructions in one bounded slice.

These checks establish only the local raw-resource envelope and retained
controls. They do not establish the real `fd.class` original binding or
Minecraft startup.

## Reproduction

From the repository root, choose fresh append-only paths beneath `build/`:

```sh
python3 evidence/java-evm/minecraft-entry/raw74-byte518516/tools/build.py \
  build/java-diff-mc-raw74-byte518516-build-TAG
python3 evidence/java-evm/minecraft-entry/raw74-byte518516/tools/generate_fixtures.py \
  build/java-diff-mc-raw74-byte518516-fixtures-TAG
python3 evidence/java-evm/minecraft-entry/raw74-byte518516/tools/gate.py \
  build/java-diff-mc-raw74-byte518516-build-TAG \
  build/java-diff-mc-raw74-byte518516-fixtures-TAG \
  build/java-diff-mc-raw74-byte518516-gate-TAG
python3 evidence/java-evm/minecraft-entry/raw74-byte518516/tools/archive.py \
  build/java-diff-mc-raw74-byte518516-build-TAG \
  build/java-diff-mc-raw74-byte518516-fixtures-TAG \
  build/java-diff-mc-raw74-byte518516-gate-TAG \
  evidence/java-evm/minecraft-entry/raw74-byte518516/results/generated-gate-TAG
```

Build scripts force the worktree's pinned `node_modules`, offline npm mode,
`GOPROXY=off`, `GOSUMDB=off`, and local Go toolchain. They do not install
packages, access the network, spawn geth, or read sibling/original workload
inputs. Host `javac --release 8` is used only to create classfile fixtures; no
generated guest class is run by the host JVM.
