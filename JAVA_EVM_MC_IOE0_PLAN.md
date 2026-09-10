# MC-IOE0: bounded exception messages and cause getters before VFS

Status: **FROZEN implementation contract**, conditional implementation work based on
accepted SC0 `2251d6c`, not an acceptance or Minecraft/VFS/EULA/listener claim.
Only the disjoint work sets below are authorized.

## Parent decision and base

Base SC0 runtime225303B SHA256
`a3fdedbcb6d517d567eb9ee0c9ab69955027a56859db8c26d9ef38e328a67e60`, source
`c983cd99ea1cb2139d978508ebc3fd935cdb28453bd0b3be46c19bee5d169a38`.
Retain all parent fixes through fe0c435, including scoped String constructor aliases,
field-write/null-fault phases and full-pool filtering. Fork into a separate target;
accepted SC0/TL0/LC0/LB0/stock source, images, outcomes and budgets stay untouched.
SC0/TL0/LC0 plans govern unchanged semantics. This plan overrides the unfrozen
`JAVA_EVM_MC_IO_EXCEPTION_PREFLIGHT.md` integrated as9711836.

Parent replayed all30 Java8/21 oracle rows from an owned ignored copy; hashes match
`1c6c2b9f1796c3dfc5d026e843ffd98bce7dc0f3fd2c352a9b0caa09db53b34a` and
`3c3b90e8b6af1c7b88215e3d80066870dc20b1b6348a9ae0771239e0ef687762`.
That is oracle evidence, not EVM implementation/resume/resource proof.

**Choose a smaller slice than the proposal.** Support fresh constructor-supplied
messages and EIIE cause fields/getters now. Defer implicit ArithmeticException
message Strings, the proposed metadata-carrier method, VM-message allocations,
new message quotas and handle-ceiling changes. Those are not needed to construct
IOException messages before VFS. Do not return a fake null for their unsupported
API: use the exact hard getter profile below. No `/ by zero` text is synthesized,
reserved, interned or added to the runtime in this stage.

## Exact guest capability

Add only these ordinary Java Code methods/constructors:

* Throwable: public ()V, (String)V, getMessage()String, getCause()Throwable;
* Exception: public ()V and (String)V;
* EIIE: public ()V and (Throwable)V, getException()Throwable and getCause()Throwable;
* IOException, FileNotFoundException and EOFException: public ()V and (String)V.

Throwable owns private detailMessage:String and cause:Throwable. Constructors
execute Object Code, set cause=this, and the message constructor stores the exact
argument ref. getMessage returns the field. getCause returns null iff cause==this,
otherwise the field. Null/empty/distinct/equal messages remain distinguishable and
no String is copied by these constructors. Exception/I/O constructors forward via
real invokespecial frames. Existing user virtual overrides execute ordinary Code.

EIIE owns private exception:Throwable. ()V leaves it null; (Throwable)V stores the
exact argument (null allowed). Both EIIE getters return that field. No String EIIE
constructor, Throwable(Throwable)/(String,Throwable), initCause, localizedMessage,
toString/printing, suppression, stack traces, fill callback, String builder/range/
formatting, Java File/stream API, VFS, main or scheduler is added. Missing APIs
remain exact inherited link/call failures. Preserve fillInStackTrace override
rejection; do not add native/no-op constructors or manufacture stack information.

Pin unsynchronized single-stack getter images below. This claims Java8 getter VALUE
semantics, not synchronized-method/monitor/thread equivalence. There is no no-op lock.

## VM-origin field initialization and exact getter profile

No extra message heap/counters/handles. All implicit exceptions retain their existing
arena origin/kind and quotas. At EVM allocation, including emergency OOM, initialize
canonical Throwable.cause to the newly allocated object's own REF; detailMessage
remains null. This is VM fault bookkeeping, not host execution or invocation of
constructor Code. Re-derive owner/name/descriptor field offsets inside EVM.

When a non-Error escapes <clinit>, allocate EIIE as before, then put the original
pending ref into its exception field. Preserve exact identity, ordering and failed
class behavior. If wrapper allocation becomes emergency OOM, do not write an EIIE
field into OOM or invent a cause. Errors propagate unwrapped.

**Replace** the TL0 wrapper-cause side table with the EIIE field in the NEW codec.
There must not be two authorities. Explicit EIIE remains ordinary allocation and
its argument may be Error, null, or a later-allocated Throwable. Only arena-origin
EIIE requires a nonnull non-Error cause with causeRef<wrapperRef.

An EVM call to the actual selected canonical Throwable getter has this profile:

| Receiver origin | getMessage | getCause |
|---|---|---|
| ordinary object (including exact known kind or user subtype) | genuine Code | genuine Code |
| VM NPE kind6 | Code returning Java8-pinned null | Code returning null |
| VM EIIE kind3 | Code returning null | EIIE override Code returning exception field |
| VM Arithmetic kind1 | hard unsupported | Code returning null |
| VM kinds2,4,5,7,8,9,10,11,12 | hard unsupported | hard unsupported |

