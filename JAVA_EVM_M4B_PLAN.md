# M4b: ordinary objects, constructors, fields and direct special calls

Authority: JAVA_EVM_PROGRAM.md. Last-green M4a c97e2db:613 oracle cases plus44
parent probes. Sol/high, inherited Fast preference (priority requested, backend
acceptance not guaranteed). Parent integrates/independently verifies then proceeds
without routine confirmation. This stage deliberately separates construction from
virtual override selection: invokevirtual/casts/type tests are M4c, not this batch.

## Execution boundary and supported profile
All class parsing, linking, allocation/layout/defaults, reference assignment,
constructor lifecycle, fields/calls and guest instructions execute in ordinary
EVM bytecode. Host packs unchanged classfiles and int args, invokes EVM, decodes
outcomes. No host class parsing/evaluation/heap, AOT, native precompile, filesystem
classpath fallback, class-specific runtime or consensus changes. Local runtime.Execute,
not CREATE/mainnet deployment. This is a subset, not full JVM verification/Java SE.

Root remains unambiguous static (I...)I; reference roots retain MethodError11.
Internal static/special methods accept I, [I, L<internal-name>; arguments and
I/V/[I/L<internal-name>; returns. Fields accept I/[I/L<internal-name>; constructors
must be <init> returning V. Extend descriptor parsing exactly; no other primitive,
reference-array or multidimensional descriptors yet. Unsupported descriptors keep
existing method/call/field errors. Preserve all earlier opcodes and typed checks.
Null is assignable to supported reference descriptors; int[] is assignable to [I
and java/lang/Object; ordinary objects are assignable to their class/superclasses/
Object, not arrays/unrelated classes. No interfaces yet. Resolve supplied names
when needed, no external loading; do not invent class definitions for unknown
classes. External root numbers can never forge references.

Add new (0xbb), getfield (0xb4), putfield (0xb5), invokespecial (0xb7).
No invokevirtual/invokeinterface, checkcast/instanceof, athrow/handlers, monitor,
strings/class literals, other Object APIs, other numeric/array types this stage.
Predecode must know operand widths and reject truncation/invalid branch targets.

## Bootstrap Object: real raw classfile inside EVM
When no input class declares java/lang/Object, append an internal bootstrap class
AFTER user classes, parsing its raw bytes through the normal in-EVM class parser.
Never replace a supplied Object class. Preserve original user class indices and
max64 input classes; the internal bootstrap slot does not count against input cap.
Zero/duplicate/malformed input rules stay. Existing hierarchy validation applies
when a user supplies Object (including illegal nonzero superclass).

Only bootstrap API is public Object.<init>()V, with ordinary Code containing
return. Its execution uses the same instance frame/bytecode machinery, NOT a
host or EVM hardcoded skip-call shortcut. This is an explicit minimal class-library
image, not the complete JRE Object implementation. Parent locally verified:
`package java.lang; public class Object { public Object() {} }`
with javac --release 8 -g:none -Xlint:-options produces95 bytes, major52,
super_class0, no fields/interfaces, one public constructor, max_stack0/max_locals1,
code b1. SHA256 af9136af3be2c44ce120ac403beccb8b1cc963fc83dc1457e63f8b69dd497fe0.
Check in source and hex; embed those exact bytes in Solidity and extend build.js
check/build to verify source->javac->hex->embedded constant before pinned solc.
Use bounded local subprocess/timeouts and temporary directories; no downloaded
bootstrap libraries. Keep solc0.8.30/optimizer200/viaIR/Cancun/metadata settings.

## Heap, layout and resource semantics
One unforgeable handle namespace for arrays and ordinary objects, with explicit
heap kind and dynamic class identity; references may alias across frames/fields/
statics. Distinct allocations stay distinct, null stays zero reference. Preserve
M4a array ops, identity and accounting when objects/arrays interleave; never use
array count as the total handle validity bound. Wrong heap kinds must not let an
object be reinterpreted as an array or vice versa.

Object layouts include inherited instance fields, keyed by actual declaration,
not merely name. Base/child hidden same-name fields are separate. Static fields
remain class-owned and are excluded from object storage. Base-first layouts may
use stable declared-field offsets across subclasses. Allocate/default all fields
before constructor execution: tagged int zero, tagged null refs. Instance
ConstantValue attributes do NOT initialize instance values (only constructor
bytecodes do); retain existing static ConstantValue semantics.

Keep array limits1024 arrays/65536 each/262144 total elements. Add limits1024
objects,1024 instance fields per object (including ancestors),65536 total allocated
instance-field slots. No GC: unreachable objects/fields/arrays still count until
invocation ends. Array/object counts and totals are independent; unified registry
can hold2048 total handles. Logical limit overflow is Java OOM kind7, not Solidity
panic; negative array sizes still precede array-cap checks. Fresh invocation resets
heap/statics. Unsupported instance field types in an allocated layout reject
explicitly; don't allocate incomplete pretend objects. Limits don't guarantee gas;
Go-only boundary probes may use finite250M if measured necessary. Never exhaust
host reference-JVM memory. Preserve existing case budgets and all other limits.

new resolves/checks an accessible ordinary non-abstract class, initializes that
class/superclasses using existing lazy/reentrant initialization, then allocates.
Replay the new instruction after scheduled <clinit> without duplicate allocation.
getfield/putfield/invokespecial don't independently trigger class initialization.

## Construction/lifecycle and invokespecial
Use distinguishable uninitialized references/tokens (not merely one global heap
initialized boolean). new's reference may be duplicated/moved through reference
locals/category-1 permutations; it cannot escape into args/fields/statics/returns,
be numerically consumed, or be used as a normal receiver before permitted init.

Constructor invocation requires an uninitialized object receiver and exact
<init> declaration in symbolic owner (constructors aren't inherited). For a new
allocation owner must be its allocated class. Within a constructor, uninitialized
this may invoke this(...) or direct-superclass <init>. Enforce access and receiver
rules. Receiver occupies local0, explicit arguments follow, with independent
frames; max_locals must accommodate receiver+args. Respect max128 frames and
existing StackOverflow outcome. Constructor cycles still obey finite frame/gas
limits, no recursion bypass.

After constructor return, initialize aliases of that uninitialized token in the
IMMEDIATE CALLER frame (stack and initialized locals), not all frames globally.
Thus a base constructor may use/publish initialized this after its super returns,
while aliases waiting in outer constructors/new's caller remain uninitialized
until their constructor call returns. Track whether each non-Object constructor
has successfully invoked this/super before allowing return. Object's root ctor
needs no super: its own local0 is initialized from entry, but its caller's token
aliases are initialized only on return. Constructor arguments may allocate/initialize other objects
without prematurely initializing this. Repeated constructor invocation on an
already initialized receiver is invalid. Transport operations accept uninitialized
refs where needed, ordinary typed consumers must not silently accept them.

JVMS pre-super putfield exception: uninitialized this can receive putfield ONLY
for a field declared by that constructor's own class; value must itself have an
ordinary compatible type (no uninitialized reference escape). No pre-super getfield
or unrelated receiver exemption. Once initialized, usual field rules apply.
Final instance writes require current frame <init> of actual declaring class;
subclass constructors can't write ancestor finals. Do not incorrectly require
receiver identity=this for an otherwise initialized receiver: final-field JVM
rule is declaring class plus constructor context. Keep final checks per use even
when CP resolution cached. Array-element mutation through a final ref is allowed.

invokespecial also supports private instance methods and ordinary super calls,
never virtual dispatch. Enforce declared/member/class access and cross-package
protected receiver restriction (dynamic receiver must be caller/subclass).
Private methods use exact resolved declaration. For non-private superclass
calls under ACC_SUPER, select starting at current class's direct superclass,
not an arbitrary explicitly named grandparent override bypass. Other unrelated
special-call forms reject explicitly. Interface/default methods remain unsupported.
Return I/V/reference using existing opcode conventions, check descriptor and
reference assignability; null receiver on valid non-constructor instance operations
is NPE kind6, never raw memory access. Keep static calls separate from special
calls and preserve static-vs-instance mismatch errors/caches.

## Error contract
No new Java exception kinds this stage: Arithmetic1,StackOverflow2,EIIE3,
NegativeArraySize4,Bounds5,NPE6,OOM7. Constructor failures in ordinary execution
remain their Java outcome; non-Errors escaping active <clinit> wrap as EIIE;
StackOverflow/OOM stay Errors. EVM OOG is never Java OOM. Uncaught only, no handlers.

- BytecodeError14(pc): numeric/reference kind mismatch or forbidden use of an
  uninitialized reference; initialized/null ref passed as constructor receiver
  also fails required uninitialized kind. Transport ops are the stated exception.
- ReferenceError1(pc): invalid handle OR wrong heap kind (preserve M4a contract).
- ReferenceError2(pc): valid reference not assignable to declared reference type/
  class receiver. This is validation, not a pretend ClassCastException.
- ObjectError(uint256 code,uint256 pc): 1 malformed new class CP reference/name
  (including array target); 2 inaccessible/abstract class or unsupported instance
  field layout; 3 invalid constructor/special form/lifecycle (wrong ctor owner,
  constructor returning before this/super). Unsupported interfaces/header shapes
  retain existing LinkError5, missing class uses existing LinkError4 conventions.
  New logical object/slot limits use OOM7, NOT ObjectError2.
- CallError1 malformed methodref,3 missing exact declaration,4 unsupported method
  shape/access/static-instance mismatch; CallError5 return opcode/descriptor
  mismatch. Field errors retain existing meanings, including4 access/final write.
- Root/static/array/predecode/hierarchy errors remain exact. No blanket accepting
  any revert as an expected Java exception; isolate negatives to one intended defect.

This is not a full classfile dataflow verifier or linkage-error taxonomy. New
abstract allocation, invalid constructor forms, unsupported library APIs and
other excluded capabilities fail explicitly, not fabricated successful values.
If a previous negative becomes genuinely obsolete due to bootstrap/object support,
report exact case and cause to parent; do not silently weaken/change old tests.

## Fixtures, verifier and acceptance
Append roughly80-120 trusted Java8 cases, preserve all prior613 entries, sources,
expected outcomes and budgets. New cumulative m4b/defaultm4b, schema1/root protocol
unchanged. Oracle host only executes trusted fixture sources, no OOM exhaustion.
Fixture methods must stay inside this stage: access public fields/static helpers,
or private instance helpers compiled as invokespecial; ordinary public instance
calls (invokevirtual) are NEXT stage, not a reason to implement outside scope.

Cover defaults/constructors, private helper args/returns/recursion, this/super
chaining, object identity/aliases/null, reference locals/static/instance fields,
int[]/Object transport and mixed heaps, inherited vs hidden storage, final fields,
classinit allocation/reentrancy/order and exception wrapping, same/cross-package
access, direct-super method selection. Values stay int32 including overflow.

Independent Go verifier covers exact malformed CP/operands/branch targets; wrong
heap kind/class assignment; root signature rejection; receiver/arg/return slot
validation; constructor-owner/lifecycle/alias misuse; final/protected rules after
cache population; null-field/special calls and exception ordering; object/field/
array cap independence/no GC/reset; OOM vs OOG. Add source review where defensive
invalid handles aren't legally forgeable. Preserve all M4a boundary tests.

Parent integrates runtime, fixtures, verifier, resolves only real integration
issues, rebuild-checks artifact/bootstrap, Go/CLI/Python real+mock tests, all613+
oracle cases, smoke/fast, demos/AOT/vet, independent object probes. Archive evidence
and last-green commit. Then freeze M4c invokevirtual/override/casts/type tests
(especially package-private override chains) without routine confirmation.

## Worktree ownership (one writer per path)
- runtime: jvmevm/runtime/JVMSubsetInterpreter.sol + runtime.hex + build.js;
  new jvmevm/runtime/bootstrap/Object.java and Object.class.hex;
  jvmevm/jvmevm_test.go EXPECTED RUNTIME HASH ONLY;
  new jvmevm/objects_test.go (runtimeM4b* helpers). No host production API edits
  needed; no old test changes without parent review. Own bootstrap reproducibility
  tests in objects_test.go/build.js. No compiler setting/dependency changes.
- fixtures: ONLY jvmevm/testdata/differential/**. Stage m4b, append cases, root int
  oracle protocol unchanged. Use fresh per-bundle JVM compilation, inspect javap
  to avoid accidental invokevirtual/JDK calls; can validate oracle manually while
  baseline runner rejects new stage. No production/harness files.
- verifier: ONLY tools/java_diff.py, tools/test_java_diff.py, tools/JAVA_DIFF.md,
  new jvmevm/objects_validation_test.go (verifyM4b* helpers). Can inspect shared
  helpers but do not edit existing Go files/runtime/fixtures. Initially expected
  failures on M4a artifact; preserve exact tests and report them, no weakening.
- parent: plans/AGENTS/Makefile/quickstart, integration, independent checks.

All workers commit only owned files, no remote pushes/global settings/peer writes/
subagents/untrusted oracle inputs. Work only assigned worktree, report measured
verification and SHA/size/hash honestly; don't claim integrated green from baseline.

## Parent integration verification (independent final review in progress)
Runtime e9147bd→e951bbb, fixtures87b9b90→8779282, verifiera192f56→efb5a6c.
Initial integration:6 Go groups red and712/713 oracle cases. Followup a5421f1→
d754944 fixed five proven malformed mutation setups without relaxing assertions,
wrong-heap-kind errors, per-object field-cap OOM, and quadratic object defaults.
Cached linear layouts reduced1024-field allocation from137,705,906 to12,527,300
gas;64 objects now62,127,859;65th OOM62,124,014. No budget increase.

Parent corrected fixture e70a168: final initialized=17 was a Java constant and
javac emitted out-of-profile Objects.requireNonNull plus an inlined value. Moving
17 assignment into constructor preserves the intended final-field/value test and
emits real getfield (confirmed javap). No host/JRE fallback added. All prior613
manifest entries/budgets remain identical. ConstantValue-ignore behavior remains
covered separately by precise test-only getfield mutation.

Parent reran artifact/bootstrap consistency, focused Go/CLI,31 real/mock Python,
713/713 full JVM/EVM cases,289 smoke,309 fast, all demos,AOT and focused vet.
Further46 independent source probes for this/super/private calls, hidden fields,
Object/int[] transport, mixed heaps, aliases, static initialization, null and
int overflow passed: build/java-diff-parent-m4b/probe-idc7mvlv/results/.

Current runtime57900 bytes, SHA256
6c1b74d7a15c247644e6831358558231d59243a21ab3068dca523e79d125cbc4.
Review worker is read-only in m4b-independent-review, also proposing the M4c
virtual-dispatch/cast contract. Last accepted stage remains M4a until final review;
then record acceptance/update quickstart and freeze/dispatch M4c automatically.
