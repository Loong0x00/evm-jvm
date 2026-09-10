# LOCAL Throwable dependency preflight after MC-LC0

Status: **documentation and ignored prototype evidence only; no implementation
freeze or acceptance claim**. Prepared at `8a6566271bb8885cb99ceef51520507777438f9c`
after accepted MC-LC0. Parent replay is recorded in `JAVA_EVM_MC_TL0_PLAN.md`.
That frozen successor overrides this proposal's invalid blanket bans on active
constructor receivers/UNINIT aliases and its suggested host MUTF8 processing.
Authority remains `JAVA_EVM_PROGRAM.md`. The target remains
unchanged official vanilla Minecraft 1.12.2, Java 8, and eventually the genuine
guest `Done (...)` marker—not full Java SE.

No Minecraft/server/JAR execution, EULA action, listener, peer/core/consensus/gas
change, production source change, or production host Java evaluator was used. Only
trusted self-authored Java was run as a test oracle. LC0 remains frozen: 206,163
runtime bytes, SHA-256 `a1820864d8e846be4de8211158778150fdfde0e41e443aa66c44ec17f487e6cd`.

## Finding and recommended next slice

Take one small **MC-TL0 fresh-Throwable identity slice** before Java I/O. It should
be a new LOCAL continuation runtime derived from LC0, not an LC0 edit or import
path. Its only new guest capability is ordinary construction of supported
Throwable classes, dynamically typed `athrow`/catch/rethrow, exact initializer
wrapping, and an uncaught dynamic-class outcome.

This is smaller than M5d-b0 and adds **no Throwable method API**. Current LC0's
`_resolveNewClass` rejects every Throwable and `athrow` requires a nonzero arena-kind
byte, although handlers/initializer-Error checks use dynamic-class assignability.
Its codec requires pending/terminal kind 1..12 and has no wrapper-cause relation.
Thus allocation, classification and serialization—not handlers—are the minimum.

Retain all 27 bootstrap images byte-for-byte, including the 19 zero-field/no-arg
Throwable images. Do not yet add `IOException`, `FileNotFoundException`, or
`EOFException`; a separate Java-I/O version must bind their exact images and
constructor/message semantics. They must not become implicit kinds 13--15.

## Exact semantic boundary

### Allocation, constructors, and identity

* `new` may resolve any linked, accessible, concrete class assignable to the
  canonical `java/lang/Throwable`, within LC0's four-class/64 KiB input and existing
  hierarchy limits. “Any” means any supplied class in this bounded profile, not an
  arbitrary Java SE classpath.
* Every explicit `new`, including an exact canonical known exception, is an
  **ordinary heap allocation**. It charges the existing 1,024-object/65,536-field
  quotas, has dynamic class plus ordinary fields, starts as `KIND_UNINIT`, and is
  promoted only by normal successful `invokespecial <init>` completion.
* Preserve current constructor resolution, frame execution, field effects and
  identity. Abrupt construction leaves the no-GC allocation charged; all caller
  aliases of that uninitialized handle are poisoned exactly as in LC0. It never
  becomes a catchable partially initialized object.
* Only the existing canonical `()V` constructor chain is present. User constructor
  bodies/descriptors already supported by LC0 remain ordinary bytecode. Missing
  `(String)`, `(Throwable)`, message/cause and four-argument constructors fail by
  existing exact link/call errors; arguments are never discarded.
* Java 8 `Throwable()` virtually calls `fillInStackTrace`. The narrow zero-field
  profile cannot do that honestly. Before class initialization/allocation, reject a
  selected user ancestry whose dispatch would override exact
  `fillInStackTrace:()Ljava/lang/Throwable;` with
  `ThrowableProfileError(1,classIndex,methodIndex)`. Never silently skip callback
  code or return a fabricated stack.

### Explicit throws versus the implicit arena
* The existing 12 VM-generated kinds and 256-record plus emergency-OOM exception
  arena remain exactly separate. VM faults, EIIE/NCDFE/SOE/logical OOM continue to
  allocate arena records and remain available when ordinary quota is full.
* Heap dynamic class and hierarchy, never the metadata low-byte kind, decide whether
  an initialized ordinary object is Throwable and which handler matches it.
  `athrow` preserves the same ref through local/field/array/call/catch/rethrow paths
  and allocates nothing. Null alone raises arena NPE6.
* Arrays, invalid/uninitialized handles, category mismatches and initialized
  non-Throwables retain hard LC0 bytecode/reference failures, not catchable Java
  outcomes.
* For pending/outcome classification, derive `knownKind=1..12` **only when the
  dynamic class exactly equals** that canonical kind class. An explicit exact
  `ArithmeticException` therefore ends as kind 1 despite being ordinary; a user
  subclass of it is kind 0 and retains its own class name.

