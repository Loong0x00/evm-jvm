# MC-SC0: bounded nonliteral String construction

Status: **FROZEN implementation contract** after accepted MC-TL0 `09f7b20` and
parent review/replay of `JAVA_EVM_MC_SC0_CONSTRUCTION_STATE_PREFLIGHT.md` (`6dc8e3e`).
This authorizes only the work sets below, not acceptance, Minecraft, EULA or I/O.

## Base and bounded choice

Fork accepted TL0 into a separate runtime/package. Base runtime212574B SHA256
`c1a9a48d598e7efb7eaf636222ee596e767a22e5859384acd33e99314acf2084`, source SHA256
`58315c6ecaa09888cc9c12b996e525137b8489c08950e516873895118cbe48b3`.
Do not fork the earlier ignored LC0-derived String prototype: it lacks accepted
TL0 semantics and parent corrections. Preserve all accepted LC0/TL0/LB0/stock files.

TL0 and LC0 plans remain normative for unchanged input limits, state, heap,
constructor rules, faults/causes, ABI fields, stepping, provenance, durability and
error contracts. This plan specifies only SC0 differences. It overrides incompatible
recommendations in the two String preflights.

Add exactly public `String(char[])`, public `String(String)`, and content-based
`intern()` on non-interned receivers. No empty/range/byte/charset constructor,
substring/concat/formatting, builder, new String method, Throwable API, VFS, main,
thread, Class/resource/JAR, full Java SE or server-readiness claim.

Parent independently replayed all eight construction-state runs plus the expected
hard failure: canonical-return Object gave97099/110; publishing/failing Object gave
111/1111 and exposed a default String, whose length hard-failed BytecodeError(14,30).
q1 and one-call terminal roots matched. These were synthetic accepted-VM Object
profiles, NOT a modified-host-JVM oracle. `/tmp/mc-sc0-parent-construction-replay.log`.
The prototype is measurement only, not the production source or acceptance evidence.

Choose **option B**, explicitly narrowing only the NEW String-allocation capability.
Never silently skip Object Code or erase already-legal REF aliases. In particular,
TL0's ordinary-object/Throwable constructor self-throws and escapes remain unchanged.

## String image and bytecode execution

SC0 retains26 old bootstrap images bit-for-bit and substitutes only its separately
versioned String image. Accepted targets retain ALL their old27 bytes untouched.
Pin the measured984-byte String image, SHA256
`7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad`.
Source SHA256 `95542f5d4b869cc96ee395c322f8368a275fe3338ae60c7810afded6d4b81f2e`.
Keep new source and `.class.hex` under `runtime/local/sc0/bootstrap/`, reproduce with
`javac --release 8 -g:none`, and cross-check the embedded Solidity image. Source is
available read-only under the String-construction preflight's ignored bootstrap-src.
It retains private final `value:[C`, private `hash:I`, old native signatures/bridge,
and private unused no-arg constructor. Only the two public constructors are enabled.

Both public constructors are genuine trusted Java8 Code dispatched by the JVM:

* char-array constructor calls Object, allocates a distinct char array, copies each
  UTF16 unit with the Java loop, then installs `value`. Never install the source
  array, delegate copying to Go, add native constructors, or bypass loop steps.
* String-copy constructor calls Object, shares source's immutable `value`, and
  copies its hash cache. The target identity is distinct; no array is allocated.

`new` creates an ordinary UNINIT String object, charged with all inherited fields.
Constructor calls/returns/promotions/failure poisoning are normal TL0 execution.
Source null faults at actual guest arraylength/getfield with NPE6. No-GC allocations
remain charged after failure; completed effects are not repeated on resume.

Seven old native APIs retain behavior. `intern()` compares full UTF16 content in
EVM, using hash as a filter only. Hit returns the existing canonical handle. Miss
inserts and returns the receiver ITSELF, allocating no object/backing and mutating
no String hash cache. Pool metadata is VM bookkeeping. Full-pool hit succeeds;
full-pool miss routes Java OOM7 without insertion, not a profile error.

Intern records remain sorted by handle. A receiver may predate the last inserted
literal: sorted insertion, not blind append, is required. Duplicate content is
forbidden even when hashes collide. Later ldc/ConstantValue loads must find a
previously interned constructed receiver. Preserve old literal/CV timing and quotas.

## Exact no-callback Object constructor profile

