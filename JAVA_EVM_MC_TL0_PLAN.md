# MC-TL0: fresh Throwable identity on genuine LOCAL continuation

Status: **FROZEN implementation contract**, after accepted LC0 `8a65662` and parent
review of preflights integrated at `6bea348`/`3faf512`. This authorizes the disjoint
work sets below, not acceptance, Minecraft execution, EULA acceptance or a listener.

## Goal, base and parent correction

Add one guest capability: ordinary construction of linked Throwable classes,
identity-preserving throw/catch/rethrow, initializer wrapping with retained cause,
and an uncaught dynamic-class outcome. No new Throwable methods, String constructors,
Java I/O, VFS, main, scheduler, resources, stack traces or full-Java-SE claim.

Fork accepted LC0 into a **separate** runtime/package. Base source SHA256:
`f0739b6dedbf3b6f7676c06459b89d12a7b8a90dde297967c32dce0af9655dac`;
runtime206163B SHA256 `a1820864d8e846be4de8211158778150fdfde0e41e443aa66c44ec17f487e6cd`.
Preserve accepted LC0, LB0, all27 bootstrap images and stock files byte-for-byte.
Preserve the durable-transport fixes through `f866ba5`; do not start from an earlier
worker transport with publication leakage or source-relative artifact loading.

`JAVA_EVM_MC_LC0_PLAN.md` is normative for unchanged semantics, quotas, input ABI,
head, step accounting, provenance, flat codec, validator, persistence and failures.
The precise TL0 differences are specified here. This plan overrides incompatible
recommendations in the Throwable preflight.

Parent replay matched all four Throwable one-call measurements and all eleven
String prototype chain rows. These prototypes remain unaccepted and are not the
production base. Parent additionally verified Java8/21 and one-call EVM results
101/102/103/201 for direct constructor `throw this`, a callee throwing the constructor
receiver, a saved receiver thrown after its constructor fails, and constructor
self-throw escaping `<clinit>`. Java8/21 also prove the last EIIE cause is that exact
receiver. The prototype does **not** retain/expose this cause or prove TL0 resume.

**Critical correction:** after a successful super-constructor, `this` can legally
be used as an initialized reference before the enclosing constructor returns. A
caller may still retain UNINIT duplicates of the same handle. Do not reject a
pending Throwable merely because it is an active constructor receiver or has an
UNINIT alias elsewhere. Abrupt construction poisons the uninitialized aliases, not
already-legal initialized references that escaped after super. Keep LC0's exact
constructor phase/link rules; do not invent a global "constructor returned" test.

## Guest semantics

1. Permit ordinary `new` of any supplied accessible concrete class assignable to
   canonical Throwable, including exact canonical exceptions. Existing resolution,
   class initialization, abstract/interface/access/descriptor errors precede
   allocation as in LC0. Failed class initialization allocates no requested object.
2. Every explicit allocation consumes ordinary object/field quota and one shared
   heap handle; normal constructor frames execute genuine guest/bootstrapped Code.
   Failed constructors leave no-GC allocations charged. Explicit canonical
   exceptions do NOT consume the implicit exception arena.
3. Preserve the12 implicit fault kinds,256-record arena and emergency OOM. Faults
   and initializer wrappers still use that arena and remain possible when ordinary
   quota is full. There is no second heap or host-created object/reference.
4. `athrow` must consume an initialized REF to a dynamically assignable Throwable,
   preserve its identity and allocate nothing. Null raises NPE6. Illegal tags,
   uninitialized operands, arrays and non-Throwable objects retain hard reference/
   bytecode failures. Matching/unwind uses dynamic class, not origin/kind metadata.
5. Classify kind1..12 only for an EXACT canonical kind class. Every other Throwable,
   including a subclass of a known kind or canonical Exception/RuntimeException/
   Error, is kind0. Exact known ordinary instances and implicit instances share an
   outcome kind but retain distinct allocation origin and identity.
