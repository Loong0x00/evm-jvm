# M5d-a: implicit exceptions, ordered handlers and initialization-aware unwind

AUTHORITATIVE FROZEN CONTRACT. Supersedes alternative choices in
JAVA_EVM_M5DA_ARCHITECTURE_PROPOSAL.md and JAVA_EVM_M5DA_ORACLE_PROPOSAL.md.
Authority JAVA_EVM_PROGRAM.md; last-green M5c-d c6b6584:2091 oracle cases plus192
parent probes,36 Python,945 smoke/965 fast. Runtime135652 bytes SHA
cf68495083ebcd2df93f6d676e16afad87192a3401bd743a0301d805d5a8cd15.
NEW agents Sol/high WITHOUT Fast/priority; never --fast/re-enable preference.
Named java-fast is fixture tier only. Parent continuously integrates/verifies and
advances bounded stages, no routine confirmation.

## Atomic vertical slice / boundary
ALL existing Java-origin faults kinds1..11 must become pending guest exceptions,
with real initialized reference identities, ordered Code handler matching and
interframe unwind. Add athrow for captured VM exceptions/null and failed-init NCDFE12.
Do not implement athrow-only or arithmetic-only catches while other Java faults
still bypass them. Reviewable subcommits allowed, stage acceptance remains atomic.

Everything (raw parsing, canonical types, exception objects, fault generation,
matching, unwind, init states and guest code) executes in ordinary EVM bytecode.
No host Throwable/parser/evaluator/heap/AOT/precompile/JRE fallback, no external
self-call/revert-decoding trick to emulate pending exceptions. EVM validation errors
and OOG remain hard uncaught EVM failures. Four raw-bit native bindings remain the
ONLY native services. Trusted javac/JVM only build/oracle. Local runtime.Execute,
not deployment/full JVM/Java SE. Preserve2091 fixture sources/entries/budgets and
all ordinary numeric/ref/heap/call/init semantics not explicitly superseded below.

Defer new of ANY Throwable subtype, user Throwable constructors/instances/APIs,
messages/causes/stack traces/getClass/toString/printStackTrace/suppression, monitors,
threads/async exceptions/jsr/ret and full dataflow verification. Existing javac8
finally/catch-all cleanup bytecodes ARE supported with normal handlers/athrow.
Root remains exact static(I...)I, ordinary/interface. Captured exception refs can
move through existing locals/fields/arrays/args/returns/casts/identity comparisons.

## Canonical raw Throwable graph (19 new bootstrap images)
Keep existing five bootstrap source/hex/API behavior. Add these exact public Java8
canonical classes, with exact parents (VirtualMachineError abstract):
Throwable -> Object, implements java/io/Serializable;
Error -> Throwable; VirtualMachineError -> Error;
StackOverflowError(2),OutOfMemoryError(7) -> VirtualMachineError;
LinkageError -> Error;
ExceptionInInitializerError(3),IncompatibleClassChangeError(10),
NoClassDefFoundError(12) -> LinkageError;
AbstractMethodError(11) -> IncompatibleClassChangeError;
Exception -> Throwable; RuntimeException -> Exception;
ArithmeticException(1),NullPointerException(6),NegativeArraySizeException(4),
ClassCastException(8),ArrayStoreException(9),IndexOutOfBoundsException -> RuntimeException;
ArrayIndexOutOfBoundsException(5) -> IndexOutOfBoundsException.
All names under java/lang except existing Serializable. New sources have no declared
fields/APIs; compiler constructor metadata not guest construction support.

Sources+hex under runtime/bootstrap; bounded javac --release8 -g:none -Xlint:-options
joint build with needed existing bootstrap sources, pinned source->freshclass->hex->
embedded consistency, then normal in-EVM parser. No synthetic host hierarchy or
kind-name-only matching. New19 names VM-reserved: user input declaring one rejects
LinkError(6,inputIndex) in BOTH entry APIs. Existing replaceable Object/marker/Float/
Double policy unchanged. At most64 users+24 bootstrap types=88 runtime classes,
indices0..87<ARRAY_CLASS_BASE256. Input max64/duplicate/name/cap checks still apply
before internal append. Record all exact bootstrap sizes/hashes from actual build.

User classes may extend canonical Throwable for TYPE/catch validation only. Any
new target assignable to Throwable rejects ObjectError2(opPC), including canonical
types. Implicit VM objects are born initialized without executing Java constructors
or class initializers. No arbitrary user object qualifies for athrow by name alone.

