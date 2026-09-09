# MC-LC0 LOCAL continuation feasibility preflight

Status: **bounded preflight only**, based on `f50fe142a7442788179687463d783edaf4dca523`.
This is not an LC0 freeze or acceptance, not a production VM, not standard CREATE
or transaction evidence, and not Minecraft execution. No JAR, EULA, VFS, thread,
listener, peer, core, consensus, gas-accounting, precompile, or global-setting work
was performed.

## Result

A small, generic single-stack LC0 is feasible, but a genuine resume was not small
enough to implement safely in this preflight. The useful measured advance is an
ignored copy of the **current real monolith** which stops at complete opcode
boundaries and successfully returns EVM-issued ABI state containing active frames,
class initialization/statics, the centralized `ExceptionArena` heap and counters,
pending exception data, and MC-LB0 String/intern state. It is not an `SSTORE`
counter surrogate.

The prototype proves extraction and gives a concrete codec-size/gas bound. It does
**not** decode that state back into the interpreter, advance an epoch/head in
storage, or execute q1/q7 as a chain of resumes. Its q1, q7, q10, and q4096 artifacts
have compile-time stop counts and each begins from a fresh Java invocation. Treating
those calls as continuation would be fake progress.

The next freeze should therefore be only a versioned start/resume kernel for one
active Java stack and these small fixtures. It should use one canonical heap,
reparse immutable metadata from EVM-bound class bytes, and add an owner/epoch/head
CAS anchor. VFS, fibers, scheduling, time, main/JAR loading, and Minecraft remain
out of scope.

## 1. Baseline at f50fe14

The checked-in StringLB0 monolith is now:

* source: 334,308 bytes / 6,641 lines, SHA-256
  `15ff4d43fe5ee55f6059c3231c6c96f24e0c60ca5856eacc0024e4a383d99cf7`;
* decoded runtime: **166,334 bytes**, SHA-256
  `ff9c9ff093e9d4885d7546e01db7aacd95cf999d5cf9b6d6b130fd43b791b982`;
* both external entry points remain `pure`; and
* `jvmevm.run` still creates a fresh environment through `runtime.Execute` and
  returns only an `int32` or recognized uncaught Java outcome.

The continuation proposal's older 154,839-byte/M5d-a measurements are therefore no
longer the implementation baseline. Its lifecycle analysis remains correct.

`ExceptionArena` is now the authoritative mutable owner of `HeapRegistry`. Its
`arrayHeap`, `objectHeap`, metadata/kind table, class table, and rank table cover
ordinary arrays/objects, interned Strings, Java exception objects, and the emergency
OOM handle. Local names in `_execute` alias those arena arrays. The arena also owns
allocation counters, exception layouts/counters, pending fault, String layout,
intern handles/hashes, and per-class String-constant references. A decoder must
instantiate this registry once and then bind all local views to it; independently
ABI-decoding an arena heap and local heap copies would be incorrect.

The concrete refactor boundary is `_execute` (currently roughly lines 782--2554):
it allocates every mutable vector as local memory, performs class initialization,
pending-fault unwind, and the large opcode dispatch in one function. There is no
resume-state input. A real implementation must move those locals into one mutable
state carrier, separate initialization from one transition unit, and route every
opcode/helper mutation through that carrier. Recovering a PC or memory image from
an OOG trace is not an alternative.

## 2. What the ignored prototype actually did

The prototype copied the f50fe14 Solidity source only under
`build/java-diff-mc-lc0-preflight/`. Production source/artifact and Go APIs were not
changed. It made these limited changes:

1. `_execute` counts dispatched JVM instructions and, before the next dispatch,
   returns lifecycle `RUNNABLE` when its compile-time q1/q7/q10 limit is reached.
   q4096 reaches the real root return and returns lifecycle `RETURNED`.
2. It ABI-encodes magic/schema, result/step count, EVM-computed artifact/config
   commitments, class init state, `initializerStarted`, statics, **only active
   frames**, and one `ExceptionArena`. Parser, selected-method, hierarchy,
   resolution, handler, and field caches are not copied. The arena's currently
   embedded lazy layout caches are still present and should be removed from the
   minimum accepted codec as re-derivable metadata.
3. The heap appears exactly once, inside the arena. Frame/static/array/String/intern
   aliases remain numeric handles into that heap; references are not recursively
   expanded or host-remapped.