Hard unsupported means new
`ThrowableAPIProfileError(uint256 kind,uint256 invokePC)`, not a Java exception or
fabricated empty/null value. Ordinary no-arg ArithmeticException still has null
message through genuine constructor/getter Code; VM Arithmetic getMessage is
explicitly NOT supported in IOE0. Do not infer origin from dynamic-class knownKind;
use the existing ordinary/arena metadata distinction.

Apply the guard only after normal receiver/null/method/access/descriptor resolution,
for the actual selected canonical getter and nonzero VM-origin receiver, before
pushing its Code frame. Do not intercept a user lookalike/override or wrong static
call, and do not alter normal null-receiver NPE behavior. Cover virtual and applicable
special/interface paths without adding host dispatch. EIIE getters execute their
actual pinned override. No native getter substitutes for supported Java Code.

## Pinned versioned bootstrap set

30 images: retain SC0 slots0..26 and substitute only Throwable, Exception and EIIE;
append IOException, FileNotFoundException, EOFException in that order. Thus24 old
SC0 images (including String984B) remain identical. Forbid raw replacement of the
three new reserved java/io identities; user subclasses remain ordinary input classes.
Do not renumber old canonical classes/kinds or rewrite accepted bootstrap files.

Pin these six new-version images. Exact source copies are under the parent's ignored
`build/java-diff-mc-ioe0-parent/minimal-bootstrap/src/` (read-only worker input).
Store reproducible source/hex under runtime/local/ioe0/bootstrap/; compile with Java8
javac -source8 -target8 -g:none (Java21 --release8 comparison is allowed).

| Image | bytes | SHA256 |
|---|---:|---|
| java/lang/Throwable |516|49b74f001ee43478dae744abc5413dcffd5dd5294856fdfbb92504f5ef0f0df1|
| java/lang/Exception |203|25cb2ac6e090fc75f4ca3faa8b00586b6373a53d0ace3024fe36be272a19b34e|
| java/lang/ExceptionInInitializerError |389|21fe8c2605bbb61c248207ed1e9c1a42b194aba9661e6b930b2c605cde962609|
| java/io/IOException |203|61b742b86e9be1d4c3bc8c5d90156befc8ce38afc5d4425bd5751b77224d4d17|
| java/io/FileNotFoundException |213|d964d55dc660566a64eda14af9dacbfa51a93baa8d5b772e73a083d2d258f654|
| java/io/EOFException |204|6cb3a2c8d9baa1403f9e5a11e7e46872bcc0da45099cbe315ec248f841a6fd0c|

Throwable516B deliberately differs from the proposal's584B carrier version. There
is NO unused VM-message carrier method or generated message String in these pins.
Build checks must bind source/class hashes and embedded image equality.

## Canonical state and constructor transients

One authoritative shared heap; unchanged ordinary1024-object/65536-field and arena
256-record/262144-field limits, per-ordinary-object1024 fields, emergency OOM and
shared handle ceiling. Added fields count in their appropriate origin quota. Do not
apply ordinary per-object quota to arena objects or waive ordinary allocation limits.
The1MiB checkpoint may dominate theoretical maxima; label such cases honestly.

Fields are base-first and located by declaring owner/name/descriptor. Throwable
message is null or an initialized exact String ref; String backing/alias/hash rules
remain SC0's. Ordinary canonical cause admits null or self, because a constructor
can fail or publish an initialized REF before cause=this executes. VM-origin cause
must be self and VM detailMessage null. No private-field setter/initCause is exposed.
User fields that shadow these names are separate, normally typed fields.

EIIE exception is null or initialized Throwable for ordinary origin; for VM origin3
it has the stricter nonnull/non-Error/prior-ref relation above. An explicit new EIIE
may evaluate/allocate its cause AFTER allocating the wrapper, so do not impose the
VM chronological rule on ordinary objects. Preserve aliases and cause-sharing.

A post-super REF does not mean all constructor field stores ran. Keep source NULL,
self-store, message-store and returned/failed phases admissible as real Code emits
them. Synthetic Object publication/failure can leave a reachable ordinary Throwable
with default fields; do not reject or erase that valid escaped REF. String new's
SC0 no-callback restriction remains isolated to String. No new lifecycle flag is
fabricated from host data. Validate typed graphs/cycles with bounded EVM traversal;
self-cause cycles must not loop. No constructor execution/repair during validation.

## New namespace/ABI/transport

Contract `IOException0Interpreter`, path runtime/local/ioe0; package
localcontinuation/ioe0 with ioe0assets.Artifact() from runtime/local/ioe0.
Files IOException0Interpreter.sol/.runtime.hex/.abi.json and embedded
artifacts/IOException0Interpreter.json. Keep pinned solc0.8.30+commit73712a01,
optimizer200/viaIR/Cancun/metadataoff and checked source/bootstrap provenance.

Namespace schema1: domains `JVMEVM:MC:IOE0:{ARTIFACT,BOOTSTRAP,CONFIG,MACHINE}:1`,
envelope magic `JVMIOE01`, machine magic `IES1`. Same216-byte header/formulas with
new domains/runtime/30-image bootstrap root. Machine is SCS1 field order/widths
EXCEPT remove wrapperCauseCount and wrapper/cause records entirely: after Pending,
encode internCount/records. No new message/origin section; origin remains heap metadata.

