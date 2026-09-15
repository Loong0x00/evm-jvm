# RECOVERY_RESULT — auxiliary recovery of the cap-failed StringBuilder bootstrap

## Result

**The size repair is complete and the single authorized recovery build fits.**
The failed formal task 3 candidate compiled to **395316 / 393216 runtime bytes**
(2100 over cap, see `BENCHMARK_RESULT.md`). The recovery is a strictly
semantics-preserving source-layout repair that materializes every bootstrap
image exactly once, and it measures **350499 bytes** — a 44817-byte reduction
from the failed candidate and 42717 bytes below the 384 KiB cap.

The repair keeps the pinned toolchain exactly (solc 0.8.30, optimizer runs 200,
viaIR, Cancun, metadata off), all 84 prior image bytes and their order, the
appended 538-byte Java-8 StringBuilder image, every fixed limit, all eight
domain constants, the failed candidate's count/reservation edits, and the
runtime derivation of the bootstrap and limits commitments. No image hash is
precomputed (the accepted parent's single precomputed EnumSet hash is removed:
all 85 commitments are now derived from the materialized bytes at run time).

The generated gate was attempted twice and **stopped honestly**, not on the
engine: the first invocation aborted on an invalid precondition in the stage's
previously unexecuted gate script (fixed, tool-only), and the second progressed
through every system-err and StringBuilder positive/negative world and then hit
the generated `string-builder-oom` fixture, which cannot produce a committed
terminal under the frozen caps and never actually crosses the element quota it
targets. No limit, fixture or engine byte was changed to force it green; no
third gate run was made.

## What the failure actually was

The accepted `parent-89928ece8` engine materializes every bootstrap image twice:
`_bootstrapRoot()` calls each `_bootstrap<X>()` once to derive the root
commitment, and `_prepare()`/the append families call it again to build the
class table. A byte-level scan of the accepted runtime (392775 bytes) shows
**76 of 84 image fingerprints embedded exactly twice**; only the one image whose
hash was precomputed (`EnumSet`) is embedded once. solc's viaIR full inliner
copies the small literal-returning callee into each call site, so appending the
538-byte StringBuilder image cost 2541 runtime bytes instead of ~538.

## The repair

`tools/recovery_transform.py` deterministically maps the accepted parent source
plus the genuine Java-8 StringBuilder image to the recovered source, asserting
every operation. It is not a rewrite: it changes only where each image literal
is materialized and who consumes it.

- `_bootstrapImages()` materializes all 85 images once into `bytes[85]`, in the
  accepted root order (0..81 parent, 82 EnumSet, 83 PrintStream, 84 StringBuilder).
- `_bootstrapRoot(bytes[] memory imgs)` derives `h[i] = keccak256(imgs[i])` in a
  run-time loop and returns `keccak256(abi.encode(DBOOT, h))` unchanged.
- `_configRoot(..., imgs)` and `_prepare(..., imgs)` plus the six append helpers
  consume the shared bytes; every `_bootstrap<X>()` has exactly one call site.
- The four entry paths materialize the set once each, in the original
  root-check-before-parse order, so revert precedence is unchanged.
- `DBOOT_ENUMSET` (the one precomputed image hash) is removed; all 85 hashes and
  the limits `abi.encode` are still derived at run time.

Measured in a scale replica of the planned structure (all 85 real images, four
entry points, pinned compiler settings) before the build: each image is emitted
once, and the old shape costs 178934 bytes versus 52801 for the recovered shape.
This predicted the observed 44.8 KB runtime reduction.

The one authorized build also records an emission histogram: the 76 parent
fingerprints that occurred twice now occur once, 0 regressions, 7 fingerprints
are not representable as contiguous slices in either runtime (measurement
artifact, equal before/after).

## Verification performed

- `tools/verify_source.py` (updated, strict): parent input sha pins, 84 prior
  image bytes byte-identical and in order, StringBuilder image byte-identical
  to the Java-8 recompilation (538 bytes,
  `5439ccde…f63`), domains/lengths, `rawLimits [30,262144]`, frames 128,
  checkpoint 1 MiB, 12 native bindings, 14 exception kinds, 11-entry limits
  commitment `d97049f6…39e`, one call site per image, no `keccak256(_bootstrap`
  anywhere, no `DBOOT_ENUMSET`, every consumer threaded from the shared array,
  coordinator/driver deltas domain/address-only. Passes.