4. The local runner manually installs each oversized q-profile code once in one
   in-memory `StateDB` account and invokes all fixture calls with `runtime.Call`.
   This is still a harness installation, not CREATE. It writes the exact returned
   bytes to ignored files; host parsing is inspection-only and never feeds Java
   execution.

The prototype runtime is 171,993 bytes for q1/q7/q10 and 171,995 bytes for q4096.
It is intentionally over EIP-170 and is LOCAL evidence only. Solc was pinned by the
existing lock to 0.8.30, optimizer runs 200, via-IR, Cancun, no metadata.

The prototype envelope is deliberately not proposed as final schema. In particular,
its config root binds EVM-derived class bytes and root numeric IDs but not all outer
entry-name/argument bytes, it has no epoch/parent/instance/runtime-code fields, and
there is no strict EVM decoder/re-encoder or semantic validator. These omissions are
acceptance blockers, not host responsibilities.

## 3. Trusted fixtures and oracle

All fixtures were compiled with `javac --release 8 -g:none`; Java 8
`1.8.0_504`, Java 21 `21.0.9`, and the unchanged f50fe14 monolith agreed:

| fixture | mechanism | result | unchanged monolith gas |
|---|---|---:|---:|
| `LC0CallLoop.run(5)` | loop plus repeated static call/return | 15 | 777,526 |
| `LC0AliasString.run()` | object/static/reference-array aliases plus one interned String | 36 | 4,861,893 |
| `LC0InitException.run()` | lazy `<clinit>`, divide fault, matching catch | 10 | 1,990,615 |

Class SHA-256 pins are recorded in ignored evidence. These are small trusted test
classes, not fixture-specific runtime metadata.

## 4. Measured extraction

Every call used an explicit finite 1,000,000,000 LOCAL gas cap. `RUNNABLE` is 1 and
`RETURNED` is 2 below.

| q | fixture | lifecycle / actual steps | active depth / top next PC | checkpoint bytes | gas used |
|---:|---|---|---|---:|---:|
| 1 | call/loop | RUNNABLE / 1 | 1 / 1 | 8,544 | 524,715 |
| 1 | heap/String alias | RUNNABLE / 1 | 3 / 2 | 596,480 | 10,500,837 |
| 1 | init/exception | RUNNABLE / 1 | 2 / 0 | 9,184 | 640,413 |
| 7 | call/loop | RUNNABLE / 7 | 1 / 9 | 8,544 | 542,447 |
| 7 | heap/String alias | RUNNABLE / 7 | 2 / 0 | 596,096 | 11,144,470 |
| 7 | init/exception | RUNNABLE / 7 | 3 / 13 | 9,920 | 810,003 |
| 4,096 | call/loop | RETURNED / 74 | 1 / 23 | 8,544 | 861,448 |
| 4,096 | heap/String alias | RETURNED / 105 | 1 / 120 | 595,456 | 12,883,262 |
| 4,096 | init/exception | RETURNED / 18 | 1 / 8 | 306,560 | 4,757,300 |

The largest observed blob was **596,480 bytes** and the largest extraction call was
**12,883,262 gas**, both well below 1 MiB and 100M respectively. Relative to the
unchanged full-run measurements, the q4096 instrumented calls used an additional
83,922 gas (scalar), 8,021,369 gas (String/heap), and 2,766,685 gas
(exception/init). These are whole-artifact deltas, not isolated encoder costs.
Decode, semantic validation, canonical re-encode, hashing, and anchor `SSTORE` remain
unmeasured.

The unexpectedly large String snapshot is explained by the current eager-capacity
heap tables after lazy registry creation: metadata/classes/ranks each had length
2,306. ABI encoding also carries thousands of empty nested array/object slots. It
fits a small-fixture LC0 cap, but it is evidence against making a raw Solidity
memory-struct encoding the long-term format. The accepted codec should emit records
only for handles `1..nextHandle`.

A second identical run produced byte-identical roots and gas rows (the normalized
probe-line SHA-256 was
`e60ca4e79853c684039833b5eeca1a21edfd3080f9a23d81a0a98dde78c177ce`
in both runs).

### Alias evidence

At the terminal alias checkpoint, read-only decoding showed:

```text
static LC0AliasString.saved = REF handle 4
static LC0AliasString.text  = REF handle 3
char[] handle 2             = [0x73,0x61,0x6d,0x65]  ("same")
Object[] handle 5           = [4,3,4,3]
String handle 3 fields      = [REF 2, INT 0]
LC0AliasBox handle 4 fields = [INT 6]
internHandles[0]            = 3
```