Only `new` of exact SC0 String invokes this guard. Resolve normal class/hierarchy/
layout metadata, then EVM-resolve and parse actual direct `Object.<init>:()V` BEFORE
this new operation schedules initialization or changes Java allocation/quota state.
Already-completed initialization from earlier operations is not undone or relabeled.

Normal malformed/missing/inaccessible/static/native/abstract/Code errors retain
inherited parser/link/call contracts at the new opcode PC. An otherwise valid
constructor is supported only with max_stack0, max_locals1, empty exception table,
exact Code length1 and opcode `return` (0xb1). Existing ordinary debug/non-Code
attribute rules remain; do not perform speculative behavioral analysis of other
Code. A valid noncanonical body/shape gives **StringProfileError(4,newPC)**.

Do not reject arbitrary otherwise-legal Object static/instance field layouts, or
its ordinary `<clinit>` merely for existing. Resolve String's OWN fields base-first
by EVM declarations, never fixed offsets. Object fields remain charged and typed.
Malformed Object constructor errors precede the SC0 shape fallback. With valid
Object metadata but noncanonical Code, profile4 precedes later String-call errors
because the new opcode executes first. With a supported Object profile, malformed
String constructor descriptors retain CallError(4,invokePC); valid unsupported
constructors retain StringProfileError(1,invokePC). Wrong invocation mode/receiver,
access and name errors retain normal constructor contracts. At a supported String
constructor call, source must have the initialized REF tag, including for null;
a nonnull payload must name a rank1 char array or exact String respectively. Wrong
source tag/type gives CallError(4,invokePC) before entering the constructor. Null
REF is allowed into Code and raises genuine NPE.
Do not turn such a guest call error into a checkpoint StateError at a later quantum.

This guard MUST NOT apply to String ldc/ConstantValue preparation, arrays of String,
other object/Throwable new, or unrelated calls. Those accepted behaviors stay intact.
It is not an Object constructor native binding: the actual frame and its genuine
one return opcode still execute and may be checkpointed. A harmless but different
body such as nop/return is deliberately outside this exact new profile.

## One heap, state vocabulary and validation

Retain TL0's authoritative shared handles, ordinary versus implicit quotas and EIIE
cause records. String intern membership is NOT object identity or completion.
Rebuild String layout metadata whenever any allocated String, String frame or intern
entry needs it, even when internCount0. Do not force an over-quota dormant String
layout when no String was allocated after a failed new.

SC0 must admit these genuine states:

1. `new` before constructor invocation/argument evaluation: default own fields,
   UNINIT aliases. Argument evaluation may fail before any String frame exists.
2. Active String construction, including a root Object constructor above it:
   Object local0 may be REF while String/caller aliases are UNINIT; after Object
   return String local0 becomes REF but own fields may still be default.
3. A fresh destination array in the char constructor loop, before installing value;
   or installed value with constructor temporaries still live before return.
4. Copy constructor's shared backing transiently on the operand stack and later
   retained by both distinct Strings.
5. Unreachable failed/default String residues after NPE/OOM or argument failure,
   still counted; no refund and no global REF-means-complete shortcut.
6. Ordinary completed non-interned Strings, and canonical interned Strings.

Under the explicit option-B guard and pinned constructor Code, default/null-backed
Strings cannot escape as usable initialized references outside construction. The
validator must establish this from graph roots/constructor contexts, not presume
it for arbitrary input. Treat inherited fields as ordinary typed fields; "default
residue" constrains String's own value/hash, not an unrelated field-layout shortcut.

Recheck the no-callback Object profile in EVM when decoded construction/default/
non-intern String state relies on it; a valid-but-noncanonical Object body with such
state gives StateError7, not an accepted escaped-object state. Do not force this
check for literal-only states and thereby break literal/CV compatibility. Ordinary
raw-class parser/link errors remain raw-class errors, not manufactured Java faults.

Use bounded, deduplicated EVM graph traversal, not host parsing or unbounded recursive
walks. Roots include initialized frame/local/stack references (retain tag distinctions),
statics, pending refs, wrapper causes, intern entries and their heap closure. UNINIT
references may reach a pre-constructor default String; they are not escaped REF.
A matching active String constructor permits its legitimate String/Object receiver
REFs and temporary states. Reject default String reachable as an initialized REF
outside such construction. Unreachable default residues remain legal.

Every nonnull String value is a valid rank1 char array with16-bit cells. Its hash
cache is zero or the actual content hash. Active String own fields must match the
supported constructor phase; infer neither completion nor failure from REF alone.
Intern entries must reference structurally completed usable Strings, remain unique,
content-distinct, hash-correct and sorted; not every String needs an intern entry.

