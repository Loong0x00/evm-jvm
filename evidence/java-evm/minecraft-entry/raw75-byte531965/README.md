# P27 raw75 / 531965-byte LOCAL envelope candidate

This isolated stage starts from the exact accepted P27 raw74/518516 engine and
coordinator in `../parent-raw74-byte518516/artifacts`. It makes only the measured
raw-resource envelope amendment. All guest classes used in the gate are generated
Java-8 fixtures; no original JAR, original class/resource, prior world, or prior
checkpoint was read.

## Frozen change set

- Engine: `MAX_RAW_CLASSES` 74→75, `MAX_RAW_BYTES` 518516→531965, and the two
  matching `_configRoot` leaves only. The P27 label and all 97 bootstrap images
  and ordered leaves are unchanged; root remains
  `70b6401e629c75ad213efb8b6bf484cb3f364dc9a281031c4651069bd3776ec4`.
- Coordinator: four fixed class arrays and the count guard 74→75; per-class and
  aggregate-byte guards 518516→531965; engine runtime-codehash pin updated to
  this compiled engine. Compiler storage-layout comparison verifies only the
  expected fixed-array growth and consequent later-slot shifts.
- Observer: ordinary raw bound 74→75, raw76 guards, and MR01 diagnostic bound
  171→172. No new bootstrap class or API is introduced.
- All other limits remain fixed: q65536, internal/transfer/CP4096, per-class
  262144, arrays/objects4096, handles8449, heap4k, checkpoint1MiB, reserve25M,
  30s watchdog, 128 frames and Java handlers. Engine runtime is 392091 bytes,
  below the explicit LOCAL cap393216. This is not standard-chain compatibility.

## Generated-only gate

Durable evidence is in `results/generated-gate-p27-v1/` with `SHA256SUMS`, exact
source/artifact hashes, ABI/storage-layout output, fixture hashes and independently
reverified public receipt/checkpoint chains. The ordinary-1B gate completed in
58.68s and reverified 18 coordinator receipts across 17 chains.

- Raw71–75 each completed and reopened at q1/q7/q4096. Raw75 checkpoints contain
  172 classes (75 raw + 97 bootstrap); all finished lifecycle2 with result0.
- Direct raw75 engine execution and the exact 531965-byte engine and coordinator
  boundary positives passed. Both 531966-byte witnesses refuse atomically.
- Raw76 is refused at the generated driver, coordinator constructor (MR0Error2),
  and engine (LinkError1/detail76), without a checkpoint product.
- Retained q4096/q65536 loop equivalence: both execute 4101 JVM instructions;
  terminal MR01 payload and machine root match. q65536 commits 4101 instructions
  in one <=30s slice. Invalid zero/over-limit JVM and internal budgets remain
  typed atomic refusals.
- Engine ABI and storage layout match P27; coordinator ABI matches P27 and its
  compiled layout is checked against the exact fixed-array growth. Engine runtime
  SHA-256: `254a73a077c6e37a02be27b141704e9feb63354af4455ce812077e5cf949fa91`;
  runtime Keccak: `311ca8f850fbb54657b621f39f55dc4eab108692025262dea6b1329890faaab1`.
  Coordinator runtime Keccak: `7f38a29af87a1715c032164d30fc3942c8b4e903782c8df52bf708e8014a551c`.
  Coordinator layout SHA-256 (canonical JSON):
  `0981f4f7824d2bfb6ebfed1b308365e5cbae4ac69f8431819fb2f3db0501dcd6`.

This only demonstrates the bounded LOCAL raw-resource envelope with generated
fixtures. It does **not** prove the original75 binding, full Session acceptance,
Minecraft readiness, EULA acceptance, world creation, or a genuine `Done`. The
parent independently handles the unchanged original75 replay and the next measured
class dependency; no `Lists` or other Guava API was added here.

## Reproduction

Run from the repository root. Select fresh, append-only build paths under ignored
`build/`; the scripts enforce offline local solc0.8.30/js-sha3 and do not install
packages or access the network.

```sh
python3 evidence/java-evm/minecraft-entry/raw75-byte531965/tools/build.py \
  build/java-diff-mc-raw75-byte531965-build-TAG
python3 evidence/java-evm/minecraft-entry/raw75-byte531965/tools/generate_fixtures.py \
  build/java-diff-mc-raw75-byte531965-fixtures-TAG
python3 evidence/java-evm/minecraft-entry/raw75-byte531965/tools/gate.py \
  build/java-diff-mc-raw75-byte531965-build-TAG \
  build/java-diff-mc-raw75-byte531965-fixtures-TAG \
  build/java-diff-mc-raw75-byte531965-gate-TAG
python3 evidence/java-evm/minecraft-entry/raw75-byte531965/tools/archive.py \
  build/java-diff-mc-raw75-byte531965-build-TAG \
  build/java-diff-mc-raw75-byte531965-fixtures-TAG \
  build/java-diff-mc-raw75-byte531965-gate-TAG \
  evidence/java-evm/minecraft-entry/raw75-byte531965/results/generated-gate-TAG
```

`javac --release 8` only generates fixtures; no guest fixture is run on the host
JVM. Generated class ZIPs and LevelDB worlds are disposable gate outputs and are
not archived. Their source inputs, hashes, public receipts and opaque checkpoint
blobs are durably recorded under `results/`.