Thus the static, two reference-array cells, and intern table all name the one String
object; the static, local/reference array, and object field observations name the
one mutated box. q7 additionally captured a constructor frame with a `KIND_UNINIT`
handle 4 alias and the already interned String handle 3. No host offset or replacement
object was supplied.

### Initialization/fault evidence

The q7 snapshot had depth 3, class 0 initialization state 1,
`initializerStarted[0] = true`, `count = 1`, and the initializer next PC 13. A q10
measurement stopped immediately after the real `idiv` at PC 15:

```text
next PC=16, depth=3, class state=1, initializerStarted=true
pending.active=true, kind=ArithmeticException(1), ref=2, faultPC=15
nextHandle=2, emergencyRef=1, exceptionObjectCount=1
```

The uninterrupted q4096 state had class state 2, `count=1`, `value=9`, result 10,
and the same retained exception ref 2; no second initializer or exception object was
allocated.

This identifies the correct resume rule: a checkpoint after a fault records the
already advanced next PC and pending fault. Resume must process the pending
unwind/handler transition before dispatching another opcode, never repeat `idiv`.
Likewise, constructor/invoke/allocation/init work may yield only after its complete
current transition. The preflight's stop check would repeatedly return the same
pending state if reused unchanged; it is extraction instrumentation, not the final
step kernel.

## 5. Minimal codec recommendation

Use ABI only as the outer and initial canonical encoding, not a dump of all Solidity
locals. Define one `CheckpointV1` tuple and require strict size/count checks,
`abi.decode`, full semantic validation, canonical re-encode, and exact byte/hash
equality. Reject trailing bytes, noncanonical offsets/padding, invalid enum/kind
bits, duplicate/out-of-order records, unknown flags, and incompatible references.
The EVM creates every accepted start/child blob; a host can only carry opaque bytes.

Minimum fields:

```text
magic="JVMELC01", schema=1
instanceId, epoch, parentCheckpointRoot
runtimeCodeHash, artifactRoot, bootstrapRoot, configRoot
lifecycle, totalJvmSteps, totalInternalSteps, result/javaKind
class initializationState[], initializerStarted[], static tagged cells[][]
active FrameV1[] only
HeapV1(nextHandle, allocation counters, HeapRecord[1..nextHandle])
PendingException(active,kind,ref,faultPC)
emergencyRef, exception object/field counters
String intern handle/hash records
```

Each `FrameV1` carries class/method IDs, next PC, call PC, SP, exact live stack,
locals plus initialized bits, initializer/init-continuation/constructor/link/entered
flags, and `thisHandle`. Each `HeapRecord` has its exact sequential handle, kind,
dynamic class/rank/leaf metadata, and either exact `uint64[]` array cells or tagged
`uint256[]` object fields. Null is 0. Cycles and repeated handles are valid. There is
no second heap section and no recursively encoded object graph.

Do **not** persist ClassInfo/constant pools, selected Code, hierarchy/member/field/
handler caches, exception class/layout defaults, String layout offsets/defaults, or
per-class literal lookup caches in LC0. Reparse and derive them in EVM on every
resume from the exact raw bundle and the unchanged appended bootstraps. This choice
is justified for the first slice by tiny classes, a 100M LOCAL budget, and measured
full parse-plus-extraction calls below 13M. It also removes cache malleability and
prevents a host from supplying offsets. Reconstruct literal lookup caches by
matching EVM-parsed constants against the checkpointed intern handles and canonical
String heap contents.

Before execution, verify every frame method/PC/stack/local shape against reparsed
Code, all static/object cells against EVM-derived descriptors/layouts, every nonnull
reference against the one registry, allocation counters against records, exception
kind/class/ref compatibility, String backing `char[]` and intern uniqueness, and
all class-init/continuation invariants. Then establish local aliases exactly once:
all dispatcher heap/kind/class/rank views and `ExceptionArena.heap` reference the
same decoded arrays.

## 6. Exact next-freeze ABI and anchor

Recommended LOCAL-only contract surface (names may be frozen exactly by the parent):