6. Before initialization/allocation, reject a user hierarchy whose actual virtual
   dispatch overrides `fillInStackTrace:()Ljava/lang/Throwable;` with
   `ThrowableProfileError(1,classIndex,methodIndex)` identifying the overriding
   declaration. The zero-field Throwable profile cannot honestly execute that
   callback. Include covariant bridges/inherited overrides. A different descriptor
   or method that is not a virtual override is not by itself a reason to reject.
   Do not silently skip user callback Code. All existing27 bootstrap images stay
   unchanged; only their existing no-argument constructor chains are available.
7. User-defined constructor descriptors/bodies remain ordinary supported Code.
   Absent message/cause/other bootstrap constructors and APIs retain exact existing
   link/call failures; do not discard arguments or supply null/empty/no-op methods.
8. Non-Error Throwable escaping `<clinit>` becomes a fresh arena EIIE3, with its
   exact original ref retained as cause. Error subclasses propagate unwrapped.
   Mark failure and later raise NCDFE12 as LC0/Java8 requires. Emergency OOM instead
   of a failed wrapper allocation creates no fictitious cause record. No Java21
   NCDFE cause behavior is claimed. Ordinary explicit EIIE has no synthetic cause.

## Versioned runtime/ABI

Contract/file: `Throwable0Interpreter` in `runtime/local/tl0/`. No legacy pure
entrypoints, constructor arguments, import, upgrade, setters or migration APIs.

Keep LC0 `start`, `resume`, `head`, `validateCheckpoint` argument signatures exactly,
including budgets and `(I...)I` root inputs. `head` and CheckpointCommitted event
retain LC0 fields/order. Control/state error names `LC0ControlError` (codes1..8)
and `LC0StateError` (codes1..7 and absolute/global offsets) remain unchanged; add
only `ThrowableProfileError(uint256,uint256,uint256)` above. Other inherited guest
profile/link errors retain their contracts. No EVM OOG becomes a Java outcome.

`start`/`resume` return `(ThrowableSliceResult,bytes checkpoint)`:

```solidity
struct ThrowableSliceResult {
  uint32 schema; uint8 lifecycle; uint64 epoch;
  bytes32 checkpointRoot; bytes32 machineStateRoot;
  uint64 totalJvmSteps; uint64 totalInternalSteps;
  uint64 executedJvmSteps; uint32 executedInternalSteps;
  int32 result; uint8 javaKind; uint32 javaRef; bytes javaClass;
}
```

Lifecycle0absent/1RUNNABLE/2RETURNED/3UNCAUGHT_JAVA are unchanged. RUNNABLE has
result/kind/ref zero and empty javaClass, even when the machine has a pending fault.
RETURNED has its int result and zero kind/ref/empty class. UNCAUGHT has result0 and
nonzero ref; exact known class gives kind1..12 and EMPTY class; other Throwable gives
kind0 and exact EVM-derived classfile internal-name bytes (1..65535). Terminal frames
are empty; exact pending ref/kind and heap/statics/counters remain retained.

Class bytes come from EVM metadata, not from host class lookup, normalization,
MUTF8 conversion or nearest-superclass guessing. Go checks bounded canonical outer
ABI/outcome shape only and transports `JavaClass []byte` opaquely. Rendering may use
hex/base64 or byte-escaped text. This is not a guest String or a message/stack trace.

## TLS1 codec/commitments

Schema1 in the NEW TL0 namespace. Domains are
`JVMEVM:MC:TL0:{ARTIFACT,BOOTSTRAP,CONFIG,MACHINE}:1`.
Envelope magic `JVMTL001`; machine magic `TLS1`. LC0216-byte header widths/order and
commitment formulas are otherwise unchanged, substituting TL0 domains/magic and
binding the exact same ordered27 bootstrap image hashes and new runtime hash.

