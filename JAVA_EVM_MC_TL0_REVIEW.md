# MC-TL0 acceptance review

Status: **ACCEPTED bounded LOCAL fresh-Throwable continuation**, after parent
integration, corrections and current-artifact reruns through `0f99bd2`.
Authority: frozen `JAVA_EVM_MC_TL0_PLAN.md` (`3173ffb`). No Minecraft, VFS, String
constructor, Throwable method API, stack trace or standard-deployment claim.

## Artifact and preservation

Worker commits `026356e`/`fcd4f2b`/`29e6c33` were integrated as
`0be2a1d`/`7758634`/`6f4ad36`. Their reports/stub compilation were not acceptance.
The first real integrated run exposed a malformed verifier Java fixture and a
missing nested-class read request; parent corrected both without skipping tests.

Accepted contract: `jvmevm/runtime/local/tl0/Throwable0Interpreter.sol`.

* Runtime **212,574 bytes**, SHA256
  `c1a9a48d598e7efb7eaf636222ee596e767a22e5859384acd33e99314acf2084`.
* Source SHA256
  `58315c6ecaa09888cc9c12b996e525137b8489c08950e516873895118cbe48b3`.
* Runtime Keccak/code hash
  `313ca13a04569237ce5596de24e0b212b9e00286b5fc78f37bc96afb4bbf7cf3`.
* Exact solc0.8.30+commit73712a01 compiler guard, optimizer200/viaIR/Cancun,
  metadataoff. Separate runtime/ABI/combined embedded provenance artifacts checked.
* All27 raw bootstrap byte bodies independently compared identical to accepted
  LC0. No accepted LC0/LB0/stock source, runtime or bootstrap changed; upstream
  EVM/state/types/consensus/protocol changes remain absent.

The initial 212059B/`585a8eca...`, intermediate `304bfd2a...` and `6d25f9e3...`
artifacts are historical candidates, not substituted for the accepted hash above.

## Genuine execution evidence

* Exactly24 trusted Java roots:21 integer outcomes and3 uncaught outcomes.
  Java8primary and Java21secondary agree; regenerated24 manifest/class files match.
* 24 actual one-call controls, plus ten selected roots at both q1 and q7
  (**20 linked continuation chains**), match outcomes, counters and terminal
  machine roots. These are not repeated fresh executions stopped at different PCs.
* The four post-super constructor cases return101/102/103/201. Initialized receiver
  aliases remain usable even while caller UNINIT duplicates exist or a constructor
  later fails. EVM-produced snapshots retain exact constructor-self EIIE cause.
* The three unchanged LC0 fixture byte bundles also pass TL0 one/q1/q7/internal1
  execution with results15/36/10 and matching counters. Cross-runtime roots are
  intentionally different, not compared as equal.
* All32 delivered independent probes now execute against the actual integrated EVM
  artifact: allocation/origin/arena/quotas, constructor/profile/tag cases,
  pending/outcome/cause codec, CAS/OOG/retry and real new-process durable reopening.
* Highest24-core one-call cost at the accepted artifact:4,914,924gas; largest core
  terminal checkpoint743bytes. These are fixture measurements, not MC estimates.

The parent additionally retained nine test groups, including36 runs covering all18
concrete canonical Throwable classes (one-call and q1/internal1), the abstract
VirtualMachineError allocation rejection, supplemental-character class-name bytes,
a cause shared by two different initializer wrappers, and large checkpoint retry.
The class-name probe proves raw MUTF8 surrogate bytes remain opaque through Go;
it does not introduce host String/class parsing.

A524935-byte parent survives a failed oversized child and genuinely resumes to an
exact1MiB terminal child. At the accepted artifact, the parent probe measured
384,675,172gas for the retry and328,666,379gas for standalone exact-limit validation
(`/tmp/mc-tl0-parent-final-large.log`). These dedicated calls retain the1B bound. Independent exact-limit/plus-one cases
and arena/ordinary quota separation also pass. No historical budgets were raised.

## Parent findings and corrections

1. `athrow null` raised NPE but left the null operand in the pending snapshot.
   Every REF operand is now consumed, including null. The retained q1 probe checks
   the actual pending frame rather than just its eventual NPE outcome.
2. A malformed raw int-at-athrow program returned BytecodeError(14,1) with a large
   quantum but StateError5 at the preceding checkpoint boundary with q1. Runtime
   boundary checking now retains the guest hard bytecode error; standalone
   restored-state checking still gives StateError5/7. This is not a Java outcome.
3. Envelope machine-root mismatch reported byte176 instead of its actual field
   offset180. TL0 now reports180. Accepted older artifact bytes were not rewritten.
4. A rehashed standalone checkpoint could change a concrete Throwable's dynamic
   class to its abstract superclass and still validate (both had empty layouts and
   completed initialization). Objects now require a concrete, non-interface dynamic
   class in decode/child checks. Abstract superclasses and array component types
   remain legal. Provenance was always separately enforced by the stored head.

The compilation fixture correction is separate from these four runtime findings.
All reproducers remain in `validation_test.go`/`parent_test.go`; no negative tests
were deleted or worker completion counted as parent acceptance.

## Verification record and limits

* `/tmp/mc-tl0-parent-gates.exit=0`: full historical2231/smoke/fast/LB0/LC0/
  bootstrap/Python/artifacts/Go/CLI/allstock/demos/AOT/focusedvet. The initial TL0
  portion used `304bfd2a...`; final-artifact evidence is the later reruns below.
* `/tmp/mc-tl0-parent-latest-tests.log`: complete current TL0 suite passes.
* `/tmp/mc-tl0-parent-latest-reproducibility.log`: final source, runtime, ABI and
  embedded combined provenance reproduce exactly. Current focused TL0/assets vet
  passes. Fixture rebuilding was performed in a separate ignored copy.
* `/tmp/mc-tl0-parent-current-corpus.log`: all24 controls and20 chains at final hash.
* `/tmp/mc-tl0-parent-watchdog.{log,json}`: complete final suite passed under an
  external1200s/4GiB process-group watchdog:17.578s, peak observed RSS276037632bytes.
  This is machine-specific evidence, not a universal performance bound.
* Initial parent findings remain in `/tmp/mc-tl0-parent-{findings,offset-initial,
  abstract-initial}.log`; later successful full runs supersede those failures.

LOCAL explicit oversized code installation and runtime.Call are not ordinary
CREATE or signed-transaction compatibility. Persistence is opaque EVM checkpoint
and trie storage, not a guest filesystem. Physical power-loss simulation and
isolation from a concurrently modifying external filesystem process are not claimed.

No Minecraft server/EULA/listener/real `Done` occurred. Next work remains narrowly
scoped nonliteral String construction, then further message/I/O/platform dependencies;
the String/VFS proposals are not implementation or readiness evidence.