```solidity
start(
  bytes32 instanceId,
  bytes[] rawClasses,
  string entryClass,
  string entry,
  int32[] args,
  uint64 maxJvmSteps,
  uint32 maxInternalSteps
) returns (SliceResult result, bytes checkpoint)

resume(
  bytes32 instanceId,
  uint64 expectedEpoch,
  bytes32 expectedCheckpointRoot,
  bytes[] rawClasses,
  bytes checkpoint,
  uint64 maxJvmSteps,
  uint32 maxInternalSteps
) returns (SliceResult result, bytes childCheckpoint)

head(bytes32 instanceId)
  view returns (address owner, uint64 epoch, bytes32 checkpointRoot,
                bytes32 artifactRoot, bytes32 configRoot, uint8 lifecycle)
```

`SliceResult` contains schema, lifecycle, epoch, checkpoint root, machine-state root,
total steps, and terminal int/known Java kind. It contains no host-computed PC,
frame, class, or heap metadata. The separate machine-state root excludes transition
history so q1/q7 terminal semantic states can compare equal; the checkpoint root
includes instance/epoch/parent to prevent history substitution.

Storage holds only an anchor per instance:

```text
owner, epoch, headCheckpointRoot, machineStateRoot,
runtimeCodeHash, artifactRoot, configRoot, lifecycle, entered
```

`start` requires an unused instance and binds owner to `msg.sender`. `resume`
requires owner authorization and CAS equality on both expected epoch and head. It
checks `address(this).codehash`, EVM-hashes the exact ordered raw classes and all
entry/argument bytes, reparses metadata, checks checkpoint provenance/canonicality,
executes EVM transitions, validates/encodes the child, increments epoch once, and
writes the new head only on successful return. Reentrancy is rejected. A stale,
foreign-owner, malformed, wrong-code/config/artifact call reverts without changing
the anchor.

The harness installs this oversized LOCAL code **once** into its account, then uses
`runtime.Call` for start and every resume on one reused `StateDB`. Re-running
`runtime.Execute` is explicitly not resume. Before each call the local driver takes
a StateDB snapshot; after success it writes/fsyncs the exact opaque returned bytes
and commits the StateDB root. Persistence failure reverts the in-memory snapshot.
No checkpoint is extracted from revert/OOG traces.

### Safepoint units

* A JVM unit is one complete dispatched instruction, including a complete faulting
  instruction. PC is always the next PC and `faultPC` retains the throwing PC.
* Pending handler search/unwind, init-continuation advancement, and constructor
  completion are explicit bounded internal units. On resume, an existing internal
  unit runs before any new opcode. Each unit has a phase/cursor only where the
  selected fixtures prove one is needed.
* LC0 does not phase-split general parsing, hierarchy walks, multi-array allocation,
  VFS, output, or scheduling. If a selected helper cannot fit the reserve, the call
  reverts as unsupported/resource failure and the old head survives.
* Stop checks occur only between units and before starting another. OOG/revert is
  never `RUNNABLE`, Java OOM, Java exception, or a successful yield.

## 7. Proposed finite LOCAL limits

These limits are for the next three-fixture kernel only, not Minecraft or a stock
transaction:

| resource | proposed LC0 limit |
|---|---:|
| ordinary `runtime.Call` gas | 100,000,000 |
| explicit boundary/malformed call gas | 1,000,000,000 |
| conservative commit reserve | 25,000,000 (must be measured) |
| JVM instructions per slice | 1..64 |
| internal transitions per slice | 1..4,096 |
| checkpoints per case | 256 |
| total JVM instructions per case | 4,096 |
| raw user classes / aggregate bytes | 4 / 64 KiB |
| checkpoint bytes | 1 MiB |
| active frames | existing 128 |
| heap/allocation quotas | existing monolith quotas, never raised |
| ordinary / boundary wall watchdog | 30 s / 120 s per call |
| whole LC0 gate | 20 min, 4 GiB RSS |

A 1 MiB checkpoint cap gives measured headroom over 596,480 bytes but is not a claim
that all existing heap quotas can be checkpointed. The implementation must reject
before oversized allocation/decoding. If decode/re-encode/commit does not fit 100M
and the 25M reserve, report the measured boundary; do not change EVM charging or
silently raise this profile.

## 8. Acceptance gates for that freeze

1. Production f50fe14 APIs/artifact and all old StringLB0 gates remain byte-for-byte
   unchanged; the local runtime is separately labeled and never presented as CREATE.