## Exception arena and heap identity
MAX_EXCEPTION_OBJECTS=256 fresh per-invocation VM exception records; one extra reserved
emergency OOM. Ordinary limits unchanged:1024 arrays,65536 each/262144 total elements;
1024 ordinary objects/1024 fields each/65536 ordinary slots. Shared handle registry
max1024+1024+256+1=2305; no GC, reset every Run.

Centralize lazy registry setup across all allocation types. Reserve nonzero handle1
as a real initialized HEAP_OBJECT of canonical OutOfMemoryError before first ordinary/
exception allocation, set nextHandle1; never magic/out-of-table/zero ref. Normal
raises allocate fresh HEAP_OBJECTs with canonical dynamic class and exceptionKinds
metadata, increment exception counter only (not ordinary object/field counters).
Normal logical OOM/SOE can therefore be caught despite ordinary heap/frame caps.
On arena exhaustion, any NEW exception/wrapper allocation becomes pending kind7
using the emergency ref; repeated emergency reuse allowed/documented. Rethrowing
an existing ref never allocates, even after exhaustion. EVM memory/gas exhaustion
while creating/using registry is still EVM OOG, not catchable Java OOM.

Respect actual inherited field layout if a replaceable Object declares fields:
initialize those fields to tagged defaults without running constructors. Canonical
Throwable classes themselves declare zero fields. Arena fields have separate
MAX_EXCEPTION_FIELD_SLOTS=262144 INCLUDING emergency storage, not ordinary slots;
capacity can cause emergency OOM earlier than256 records. Object has at most65535
classfile fields, so its emergency inherited layout fits that bound. Normal arena
allocation exceeding remaining arena fields reuses emergency; no recursive OOM
allocation. Valid supported inherited primitive/ref fields keep normal layout;
unsupported malformed layouts remain uncatchable validation failures. This addition
avoids pretending a zero-length object layout when supplied Object has fields.
An optional internal cause/ref relation for EIIE is allowed, no exposed cause API.

## Pending state / Java fault migration
Maintain one execution-local pending state {active,kind,ref,faultPC}, plus frame/init
origin metadata as needed. Process pending before fetching another guest opcode.
After setting pending, the faulting opcode performs NO further store/allocation/
normal-return action. Precise synchronous effects before it remain visible to catches.

Inventory/migrate ALL19 _throwJava sites, all7 direct frame-cap SOE sites, and direct
ICCE/AME reverts in resolution/selection/special helpers. Helpers return explicit
Java-fault status to dispatcher; only validation still reverts. No _hasActiveInitializer
blanket wrapping remains. No direct JavaException revert except FINAL uncaught exit.
Call-cap failure raises SOE2 at invoking opPC without pushing a child, so a handler
in the full current frame can catch it. Four native bit services obey same depth rule.

## Handler parsing, validation and lazy resolution
MAX_EXCEPTION_HANDLERS=256 per entered method. Preserve classfile order exactly;
overlapping, duplicate and non-nested entries valid. Store start/end/handler PCs,
catch_type CP index and optional resolved-class cache in Selected. Parse entries
and following Code attributes, not the current blanket root Method8/callee rejection.

New signature HandlerError(uint256 code,uint256 classIndex,uint256 methodIndex,
uint256 entryIndex). Use entryIndex=uint256.max for whole-table/method faults.
- 1: count>256 or incomplete handler table (remaining Code attribute lacks8*count
  bytes plus following attributes_count); compute bounded before allocation.
- 2: start>=end, end>codeLength, handler>=codeLength.
- 3: start/handler not instruction boundary, end not boundary or codeLength.
- 4: nonzero catch_type bad CP index/tag/name chain or non-ordinary/array name.
- 5: range-applicable catch class missing on resolution.
- 6: resolved catch type is interface or not Throwable-subclass.
- 7: nonempty handler table but max_stack<1.
- 8: a matching handler would be entered while current constructor has not linked
  this/super (explicit supported-profile limitation, not full verifier).
- 9: resolved catch class inaccessible to current declaring class.
Other malformed outer Code lengths/nested attributes retain existing mode-specific
Class/Call/Init validation; no unchecked payload reads.