Reject LC0 blobs in TL0 and TL0 blobs in LC0. Existing instances continue only on
their accepted artifact. No host conversion, source checkpoint import or cross-
profile reissuance. An independently validated blob still is not a live head.

TLS1 is LC0's flat stream with these differences ONLY:

* Terminal prelude and Pending may carry kind0 with nonzero Throwable ref. Known
  kinds match exact dynamic class, independently of ordinary/arena origin. Inactive
  Pending remains allzero. Apply the constructor correction above; do not prohibit
  legitimate REF/UNINIT coexistence or saved initialized receivers after failure.
* After Pending and before ordered intern records, encode
  `wrapperCauseCount:u16`, then sorted `{wrapperRef:u32,causeRef:u32}` records.
  There is exactly one record for every **arena-origin** EIIE3 object; none for
  ordinary explicit EIIE or any other object. Count<=256. Wrapper refs strictly
  increase, `0<causeRef<wrapperRef`; cause is a valid non-Error Throwable and uses
  the authoritative heap. Missing/duplicate/wrong-type/unordered records fail
  state error7. No new Java quota is charged for this VM bookkeeping relation.

Reparse/rederive all caches in EVM, including Throwable class classification.
Validate full state, reference/tag/layout/initialization/frame/cause/intern bounds;
canonical re-encode equality remains required. Never mutate state or fabricate a
cause during validation. Child validation/encoding precedes successful-only head
publication/event. Pending operations resume before another opcode, with LC0 units.
The cause list adds bytes to the1MiB cap; do not quietly change that limit.

## Go transport/artifacts

New package `jvmevm/localcontinuation/tl0`; public API names/signatures are LC0's
`Runtime`, `RuntimeHash`, `ABI`, `NewMemory`, `Open`, Session `Start`, `Resume`, `Head`,
`ReadCheckpoint`, `Close`. `Result` retains Slice/Checkpoint/GasUsed/RevertData/Logs;
its `SliceResult` adds `JavaClass []byte` corresponding exactly to the new tuple.
Use embedded generated `artifacts/Throwable0Interpreter.json` via package
`jvmevm/runtime/local/tl0` (`tl0assets.Artifact()` returns a defensive byte copy).
Generate/check separate `.runtime.hex`, `.abi.json` and combined provenance JSON.
Pinned solc0.8.30 exact compiler guard, optimizer200/viaIR/Cancun/metadataoff.

LOCAL contract address: `0x004a564d45564d544c3052554e54494d4500000001`.
Store marker: `JVMEVM-MC-TL0-DISK-STORE-1\n`; format1. Keep LC0's fixed all-dev-chain
execution context, manifest field layout and owned filenames. Runtime code hash,
marker, address and TL0 ABI prevent treating an LC0 store as TL0. No silent reset.

Copy the accepted durability behavior: resolve an explicitly requested root alias;
check metadata and fixed entry types before opening LevelDB; bound regular-file
reads; preserve/ignore only owned unpublished manifest temporaries; sync both new
and existing opaque blobs before trie/head publication. Old-root recovery and
ambiguous-publication poison/reopen semantics, failure-result gas-only behavior,
code-not-reinstalled checks and real new-process tests remain mandatory. No guest
machine/class/heap parser or Java evaluation in production Go. No core/state changes.

## Exact core fixtures/gates

24 ordinary roots in five fixture groups; each root's raw bundle<=4classes/64KiB.
Hygienic ordinary Java source, Java8 classfiles, Java8primary/21secondary oracle.
Oracle helpers may inspect exception class/cause OUTSIDE the unchanged guest roots.
Do not put fixture names/expected results/PCs into production Solidity or Go.