Immutable backing aliases are restricted to String's own value fields and exact
supported constructor temporaries. In char construction the pinned Code's destination
local2 and transient stack references are legitimate; source local1 is not a backing
alias. String-copy Code may carry source backing transiently on its stack. Backing
sharing between completed Strings is legal. Reject exposed backing through ordinary
statics/fields/reference arrays/caller locals; keep inherited Object fields distinct
from String's own value. Bound all graph/record/cell work by existing caps. No cached
layout/Code/PC/hash/graph metadata is accepted from Go. These checks are structural
validation, NOT proof of historical execution; live head commitments remain required.

Read-only validation must not run Java, modify hash caches, initialize classes,
allocate Java objects/emergency faults or repair state. Child validation/encoding
precedes publication. Preserve TL0's null-athrow consumption, concrete dynamic heap
class check, exact header offset180 and guest-versus-restored hard-error distinction.

## Namespace, codec, ABI and host transport

New contract/file `String0Interpreter`, path `jvmevm/runtime/local/sc0/`.
New package `jvmevm/localcontinuation/sc0`, asset package `sc0assets.Artifact()`.
Artifact names `String0Interpreter.runtime.hex`, `.abi.json`, and embedded
`artifacts/String0Interpreter.json`; include checked compiler/source/bootstrap
provenance. Solc exact0.8.30+commit73712a01, optimizer200/viaIR/Cancun/metadataoff.

Namespace schema1, domains `JVMEVM:MC:SC0:{ARTIFACT,BOOTSTRAP,CONFIG,MACHINE}:1`,
envelope magic `JVMSC001`, machine magic `SCS1`. Keep TL0216-byte envelope and flat
TLS1 field widths/order, including the wrapper-cause table, substituting magic and
SC0 commitments/new ordered bootstrap root. String admissibility changes, so use a
new decoder; do not reinterpret/import/upgrade TL0 or LC0 blobs or stores.

Public signatures/method names/event/head/errors are TL0's; result struct may be
named `StringSliceResult` but its13 fields/order/types are EXACTLY TL0's, including
opaque `javaClass:bytes`. Keep LC0ControlError/LC0StateError and ThrowableProfileError;
StringProfileError gains reserved reason4 above. No new Java exception kinds.

Go API is TL0's Runtime/RuntimeHash/ABI/NewMemory/Open and Session Start/Resume/Head/
ReadCheckpoint/Close. Result/SliceResult retain all fields including JavaClass[]byte.
Only opaque bounded ABI transport, no class/heap/String/graph decoder in production.
SC0 address `0x4a564d45564d53433052554e54494d4500000001`; store marker
`JVMEVM-MC-SC0-DISK-STORE-1\n`, format1. Keep accepted fixed context, filenames,
embedded-assets-only loading, bounded reads, code-not-reinstalled reopen, resolved
root aliases, metadata-before-LevelDB and exact publication/fsync failure behavior.
No storage/code injection except explicitly labeled one-time LOCAL runtime install.

## Core fixtures and independent gate

Freeze24 ordinary Java8 roots. Java8primary and Java21secondary oracles run unchanged
guest fixture bytes; native services/constructors execute inside EVM in production.
No fixture names/results/PCs in production code. Each bundle<=4classes/64KiB. Record
source/class hashes, bundle/entry/args/outcomes in deterministic fixture manifest.

| Group (8 each) | Root / expected int |
|---|---|
| SC0Chars | empty=0; asciiLength=5; nulUnits=1; surrogatePair=1; isolatedHigh=55296; isolatedLow=56320; defensive=97099; hashCache=2112 |
| SC0CopyIntern | copyDistinct=1; copyHash=2112; category2Caller=1; literalCopyIntern=111; constructedFirst=111; earlierHandleInsert=1; hashCollision=1; interfaceDispatch=1 |
| SC0Flow | nullChars=1; nullCopy=1; failThenValid=12; charsInClinit=1; initFailureThenNCDFE=3; loop64=64076; argumentFailure=1; throwableIntegration=1 |

Outcomes arise from actual copy/field/hash/alias/handler effects, not constant-only
roots. Existing ignored SCProbe defensive/intern/null/loop methods guide compatible
fixtures. Category2Caller carries live long/double words around String calls;
throwableIntegration stores the constructed String in a fresh Throwable field and
checks it after throw/catch. Initialization failure must retain actual NPE cause
through EIIE and preserve default String residue/class failure state.