Ranges/CP shape/table cap/max_stack validated at load; boundaries use decoded start
map (including switch/wide rules). Nonzero catch class resolves ONLY when entry is
reached in pending scan AND its PC range applies, with normal hierarchy validation,
no class initialization. Cache per entry. Earlier applicable missing/invalid catch
fails hard rather than skipping to later handler. Catch-all0 needs no lookup. User
Throwable subtypes permitted as catch types if supplied/accessible, but no creation.
Missing/hierarchy/validation faults never become Java NCDFE; kind12 reserved for
previously failed initialization. This explicit lazy selected-method policy is NOT
HotSpot whole-class verification: preflight HotSpot may reject missing catch classes
before a no-throw body. Missing-type probes are EVM policy tests, not JVM parity.

## Ordered matching and interframe unwind
For each Java frame search from entry0: start<=pending.faultPC<end and catch-all or
thrown dynamic class assignable to resolved catch class. First matching entry wins.
On match preserve locals/initialized states, set pc=handlerPC, discard ENTIRE operand
stack, push SAME exception ref as sole category1 item, clear pending. F/D/J locals
and unrelated constructor tokens remain intact. Handler target is a normal opcode
start; handler stack needs one word, not the discarded prefix's size.

If no match, discard Java frame and use popped.callPC (INVOKE start) as caller fault
PC, not caller's already-advanced pc. Maintain identity across calls/rethrow. Synthetic
initialization continuations have no handlers and forward to recorded active-use
request PC or root-entry sentinel while applying failure rules below. Validation
errors and EVM OOG cannot enter guest handlers, even catch(Throwable)/catch-all.

Constructor safety: promote aliases only on NORMAL ctor return. Abrupt child<init>
exit poisons every immediate-caller local alias of its uninitialized thisHandle
(and stack aliases defensively); never mark caller linked. Handler stack is cleared.
Invalidate aliases using initialized=false/poison consistently. A matching handler
in an UNLINKED constructor rejects Handler8 rather than pretend full JVMS4.10.1.9.
Post-super handlers work; failures caught by the caller around new/ctor work. Do not
poison this for an ordinary helper failure merely because called before super.

## Initialization state machine (four states)
0 uninitialized,1 initializing in this single execution,2 initialized,3 erroneous.
Preserve preparation/default/ConstantValue and M4fb superclass/default-declaring
interface ordering. State1 reentry succeeds with current/default values.
Record continuation owner/phase(own clinit vs prerequisite), started state and
request/invoke PC/root origin. Check frame capacity BEFORE changing a fresh target
to state1 when scheduling needs a frame. On failed scheduling leave untouched target0;
installed active-owner continuations unwound due failure become erroneous. No state1
residue after catchable SOE. Trivial init can complete without unnecessary frame.

Initialize root class BEFORE root Java method becomes eligible for handler search.
A root's own initialization/super/default-interface failure is outside its not-yet-
entered method; its method's handlers cannot catch that failure. Preserve existing
normal root frame-limit behavior and args until entry succeeds; a reserved dormant
root frame is acceptable (and preserves prior initialization depth accounting), but
MUST NOT be searched for handlers before entry. No extra counted permanent entry frame.

Search helpers and actual <clinit> handlers FIRST. A caught fault allows initialization
to continue; no early EIIE/failure. Only an UNHANDLED fault leaving actual <clinit>
marks its owner erroneous and wraps non-Error in fresh EIIE3; Error/subtype identity
unchanged. Determine Error via canonical class hierarchy, not stale kind lists.
If wrapper allocation exhausts arena, propagate emergency OOM7. When prerequisite
initialization fails, mark each abandoned dependent class erroneous and forward
SAME Error (no double wrapping). If A.<clinit> actively uses failed B, deliver B's
error at A's active-use PC so A can catch and complete; if uncaught A fails too.

Later active use new/getstatic/putstatic/invokestatic of ACTUAL erroneous owner
raises fresh catchable NoClassDefFoundError12 at opPC after existing resolution/
access/shape checks. Qualifying classes/interfaces not actively initialized remain
unaffected. All states/heap reset next Run; no cross-invocation persistence claim.