| Group | Roots (expected int, or uncaught outcome) |
|---|---|
| TL0Construction (6) | exactException=1; exactArithmetic=1; customFields(17)=17; hierarchyFields=37; distinct=1; ctorEffects=11 |
| TL0Identity (6) | localCatch=1; fieldCatch=1; arrayCatch=1; callUnwind=1; rethrow=1; knownSubclassCatch=1 |
| TL0Initialization (5) | failingConstructor=7; initBeforeNew=3; wrapsNonError=1; propagatesCustomError=1; secondUse=3 |
| TL0Outcome (3) | exactKnown:kind1/emptyclass; custom:kind0/TL0Outcome$Problem; subclassKnown:kind0/TL0Outcome$KnownChild |
| TL0ConstructorSelf (4) | direct=101; throughCall=102; escapedAfterFailure=103; inClassInit=201 |

Values must arise from constructor/field/identity/handler effects, not constant-only
roots. Construction group uses <=3 nested classes; other groups may compile more
nested classes but each selected raw bundle is explicit and bounded. Record exact
source/class hashes, selected bundle, entry, args and oracle outcome in manifest.

Run24 one-call4096 controls. Run q1 AND q7 for these10 roots: customFields,
callUnwind, rethrow, initBeforeNew, wrapsNonError, propagatesCustomError and allfour
ConstructorSelf roots (20actual chains). Snapshot before/after new, super return,
constructor field writes, pending throw and wrapping; terminal machine roots,
values/outcomes and total counters match the one-call control. Retain exact cause
identity in EVM-produced snapshots, including constructor-self `<clinit>` wrapping.
Also replay the three accepted LC0 fixture bytes on TL0 with one/q1/q7/internal1;
compare outcomes/counters, NOT roots across different runtime/config namespaces.

Independent32 core probes:8 allocation/arena/field/checkpoint/quota boundaries;
8 tag/constructor/fill-override/profile cases;10 pending/outcome/cause canonical
stream cases;6 stale-head/OOG/rollback/retry/new-process cases. Include ordinary
known-kind origin vs implicit origin; explicit EIIE with no cause; exact1MiB and
plus-one size; full ordinary quota with still-available implicit faults; wrapper
OOM; cross-namespace blob/store refusal and no speculative publication output.
Parent may retain additional probes separately; do not remove old negative tests
that remain valid on accepted LC0/LB0, or count worker completion as acceptance.

LOCAL runtime<=256KiB; checkpoint<=1MiB; percall1..4096JVM/internal units;
100M/30s ordinary and1B/120s dedicated boundaries;25Mcommitreserve unchanged.
Ordinary test cases<=4096dispatchunits/256slices. **New TL0 quota cases only** may
use<=65536dispatchunits/256slices, to genuinely fill1024objects through constructor
chains. This is an explicit new LOCAL test allowance, not a change to LC0 or stock
gates or VM opcode accounting. Whole TL0gate20min/4GiBRSS external watchdog.

Final parent gates: newTL0, unchanged LC0/LB0/2231/smoke/fast/bootstrap/Python/
artifacts/Go/CLI/allstock/demos/AOT/focusedvet. Preserve reproducible artifacts,
exact errors, failure reproducers and last-green commits. No startup-cost promise.

## Authorized disjoint work sets

* Runtime worker: ONLY `jvmevm/runtime/local/tl0/**`, including source/build/assets.
  One production Solidity writer, generic dispatcher and actual continuation.
* Harness worker: ONLY `jvmevm/localcontinuation/tl0/{tl0.go,session.go,session_test.go,README.md}`
  and `jvmevm/testdata/local/tl0/**`. Opaque durable transport and24fixture manifest.
* Verifier worker: ONLY `jvmevm/localcontinuation/tl0/validation_test.go`; independent
  test fixtures may live under its ignored build directory. No production edits.
* Parent: plan/Make/guide/integration, independent probes and final acceptance.

All workers Sol/high, no Fast/priority, spawn/push/peer writes or global settings.
Missing artifacts fail or block, never count as skipped acceptance. Surface genuine
ABI/gas/quota/provenance blockers rather than weakening the frozen contract.