Run24 one-call4096 controls. q1 AND q7 for ten roots: defensive, surrogatePair,
copyDistinct, literalCopyIntern, constructedFirst, earlierHandleInsert, hashCollision,
failThenValid, initFailureThenNCDFE, argumentFailure (20actual chains). Additionally
loop64 q7 (one chain); do not falsely claim q1 completion within256 slices for it.
Within SC0, final machine roots/outcomes/counters agree with one-call controls.
Also retain all24 TL0 fixtures on SC0 controls, its ten q1/q7 selections, and the
three LC0 byte bundles one/q1/q7/internal1. Compare outcomes/counters across profile
versions, not roots whose runtime/config commitments intentionally differ.

Independent32 numbered core probe groups (variants may be explicitly logged):

* 01..08: defensive-copy and copy-no-array accounting; failed-backing OOM residue;
  full ordinary/array quotas with intern hit and receiver insertion; inherited1024
  field fit/1025 OOM; exact1MiB/plus-one; declared over-cap counters/pool bounds.
* 09..16: publishing/failing Object rejected only for String new; nop/return and
  noncanonical max-stack/locals shapes; malformed/missing/access/static/native/Code
  precedence; unsupported/range/byte/empty String constructors; malformed descriptor;
  wrong mode/receiver/replacement/final-class rules; mixed-error ordering; unrelated
  Throwable/Object construction and String literal/CV compatibility under custom
  Object profiles. Synthetic Object cases are EVM-profile tests, not stock-JVM runs.
* 17..26: nonintern/no-pool metadata rebuild; pre-call argument failure/default
  residue; active Object/String REF/UNINIT states; illegal exposed default String;
  bad value/hash/backing/cells; external backing aliases versus legitimate constructor
  temps/copy sharing; duplicate content/order; earlier-handle insertion; intern miss
  returns receiver without allocation; TL0 cause/Throwable-field graph preservation.
* 27..32: CAS/namespace/blob/store binding; OOG during copy rollback/retry; reserve/
  progress; disk publication error seams including existing-blob sync; actual new-
  process mid-copy reopen; new-process pending constructor failure/cause continuation.

Do not manufacture unreachable live-boundary evidence. With1024 ordinary objects,
1024 distinct pool entries leave no extra nonintern String receiver: full-pool miss
is unreachable in an otherwise legal state today. Keep correct OOM code for that
branch but do not claim a live test of it. A full ordinary/array heap can still admit
an intern miss with a smaller pool, because insertion allocates no Java heap record.
Use an existing source/copy/literal/dummy-object combination to prove that case.
Similarly, some maximum element/field quotas exceed the1MiB checkpoint bound before
a terminal state can be published. Test earlier hard size rejection or read-only
counter bounds honestly, never seed a fabricated live head or relabel it Java OOM.

## Resources and work sets

Runtime<=256KiB, checkpoint<=1MiB;100M/30s ordinary and1B/120s dedicated boundaries,
25Mcommitreserve; percall1..4096 JVM/internal units. Existing quotas are unchanged.
Ordinary cases<=4096dispatchunits/256slices; SC0 dedicated copy/quota cases may use
<=65536dispatchunits/256slices. New gate external20min/4GiBRSS watchdog. No production
256-epoch cutoff. Maximum65536-char copy completion is NOT promised within test or
checkpoint limits; do not lower accepted array quotas or raise old budgets to hide it.

Final parent gates include newSC0, unchangedTL0/LC0/LB0/2231/smoke/fast/bootstrap/
Python/artifacts/Go/CLI/allstock/demos/AOT/focusedvet. No acceptance without actual
runtime, canonical positive/negative checks, failure reproducers and durable reopen.

Authorized disjoint sets:

* Runtime: ONLY `jvmevm/runtime/local/sc0/**`, including pinned String source/bytes,
  generic interpreter/codec/validator/guard/build/assets. One production Solidity writer.
* Harness: ONLY `jvmevm/localcontinuation/sc0/{sc0.go,session.go,session_test.go,README.md}`
  and `jvmevm/testdata/local/sc0/**`, opaque transport/24-root oracle corpus.
* Verifier: ONLY `jvmevm/localcontinuation/sc0/validation_test.go`; own ignored probes.
* Parent: plan/Make/docs/integration/independent probes/final acceptance.

Sol/high only, NO Fast/priority/spawn/push/peer writes/global-setting/core changes.
Missing artifact is a blocker/failure, not a skipped acceptance test. Surface true
schema/gas/alias/guard blockers rather than weakening the frozen contract.