Public method names/signatures, head/event and13-field result are SC0's. The struct
may be IOExceptionSliceResult; keep opaque javaClass and no host message/cause ABI.
I/O uncaught outcomes are kind0/exact internal-name bytes, not kinds13..15. Keep
LC0ControlError/StateError, StringProfileError/ThrowableProfileError plus getter
profile error above. No imports/upgrades/setters or cross-profile store/blob reuse.

Go API/Result fields are SC0's with new package/assets only. Address is
`0x4a564d45564d494f453052554e54494d45000001`; store marker
`JVMEVM-MC-IOE0-DISK-STORE-1\n`, format1. Retain exact fixed context and durability:
opaque bounded bytes, runtime.Call after one explicit LOCAL install, genuine trie/
code new-process reopen, no reinstalls, metadata-before-LevelDB, owned temp recovery,
new/existing-blob sync, old-root recovery and gas-only failure publication output.
No host class/heap/message/String evaluation, core modification or standard CREATE claim.

## Exact core and boundary gates

24 paired Java8primary/Java21secondary roots, each <=4rawclasses/64KiB and (I...)I.
All24 expected int1 except failedClassLater=3; values arise from actual reference/
field/catch/dispatch effects. The VM Arithmetic message profile failure belongs to
negative tests, NOT a falsely matching oracle value row.

| group8 | roots |
|---|---|
| IOE0Messages | throwableZero; throwableMessageIdentity; exceptionMessageIdentity; ioZero; ioLiteral; fnfeConstructed; eofNullVsEmpty; virtualMessageOverride |
| IOE0Origins | explicitAE; implicitAECause; explicitNPE; implicitNPE; rethrowIdentity; ordinaryEIIE; wrappedAE; wrappedNPE |
| IOE0Causes | eiieNull; eiieArgumentIdentity; vmWrapper; sharedTwoWrappers; customErrorUnwrapped; failedClassLater; ioSubclassMessage; constructorFailureAfterSuper |

24 one-call controls; q1 ANDq7 for ten roots: throwableMessageIdentity, fnfeConstructed,
virtualMessageOverride, implicitNPE, rethrowIdentity, ordinaryEIIE, wrappedNPE,
eiieArgumentIdentity, sharedTwoWrappers, constructorFailureAfterSuper (20chains).
Within IOE0 compare outcomes/counters/final roots, including exact message/cause refs.
Retain all SC024/TL024/LC03 outcome controls on IOE0 and representative q1/q7/internal1
continuations. **Do not demand old cross-profile counters**: genuine new Throwable
constructor stores add opcodes; account them honestly. Old-profile gates run unchanged.

32 independent numbered groups:8 image/method/access/unsupported getter/API precedence;
8 origin/ordinary/arena/field/shared-handle/exact-checkpoint quota boundaries;
10 message/self/default/EIIE/chronology/cycle/constructor/alias codec groups;6 CAS/OOG/
rollback/retry/disk/new-process groups. Include ordinary EIIE with later-created cause,
full ordinary heap with still-available implicit AE/cause, wrapper emergency OOM,
VM getters deliberately unsupported, and synthetic Object escape before cause store
(EVM-profile only, not a replaced-host-JVM oracle). Missing artifacts fail/block.

Runtime<=256KiB, checkpoint<=1MiB,100M/30s ordinary,1B/120s dedicated boundaries,
25Mcommitreserve; percall1..4096 JVM/internal units. Ordinary cases<=4096total units,
dedicated quota cases<=65536total units; <=256slices, whole new gate20min/4GiBRSS
external watchdog. No accepted budget change. Recalibrate NEW exact-size fixtures for
changed object fields/removed table; do not rewrite old boundary bytes or outcomes.

Parent acceptance requires newIOE0, unchangedSC0/TL0/LC0/LB0/2231/smoke/fast/
bootstrap/Python/artifacts/Go/CLI/allstock/demos/AOT/focusedvet and retained regressions.
No file bridge, VFS, logging or MC-ready claim follows from this library slice.

## Authorized disjoint sets

Latest user preference: keep work written to repository files and use one or two
parallel agents. This stage uses exactly TWO workers, not a third verifier worker.
Runtime worker ONLY jvmevm/runtime/local/ioe0/** (including six versioned bootstrap
sources/hex, Solidity/build/embeddedassets). One production Solidity writer.
Harness worker ONLY jvmevm/localcontinuation/ioe0/{ioe0.go,session.go,session_test.go,README.md}
and jvmevm/testdata/local/ioe0/**. Parent independently owns
jvmevm/localcontinuation/ioe0/validation_test.go plus parent probes, and owns the
plan/Make/docs/integration/final acceptance. Neither worker may edit parent tests.
Sol/high, noFast/priority/spawn/push/peer/settings/core changes. Surface real blockers;
never weaken origin, class identity, failure contracts or budgets to claim success.
