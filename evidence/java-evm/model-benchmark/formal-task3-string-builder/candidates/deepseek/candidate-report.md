# BENCHMARK_RESULT — formal task 3/3: bounded `java/lang/StringBuilder`

## Result

**Over cap / blocked (not accepted).** The single required build attempt compiled the
proposed 85-image engine and measured **395316/393216 runtime bytes (2100 over the
cap)**; `engine/build.js` refused to publish the artifact. No generated gate was run,
so no q1/q7/direct/reopen/canonical receipt, no engine/coordinator/driver pin and no
runtime size claim are made.

Every other source and evidence artifact required for the attempt is present,
reviewed and committed:

- strict parent-pinned reverse verifier passed before the build (84 prior image bytes
  byte-identical, exactly one append-only StringBuilder image, fixed limits intact,
  Java-8 recompilation byte-identical);
- Java-8 provenance: genuine `/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8
  -g:none` image, 538 bytes,
  `sha256 5439ccde8ea934cfc22d7061d0e102d6f1efe0d94241ee2e9c5f6386dca91f63`;
- generated-only fixture set for the positive/negative controls (see below);
- generated-only gate with q1/q7/direct(q4096)/reopen/canonical probes and retained
  System.err/failed-init/raw30/31/262144/262145/EnumSet/ACC_ENUM/queue/OOM controls.

The measured overage is larger than the 538-byte image plus the explicit hooks and is
consistent with the known Solidity `viaIR` layout sensitivity of this 392 KB runtime
(the parent's System.err feature was `-430` bytes for a smaller source delta). A repair
needs a measured saving of at least 2100 bytes that preserves runtime-derived
limit/bootstrap commitments (no precomputed `DLIMITS`/`DBOOT_PRINTSTREAM` regression)
and weakens no prior check; no such measured repair was completed inside this attempt.

## Files Changed

Source commit (`java-evm: stage bounded StringBuilder bootstrap`):

- `evidence/java-evm/minecraft-entry/string-builder-preflight/bootstrap/java/lang/StringBuilder.java`
  — bounded Java-8 guest source: default `<init>()V`, same-object chained
  `append(String)` with ordered char accumulation, `toString()` allocating a fresh
  `String` copy (`new String(value)`). Uses only engine-supported guest bytecode
  (`new char[]`, `caload/castore`, `String.length/charAt`, pinned `String([C)V`).
- `.../bootstrap/java/lang/StringBuilder.class.hex`, `.../bootstrap/pins.json` — the
  exact 538-byte image and reproduction/hash pins.
- `.../engine/MCEntryInterpreter.sol` — accepted parent engine plus only: new domain
  `MC-STR-BUILDER-PRN1`; `h` 84→85 with `h[84] = keccak256(_bootstrapStringBuilder())`;
  `count +78 → +79`; `classes[classSlot + 45]`; reserved
  `java/lang/StringBuilder`; one appended `_bootstrapStringBuilder()` image.
  All 84 prior image literals, amended System/PrintStream, runtime-derived
  `uint32[11]` limits commitment, raw30/262144 and every other bound are untouched.
- `.../coordinator/MCEntryCoordinator.sol` — parent template + domain/address rename
  only; engine codehash rebound at build time.
- `.../tools/` — `verify_source.py` (strict parent-pinned reverse verification),
  `build.py` (one pinned solc 0.8.30 runs200 viaIR Cancun metadata-off build),
  `generate_fixtures.py`, `gate.py`, `checkpoint_diagnostic.py`, `verify_receipts.js`,
  `Go.txt` (parent driver template + domain/address rename).
- `.../parent-input.json` — sha256 of the four accepted parent inputs.

Evidence commit (`java-evm: archive StringBuilder build-cap failure`):

- `.../artifacts/source-verification.log` — the strict reverse verification receipt.
- `.../artifacts/engine-build.log` — the single build attempt: source verified,
  `Contract code size is 395316 bytes`, `runtime >384KiB` refusal.
- `.../artifacts/build-failure.json` — machine-readable failure record.

Untracked, ignored `build/` intermediates (fixtures, build sandbox) are not committed.

## Verification

Performed:

- `python3 .../tools/verify_source.py` — passed: parent file sha256 pins; parent image
  literals byte-identical for all 84 prior images; `_bootstrapStringBuilder` present
  exactly once; Java-8 recompilation of the staged source equals the embedded image
  hex/sha; `limitsCommitment d97049f6…` recomputed; raw30/262144, frames128,
  checkpoint1MiB, 12 native bindings, 14 exception kinds intact; coordinator/driver
  deltas are domain/address only.
- one pinned engine build: **failed the required `runtime <= 393216` bound** at
  395316 bytes; per the task rule ("build/gate each at most once; stop rather than
  broaden") no second build and no gate were run.

Not performed (and therefore not claimed): runtime artifact pins, coordinator/driver
rebuild, q1/q7/direct(q4096)/reopen positives, null bound, uninitialized/replacement/OOM
negatives, retained System.err/failed-init/raw30/31/262144/262145/EnumSet/ACC_ENUM/
queue/OOM controls, canonical receipt verification, original30 (parent-only).

## Remaining Uncertainty

- Whether a compact size repair exists that recovers ≥2100 bytes without weakening
  checks or regressing the accepted runtime-derived commitments; the measured
  `viaIR` layout response makes source-only prediction unreliable.
- The staged null bound is an explicit `NullPointerException` before mutation, not
  Java-8 `"null"` append; the `string-builder-null` fixture asserts NPE plus
  content-unchanged and deliberately has no host Java-8 oracle (host Java 8 appends
  `"null"`). This is a declared bound, not a passed gate.
- The `string-builder-oom` fixture (element-quota exhaustion through append) is
  generated but unexecuted; its engine-side outcome is unverified.
- No claim is made for capacity/primitive/Object `append` overloads,
  `AbstractStringBuilder`, `Serializable`, PrintStream output/println, Minecraft,
  EULA, world generation or Done.
