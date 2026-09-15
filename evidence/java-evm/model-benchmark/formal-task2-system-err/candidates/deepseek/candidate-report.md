# BENCHMARK_RESULT — bounded `java/lang/System.err` bootstrap (deepseek candidate)

## Result

IMPLEMENTED AND VERIFIED for the measured frontier. The candidate engine
(`evidence/java-evm/minecraft-entry/system-err-preflight-deepseek/`) replaces only
the `java/lang/System` image at slot44 (adding `public static final PrintStream err`
and genuine `<clinit>` construction) and appends one immutable Java-8
`java/io/PrintStream` image at slot83 (bootstrap count 83 -> 84). Engine runtime is
**392774 bytes** (<= 393216; the accepted parent is 393205), coordinator 4146 bytes,
raw30/262144, CP4096, Code65535, frames128, checkpoint1MiB, Head32768B, LOCAL1B gas
with 25M reserve, 12 native bindings, 14 exception kinds all unchanged. No
print/println/output behavior is claimed.

## Files Changed

* `evidence/java-evm/minecraft-entry/system-err-preflight-deepseek/`
  * `engine/MCEntryInterpreter.sol` — staged candidate source (exact parent+delta, SHA256 pinned by `verify_source.py`)
  * `coordinator/MCEntryCoordinator.sol`, `tools/Go.txt` — mechanically re-pinned domain/address/owner/engine codehash only
  * `bootstrap/java/lang/System.java|.class.hex`, `bootstrap/java/io/PrintStream.java|.class.hex` — JDK8 `-g:none` images
  * `tools/verify_source.py` — strict reverse verifier pinned to `parent-de60a3245`
  * `tools/build.py` — one-shot staging/build of engine pins, coordinator and generated driver
  * `artifacts/` — engine/coordinator artifacts, `pins.json`, generated world heads, refusal receipts, `summary.json`
* `BENCHMARK_RESULT.md` (this file; copy retained under the preflight directory)

## Verification

Strict reverse verifier (passes, pinned to parent-de60a3245 input hashes):
82 prior images byte-identical in order; only `_bootstrapSystem` differs (slot44);
`_bootstrapPrintStream` appended (slot83); both images equal JDK-8 `javac
-source 8 -target 8 -g:none` output against a stripped rt.jar (major version 52);
engine source equals the mechanical parent+delta reconstruction; coordinator/driver
deltas are exactly the documented pin substitutions; fixed limits unchanged.

Generated-only EVM worlds (no original JAR/class/resource/world):
positive `ErrMain`+`Probe` bundle reads `System.err`, requires non-null, stable
identity across reads and through a PrintStream-typed constructor handoff, and sets
`state=7` only after all checks; q1/q7/direct + fresh-process reopen all complete
lifecycle=2 outcome=2 result=0 with identical machineRoot
`0x456dcb30...` (quantum invariant, 127 JVM/6 internal steps).
Checkpoint decode: 86 classes; System state=2 with `err=KIND_REF payload10`,
`properties=KIND_REF payload3`; mid-initialization checkpoints show System state=1
with `err` a typed null reference (no preinitialized/fabricated handle);
PrintStream image state=2.
Replacement negatives: raw `java/lang/System` and raw `java/io/PrintStream` bundles
are atomically refused with `BootstrapProfileError(1,0)` selector `0x6a23ad80`,
root unchanged.

## Remaining Uncertainty

* Raw31 driver/coordinator/engine atomic refusals, the 262144/262145 byte
  boundaries and canonical nested receipt re-encoding (148 receipts over the three
  err worlds plus raw30) were verified after the first commit and are recorded in
  the preflight `artifacts/` and `summary.json`.
* Retained Enum/ACC_ENUM + EnumSet (541 JVM steps, result 0, matching the accepted
  parent's 541-step positive) and ConcurrentLinkedQueue (109 steps, result 0) were
  re-executed and pass; their images are byte-identical to the accepted parent.
* An OOM-quota re-execution was not run before the harness wall clock ended; the
  unchanged images and the failed-initialization/checkpoint evidence make no
  behavior change expected. No original30 claim is made.
* A stale orphaned run from an earlier invalidated pilot remained active in this
  worktree during this session and wrote under
  `evidence/java-evm/minecraft-entry/system-err-preflight/` (a different directory);
  this deliverable is self-contained under `system-err-preflight-deepseek/` and was
  committed separately.
* `PrintStream` is a bounded construction-only subset (no output methods, no
  supertype hierarchy beyond Object); unmodeled API fails explicitly.