### Initialization failure and poisoning
* If the class targeted by `new` fails its own active initialization, no explicit
  object is allocated. Mark it erroneous and preserve LC0 prerequisite/unwind rules.
* A fully constructed non-`Error` escaping any `<clinit>` marks that class erroneous
  and is replaced by a fresh arena EIIE3. Record the exact original ref as the
  wrapper cause. Wrapper allocation failure produces emergency OOM7 without a fake
  cause.
* A fully constructed custom `Error` escaping `<clinit>` propagates the exact same
  ref, unwrapped. Later active use of either failed class raises fresh NCDFE12 under
  the selected Java 8 profile. Do not synthesize Java 21's implementation-visible
  NCDFE cause.
* No guest cause API is exposed, but losing the EIIE relation would make future
  semantics impossible. Store it canonically now; do not invent String/message/
  stack/suppression state.

## New LOCAL ABI and checkpoint version

Provisionally name the separate contract `Throwable0Interpreter`. Keep LC0's
`start`, `resume`, `head`, and `validateCheckpoint` argument signatures and owner/
epoch/head/CAS/event/rollback rules. Return a new struct:

```solidity
struct ThrowableSliceResult {
  uint32 schema; uint8 lifecycle; uint64 epoch;
  bytes32 checkpointRoot; bytes32 machineStateRoot;
  uint64 totalJvmSteps; uint64 totalInternalSteps;
  uint64 executedJvmSteps; uint32 executedInternalSteps;
  int32 result; uint8 javaKind; uint32 javaRef; bytes javaClass;
}
```

Canonical outcomes are:

* RUNNABLE: result/kind/ref zero and `javaClass` empty; pending may be custom.
* RETURNED: int result, kind/ref zero and `javaClass` empty.
* UNCAUGHT exact known class: kind 1..12, ref nonzero, `javaClass` empty.
* UNCAUGHT every other Throwable: kind 0, ref nonzero, `javaClass` equals the exact
  EVM-validated classfile internal-name bytes (1..65,535), with no slash-to-dot,
  message, nearest-supertype guess, or host class lookup.

The Go transport may strictly ABI/MUTF-8-validate and display those EVM-returned
bytes; it must not inspect classfiles or run Java. Malformed/noncanonical dynamic
outcomes remain runner failures. This successful terminal slice result replaces
M5d-b0's pure-runtime `JavaThrowable(bytes)` revert at the continuation boundary.

Use new domains `JVMEVM:MC:TL0:{ARTIFACT,BOOTSTRAP,CONFIG,MACHINE}:1`, envelope magic
`JVMTL001`, machine magic `TLS1`, and schema 1 in that namespace. Retain LC0's
216-byte envelope shape and 1 MiB total cap, but use a TL0-only decoder. LC0
`JVMELC01/LCS1` blobs are rejected, never upgraded or relabeled; TL0 blobs are
rejected by LC0. Bind the exact 27-image ordered hash, raw bundle, profile constants
and runtime code hash in TL0 config.

The `TLS1` stream is LC0-derived with these exact differences:

1. terminal prelude permits `(kind=0,ref!=0)` only for an uncaught non-known
   Throwable; the returned class bytes are derived from that heap class, not stored;
2. runtime creates kind-0 Pending only after `athrow` consumes `KIND_REF`; restore
   requires an ordinary Throwable ref that is not an exact known class, is not an
   active constructor receiver and has no `KIND_UNINIT` alias. Kind 1..12 must
   exactly match dynamic class regardless of arena/ordinary origin; and
3. after Pending and before intern records encode
   `wrapperCauseCount:u16`, then strictly increasing
   `{wrapperRef:u32,causeRef:u32}`. There is exactly one record for every arena
   kind-3 EIIE, `causeRef < wrapperRef`, cause is a valid non-Error Throwable, and
   no other record is legal. Re-encode equality and all LC0 reference checks remain.

No public checkpoint import/upgrade, outcome setter, heap inspector or host cause
injection is added. Standalone validation is not provenance; live resume still
requires exact EVM-anchored owner/epoch/root/config/runtime commitments.

## Proposed bounded acceptance gate

Keep ordinary calls at **100M gas/30 s**, dedicated boundary/malformed calls at
**1B/120 s**, 1..4096 units/call, at most 256 slices/case, and the whole new gate at
**20 min/4 GiB RSS**. Do not raise any accepted LC0/LB0/stock budget.

Freeze exactly 20 trusted Java roots: six construction/hierarchy/field cases; six
same-ref catch/call/field/array/rethrow cases; five constructor/class-init/EIIE/
custom-Error/NCDFE cases; and three uncaught exact-known/custom/subclass-of-known
cases. Compare Java 8 primary and Java 21 secondary results, then 20 EVM one-call
runs. Run eight boundary-sensitive roots as genuine q1 and q7 start/resume chains
(16 chains), including checkpoint after `new`, mid-constructor, pending custom throw,
EIIE replacement and custom Error unwind. Final values/outcomes/machine roots and
unit totals must agree where history is omitted.