2. Java 8, Java 21, unchanged monolith, uninterrupted local kernel, q1-sliced, and
   q7-sliced executions agree on 15/36/10 and known Java outcomes. Runtime code is
   generic; fixture names/results live only in the trusted harness.
3. Call/loop checkpoints cover depth >1, caller `callPC`, locals/stack prefix, and
   return. q1/q7 final machine-state roots and side-effect sequences agree.
4. Alias checkpoints prove the exact same handles through local/static/reference
   array/String intern paths before and after mutation. The EVM view/validator, not
   host decoding, supplies inspected IDs.
5. Initialization checkpoints cover state 1 with an active initializer, q10-equivalent
   pending fault before handler search, handler entry with the same ref, state 2,
   `count=1`, `value=9`, and exactly one exception allocation. No opcode,
   constructor, initializer, allocation, or static write repeats.
6. Header/frame/heap/padding/offset/page-order and raw-class mutations, incompatible
   handles, cache-like host metadata, stale epoch/root, wrong owner, wrong instance,
   and wrong runtime/config/artifact all revert with byte-identical anchor/output.
7. A measured low-gas/reserve failure and actual OOG preserve the old head and emit
   no child. Retrying from the old blob yields the same child as the control.
8. Code-install tracing proves one local install followed only by `runtime.Call`.
   Supplying a valid blob through fresh `runtime.Execute` cannot resume it.
9. Persist/reopen the local StateDB plus opaque blob at an alias checkpoint and at
   the pending-fault checkpoint; both finish identically to uninterrupted controls.
10. Record exact source/runtime/class/blob hashes, every epoch/root/PC/depth/selected
    handle, gas, explicit limits, wall time, and replay commands. No MC/EULA/listener
    action is part of the gate.

## 9. Exact remaining implementation work and write set

The preflight did not hide the resume gap. The next single Solidity owner must:

1. introduce the mutable carrier and move `_execute` initialization out of the step
   loop without changing opcode semantics;
2. extract one-opcode and one-internal-transition entry points from the current
   dispatcher, preserving PC/fault/call/constructor/init ordering;
3. implement compact `CheckpointV1` decode, bounds, semantic validation,
   re-encoding, one-heap alias reconstruction, and EVM-only cache rebuilding;
4. implement start/resume owner/epoch/head CAS and commit reserve; and
5. add the reused-StateDB opaque transport/restart harness and the gates above.

Recommended frozen writes:

```text
jvmevm/runtime/local/lc0/**
jvmevm/localcontinuation/**
jvmevm/testdata/local/lc0/**
JAVA_EVM_MC_LC0_PLAN.md
build/java-diff-mc-lc0/**                 # ignored evidence
```

Do not edit `jvmevm/runtime/JVMSubsetInterpreter.sol` or its artifact,
`jvmevm/jvmevm.go`, stock S0/S1/S2, Makefiles, core/vm/state/types, consensus,
params, precompiles, peer/listener code, or global settings. Do not add VFS, threads,
fibers, scheduler, time, output, main, ZIP/JAR, MC, or EULA behavior in this freeze.
One worker owns all local Solidity.

## 10. Ignored evidence

Principal reproducibility paths (all ignored, not product or committed artifacts):

* `build/java-diff-mc-lc0-preflight/JVMSubsetInterpreterLC0Preflight.q{1,7,10,4096}.sol`
  and matching `runtime.q*.hex`;
* `build.js`, pinned local `package-lock.json`, and compiler logs;
* `run_probe.go`, `measurements.jsonl`, `measurements-q10.jsonl`, `run.restore.log`;
* `fixtures/src/**`, `fixtures/classes/**`, `environment-and-oracles.log`;
* exact `checkpoint-q*-*.bin` EVM return bytes;
* `inspect_alias.py` / `alias-inspection.log` and
  `inspect_init.py` / `init-inspection.log` (read-only evidence inspection); and
* `evidence-hashes.log`.

`run_probe.go` SHA-256 is
`aa5e68207a04d811c570e560730bc2d242f0ba90c91b4ff01b2582c43ccc5a2e`;
`measurements.jsonl` is
`09c80552137a8b7e884bdf0639f4b6ea92fee733eecb5fd6741b76050c22f38f`;
and `measurements-q10.jsonl` is
`bb5b174fd62d7592fa4151260b082178744ad39474066fcfb88d5485f345d7c1`.
The host inspection scripts are not on the execution path and cannot create or
resume Java state.