## athrow and uncaught ABI
athrow0xbf width1. Empty stack Bytecode3; int/J/F/D/uninitialized ref Bytecode14;
invalid handle Reference1. Null initialized ref raises fresh NPE6 (arena failureOOM7).
Non-null captured registry exception uses same kind/ref, no allocation; non-arena
ref (even ordinary Throwable-looking class) Bytecode14. Operand prefix is discarded
on handler entry/unwind, not required empty before athrow.
Final uncaught pending exits using EXACT existing JavaException(uint256) payload,
adding ONLY12 java.lang.NoClassDefFoundError. Kinds1..11 unchanged; host decoder only
canonical36 bytes, unknown/noncanonical/trailing errors unchanged. No ref/message/
cause crosses ABI. Graph Error includes2/3/7/10/11/12 and controls wrapping.

## Oracle/fixture discipline and gates
Preflight architecture/oracle proposals are evidence, THIS document resolves:
raw19 canonical classfiles (not host/synthetic-only hierarchy),256 fresh arena+
emergency,256 handlers, lazy applicable-catch resolution, allowed user catch subtypes,
Handler8 on matched unlinked-ctor handler, exact errors above. Source archives remain
in m5da-oracles/build/java-diff-m5da-oracle-preflight (proposal hashes recorded).

Append~100-140 trusted Java8 m5da cases, preserve2091 prior entries/sources/budgets.
Catch all source-reachable implicit kinds by exact/supertypes/Throwable/catch-all,
ordered multi-catch/nested/finally/rethrow/null identity, every invocation mode and
invoke-only ranges, F/D/J locals/prefix, stored Throwable refs/casts/arrays, init
caught/uncaught/reentrant/EIIE→NCDFE/super/default failures/root-before-entry.
No new Throwable/API calls/JRE printing in guest. OOM/arena/SOE resource limits are
Go/EVM-only tests, no new host OOM/SOE exhaustion. Binary-evolution ICCE/AME use
bounded Java8 exact oracles as before; Java21 can differ and is secondary signal.

Fixture owner may narrowly extend HOST-ONLY OracleMain class-initialization outcome
reporting for the known Error classes where current catches omit them. Reflection/
missing entry/argument/class harness failures remain failures; don't blanket catch
all harness Throwables as valid guest output. Preserve protocol and existing cases.
No production host handling of Java exceptions beyond kind12 decoding.

Independent Go every HandlerError code/boundary/CP/trunc/cap/cache, local matching
order/invokePC/stackclear, all direct previous SOE/ICCE/AME paths catchable, every
knownkind1..12/super/catchall/rethrow, validation/OOGuncatchable, arena256fresh vs257
emergency/rethrowwithoutallocation/reset, ordinaryfullheapOOMcatch, frame128SOEcatch,
init scheduler no sticky1/root sentinel/failed dependents/wrapping boundary/NCDFE,
ctor poisoning/Handler8/postsuper. Typical probes<=20M, complexinit<=80M, Go-only
quota/arena<=250M; measure failures before any budget changes. No host memory exhaustion.

Parent integrates runtime->fixtures->verifier; obsolete handler/athrow guards ONLY
explicitly updated after evidence. Independently rebuild24bootstrap images/artifact,
Go/CLI/Python2091+fulloracle/smoke/fast/demos/AOT/vet plus new probes. Preserve four
raw-bit bindings and ordinary limits. Accept last-green then freeze user Throwable
construction/APIs separately. No routine confirmation/full-JVM/deployment claim.

## Ownership
Runtime ONLY Solidity/runtimehex/build.js;19newbootstrap*.java/*.class.hex; jvmevm.go
kind12decoder only; jvmevm_test.go HASH ONLY; integer_test.go decoder tests only;
new jvmevm/exceptions_test.go runtimeM5da* helpers. Existing5bootstrapbytes/compiler
deps/settings/hostAPI/CLI/fixtures/harness/oldtests not owned. Report obsolete tests.
Fixtures ONLY differential/** including narrow HOST-ONLY OracleMain update, stage
m5da/preserve2091/schema1. Baseline rejection -> bounded manual trusted oracle checks,
not harness edits/fake EVM green. Verifier ONLY tools/java_diff.py,test_java_diff.py,
JAVA_DIFF.md,new jvmevm/exceptions_validation_test.go verifyM5da* helpers. Baseline
red expected, exact failures documented. Parent owns plans/AGENTS/quickstart/Makefile,
explicit old-profile updates and integration/independent review.
One Solidity writer, no spawning/peer writes/push/global config/untrusted Java.
All agents Sol/high WITHOUT Fast; scoped commits/honest hashes/caveats/limits/checks.