Add exactly 32 independent EVM probes: eight allocation/arena/quota boundaries;
eight malformed `athrow`, constructor and fill-override rejections; ten canonical
pending/outcome/cause-codec mutations with rehashed outer fields; and six stale-head,
OOG rollback, retry and disk/new-process reopen checks. Preserve all accepted LC0,
LB0, 2,231, stock and artifact gates separately. A failed bound is a blocker, not
permission to weaken an outcome or budget.

## Ignored feasibility prototype and measurements

Evidence is under ignored `build/java-diff-mc-throwable-local-preflight/`. A throwaway
prototype copied the accepted **pure LB0** source (not LC0), removed the allocation
gate, made `athrow` hierarchy-based, and emitted strict `JavaThrowable(bytes)` for a
custom uncaught object. It does **not** implement TL0 serialization, cause retention,
fill-override rejection or resume, so it is not an implementation candidate.

Accepted/patched source SHA-256 values are `c2fab72e468a951e29fd069d3bf3dfa98ab1513138ed7ae33f219a2588fcea9d` /
`78f2df6c5f2cd88a8b2f00e059554eb7bb2fa4dfe7c877d0f14f10b3f9ef17b0`.
Solc 0.8.30 (optimizer 200/viaIR/Cancun/metadata-off) produced 166,583 bytes,
SHA-256 `be9d9790f3c7ef642e4711a30c2e36fec2e6d2e3cb448c1c962e48110f71e497`.
These were genuine EVM `runtime.Execute` **one-call** runs at 100M; neither
extraction-only nor actual checkpoint resume:

| Java 8 fixture | JVM 8 / 21 | EVM result | gas |
|---|---:|---:|---:|
| fresh custom caught, same ref/field | 17 / 17 | 17 | 2,732,434 |
| custom RuntimeException init, then NCDFE | 3 / 3 | 3 | 3,178,865 |
| custom Error init, unwrapped same ref | 7 / 7 | 7 | 2,627,207 |
| uncaught custom | exact custom class / same | exact 29-byte internal name | 2,473,555 |

Accepted LB0 (166,385 bytes, SHA-256 `ea94075540b8b66aa8e85823ee66e9dba4a2be65f29942855a8f59478bca0cbf`)
rejected the first case as `ObjectError(2,0)` at 1,100,616 gas. EVM used Java-8
classfiles; Java 21 was oracle-only. SHA-256: results=`1607cc76d6e0c7ff78f9460431813cdf3b2afe7b38c0d95d84c2eb3be2d00515`,
oracle stdout=`929d52b08dafa1dc053f06bed40da0046a392270605eba207f4ff51c3d25b61d`,
manifest=`86f07b7de74b2e894f2d273402adfbc585557822e4fefdcee537e0d0b7364aef`.

Exact replay commands from repository root were:

```sh
/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8 -g:none -d build/java-diff-mc-throwable-local-preflight/classes/java8 build/java-diff-mc-throwable-local-preflight/src/*.java
javac --release 8 -g:none -d build/java-diff-mc-throwable-local-preflight/classes/java21 build/java-diff-mc-throwable-local-preflight/src/*.java
(cd build/java-diff-mc-throwable-local-preflight/prototype && npm ci --ignore-scripts --no-audit --no-fund && node build.js)
go build -trimpath -o build/java-diff-mc-throwable-local-preflight/evm/runner build/java-diff-mc-throwable-local-preflight/evm/main.go
for m in caught init-runtime init-error uncaught; do timeout 30s build/java-diff-mc-throwable-local-preflight/evm/runner build/java-diff-mc-throwable-local-preflight/prototype/ThrowablePrototype.runtime.hex build/java-diff-mc-throwable-local-preflight/classes/java8 "$m"; done
```

## Deferred blockers

Message/cause APIs, general cause constructors, `getClass`, stack traces,
`fillInStackTrace`, suppression, printing/toString, synchronization and launcher
text remain unsupported—not null/empty/no-op stubs. The prototype did not prove
cause persistence, constructor-poison checkpoints, malformed codec handling,
actual resume, rollback or durable reopen. TL0 cost and 1 MiB fit are unmeasured.

After TL0 acceptance, separately preflight the three Java-I/O exception images,
nonliteral String/message construction and platform-generated ordinary exception
construction before freezing the VFS bridge. `IOException`/FNFE/EOF operational
errors must use ordinary constructor-backed identity, not the implicit arena or host
OS errors. No current evidence proves their exact messages are unobserved on the
real pre-`Done` path. MC main, VFS, resources/JAR, scheduling, logging/output and the
genuine `Done` marker all remain later work.