- `tools/analysis_check.py` (precondition, no bytecode requested, not a build):
  solc parse/type analysis with the pinned settings, **0 errors** (45 warnings,
  all pre-existing). It caught and prevented one real argument-order bug in the
  transform before the build attempt.
- The single build (`tools/build.py`, attempt 2): engine
  `350499` bytes, runtime sha256 `b70fcbd8…d704`, keccak `3aeb4314…55df`; init
  sha256 `b21f98a3…a318`; coordinator 4146 bytes as required
  (runtime keccak `bb3e18d8…01d`); Go driver/vet clean.
- Gate evidence (generated-only): ten completed worlds — system-err q1/q7/
  direct, system-uninitialized, string-builder q1/q7/direct (terminal
  lifecycle/outcome 2, result 0, 1507 JVM steps, identical machine root
  `0x08db54eb…0d8c` across quanta), string-builder-null q1/q7/direct (277 steps,
  identical root `0x120b4212…fdab`) — plus the corrected precondition proving
  StringBuilder state 2 and System/PrintStream untouched. Every one of these
  also passed start/finish/reopen process receipts and the diagnostic class
  count.
- `tools/verify_emission.py`: parent-vs-recovery fingerprint histogram
  (`{2:76,1:1,0:7}` → `{1:78,0:7}`), 0 regressions.

## Gate limitation found (pre-existing, not the engine)

`string-builder-oom` targets element-quota exhaustion through `append("x")`, but
its live `char[]` arrays total exactly `63*4096 + 4031 = 262079` elements and
the append needs one more (`262080 <= MAX_ARRAY_ELEMENTS = 262144`), so no
`OutOfMemoryError` is raised at all; the guest would instead throw an uncaught
`Error`. Independently, `_machineSize` encodes heap array elements at 8 bytes
each, so any committed state holding those arrays is ~2.1 MiB against the fixed
1 MiB `MAX_CHECKPOINT_BYTES`; observed at epoch 321 with a 1019351-byte
checkpoint, the next resume reverts `LC0StateError(1,0)` and the root is
unchanged. `_machineSize`, `MAX_ARRAY_ELEMENTS`, `MAX_CHECKPOINT_BYTES`,
`MAX_ARRAYS` and the whole array-allocation path are byte-identical to
`parent-89928ece8`; this is a generated-fixture defect from the failed attempt,
which never executed its gate. Because of it the gate stopped before the
retained raw30/31, 262144/262145, raw-replacement, EnumSet, queue, field-arena
OOM and canonical-receipt sections.

## Files changed

Source commit `06064f4df` (`java-evm: recover StringBuilder cap with single
image materialization`):

- `evidence/java-evm/minecraft-entry/string-builder-preflight/engine/MCEntryInterpreter.sol`
  — recovered engine source, sha256 `2268113e…351f`.
- `.../tools/recovery_transform.py` — deterministic, asserted parent→recovery
  transform (the auditable definition of the repair).
- `.../tools/verify_source.py` — strict reverse verifier updated to the
  single-materialization invariants (all prior pins/checks retained and
  strengthened).
- `.../tools/analysis_check.py` — no-bytecode parse/type precondition.
- `.../tools/verify_emission.py` — per-image fingerprint emission evidence.
- `.../tools/build.py` — runs the above; records emission evidence and the
  recovery transform in the build pins.

Gate-tool fix `7001861f8` (`java-evm: correct invalid StringBuilder gate
precondition`): replaces `assert raw + 83 in states` with the fixture's true
negative invariant. Engines/fixtures untouched.

Build evidence `e4ced00ae` and the gate evidence commit: `recovery-build.json`,
`recovery-build`/`analysis`/`source-verification`/`coordinator` logs,
`recovery-emission-evidence.json`, `recovery-SHA256SUMS`,
`recovery-gate-findings.json`, both gate stdouts and the OOM resume refusal.

## Not claimed / remaining uncertainty

- No complete acceptance gate: the OOM fixture is infeasible under the frozen
  caps and stop was honest; the OOM negative remains unverified.
- No fixture redesign, no fixed-limit change, no third gate run, no push.
- The recovery transform relies on the observed (and replica-verified) fact
  that an 85-statement image builder is not inlined; the measured 350499-byte
  runtime and single-occurrence fingerprints confirm it for this exact source.
- The declared bound that `append(null)` is an explicit NPE before mutation
  (not Java-8 `"null"` append) is unchanged and still a declared bound.
- No Minecraft/EULA/world/Done evidence; no original artifact was read.
