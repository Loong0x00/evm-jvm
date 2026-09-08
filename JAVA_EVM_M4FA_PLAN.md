# M4f-a: interface graph, abstract calls and interface reference types

Authority JAVA_EVM_PROGRAM.md. Last-green M4e927868d:960 oracle cases plus48
independent probes,34 Python,415 smoke/435 fast and full focused gates.
Runtime80614 bytes SHA435082ccaf879e822d2e02b8f698f804284e3e7e48f65918c1b0184d39f38590.
ALL NEW agents Sol/high WITHOUT Fast/priority; never --fast or re-enable preference.
Parent continuously integrates/verifies/advances, no routine confirmation.

## Bounded scope and execution boundary
Add a real multi-parent interface graph and abstract invokeinterface0xb9. Extend
reference assignability (including arrays) and the abstract-interface fallback
needed by invokevirtual class-method resolution. All parsing/linking/graph traversal,
dispatch/access checks/type operations/heap/Java execution remain inside ordinary
EVM bytecode. Host only packs unchanged raw classes/int arguments, invokes EVM,
decodes. No host parser/evaluator/heap/AOT/precompile/classpath/JRE fallback or
class-specific runtime. Trusted JVM/javac only build/oracle. No consensus changes.
Local runtime.Execute, not CREATE/mainnet deployment or full JVM/Java SE.

Keep root static(I...)I, existing value types/descriptors and all heap/frame/gas
limits, 960 historical cases/budgets. No new JavaException kinds (1..9 unchanged).
Interfaces may be types but cannot be object-new targets. Root entry must remain
an ordinary class: interface entry still LinkError5. Interface native/default/
private bodies, static interface invocation/fields, default-method selection and
required default-interface initialization are NOT implemented in this batch.
Defaults+initialization are M4f-b; static interface members M4f-c. Other primitives,
handlers, monitors, Object/JRE APIs and array-receiver dispatch remain deferred.

## Interface graph and conservative profile guard
Store direct interfaces from every class/interface classfile, not just a boolean
unsupported marker. Preserve ordered edges for future initialization semantics.
Ordinary superclass chain remains separate. Interfaces have java/lang/Object in
the classfile super_class slot, but that is NOT an interface-parent edge or an
instruction to initialize Object when initializing an interface. Validate class/
interface kinds, this/super/header shape, direct interface CP edges/names, access,
duplicates by resolved identity and cycles; diamonds/transitive sharing are valid.
A class superclass cannot be an interface (existing HierarchyError4). Preserve
annotation/enum/module and other unsupported header rejections; don't clear a
blanket unsupported flag and accidentally accept them.

Interface closure includes own parents and a class's inherited implementations
through every superclass. Graph/type checks are bounded by supplied+bootstrap
classes (at most67), not recursive/unbounded EVM stack. Missing edge target uses
LinkError4(owner class index detail); malformed/wrong-kind/duplicate edge or invalid
interface structural header InterfaceError(1,classIndex), cycle InterfaceError2,
inaccessible interface edge InterfaceError3. New error signature is
InterfaceError(uint256 code,uint256 location); graph locations are class indices.
Keep existing superclass errors and lazy unused-class validation conventions.

CRITICAL DEFAULT GUARD: validate reachable interface graph before initializing
an ordinary class or allocating it. Any non-static interface method other than
metadata-only public abstract/no-Code declarations is deferred InterfaceError4
(interface index). This includes default, private, native/synchronized instance
forms and synthetic default bridges. Do NOT silently ignore default semantics or
skip default-bearing interface initialization. Java8 interface covariant-return
bridges can have Code, so fixtures must inspect this rather than assume 'abstract
source interface' has no defaults. Class bridge methods remain supported.

Static interface method/<clinit> metadata and fields may be parsed without entry;
implementing/allocating a class with only abstract interfaces does not initialize
those interfaces, even if they have <clinit>. Calling an abstract interface method
does not initialize its declaring interface. Root interface/static entry remains
deferred; invokestatic InterfaceMethodref retains CallError1 rejection. A forged
Methodref10 targeting an interface static method must reject CallError4, not bypass
the deferral. Direct interface getstatic/putstatic rejects FieldError3. Inherited interface static-field
resolution is deferred (may retain missing FieldError2); do not fabricate values
or accidentally use class initialization rules to execute interface statics.

## Bootstrap marker interfaces and array types
Add trusted minimal raw classfiles for java/lang/Cloneable and java/io/Serializable.
Append after user classes when absent, like Object; never replace supplied bytes.
Preserve user indices and64 user-input limit; at most3 internal bootstrap slots.
Parse all bootstrap bytes through normal EVM parser, no host-side type shortcuts.
Keep Object constructor-only95 bytes. Build/check verifies source->javac->hex->
embedded bytes with bounded temp subprocesses before unchanged pinned solc.
Parent locally verified --release8 -g:none -Xlint:-options:
- `package java.lang; public interface Cloneable {}`:71 bytes,
  SHA07930c21cec8dfc8a031c04590af290511e2be6dbae7ad1282a2cfa00a06c457;
- `package java.io; public interface Serializable {}`:72 bytes,
  SHA90bd3c397ef8d1f81a72b59b80c6a96ac158ac9fc97c95851d246eff8e66a70a.
Supplied marker definitions must be interfaces before granting marker semantics;
invalid replacement kind rejects InterfaceError1. No serialization/clone service
or other Object methods are added. No host bootstrap loading.

Every supported array implements resolved canonical Cloneable/Serializable markers
in the EVM type system, in addition to Object. Ordinary objects implement only
interfaces from their validated class/interface closure (not all marker types).
Extend all existing fields/calls/returns/casts/instanceof/aastore/covariance paths.
Interface reference and interface-leaf arrays are now allowed, including anewarray
and multianewarray: no interface initialization/constructors. Non-implementing
valid object cast -> CCE8/test0, incompatible array element -> ASE9. Assignment
validation remains ReferenceError2 for valid incompatible class/interface types;
invalid handles/wrong element opcode heap kind remain ReferenceError1. Do NOT
classify a valid array vs interface as a wrong-heap-domain fault: return the normal
assignability result, so field/call assignment fails ReferenceError2 if incompatible.

Examples to cover: Child implements J extends I; Child[] -> I[]; int[] -> Cloneable
and Serializable; int[][] -> Cloneable[]; Object[] NOT Cloneable[]. Arbitrary
interface I is not implemented by an array merely because it is an interface.
Null casts/tests keep M4c structural-before-null/no-resolution shortcut, even for
well-formed missing/deferred targets. Non-null resolution never initializes types.
new interface still ObjectError2, interface arrays are valid. All array quotas,
rank bounds/noGC and uninitialized-object reference protections unchanged.

## invokeinterface and affected invokevirtual
Width5: opcode,u2 InterfaceMethodref11 index,u1 count,u1 zero. Validate count nonzero
and final byte zero; descriptor-supported category1 argument slots imply count
EXACTLY explicit argument count+receiver (<=255). Bad CP/tag/name/operands/count ->
CallError1; non-interface symbolic owner -> InterfaceError1(callPC); names <init>/
<clinit>, static/private/non-public resolved method, unsupported signature/access
-> CallError4. Validate symbolic resolution/access/shape/count before null.

JVMS8 5.4.3.4 interface resolution: own declaration, then public non-static method
from Object, then maximally-specific superinterface abstract declarations. With
all default Code rejected, multiple matching maximal abstract declarations may
resolve deterministically; no invented default conflict/ICCE implementation. Missing
method CallError3. Object fallback is a resolution rule, NOT a new Object API:
constructor-only bootstrap has no ordinary fallback methods. Supplied Object Code
can exercise the rule in Go tests; do not fake hashCode/equals/toString/clone.

Non-null ordinary receiver must implement symbolic interface transitively, otherwise
ReferenceError2. Null -> NPE6 after successful symbolic checks. Uninitialized or
numeric receiver/args -> BytecodeError14; invalid handle ReferenceError1. Actual
array receiver still CallError4 after successful symbolic/reference validation,
even for marker interfaces; no array dispatch/native service. For ordinary object,
select the public concrete instance method from its dynamic class/superclasses.
Implementation may be inherited from a superclass that itself doesn't declare
implements I. Enforce public access and existing exact typed arg/return/local0/
frame semantics. Missing implementation or selected abstract/native/synchronized/
static/private/inaccessible/no-supported-Code -> CallError4, not a new AME/native
claim. Static methods must not masquerade as instance implementations.

Preserve invokevirtual ordinary override relation/final/protected rules. ADD its
abstract-interface resolution fallback when symbolic CLASS and its superclass
chain have no declaration but reachable interface abstracts do: e.g. abstract
A implements I (no f declaration), B extends A implements public f, call A.f uses
invokevirtual and must dispatch B.f. Parent local Java21 probe returned7 and javap
confirmed invokevirtual A.f()I. Don't feed an interface owner into a class-only
superclass traversal. Use separate resolved declaration/qualifying class/interface
metadata and class implementation selection as needed. No default lookup yet.

Same CP sites with varying receiver classes, class bridges, inherited public methods
and both b6/b9 paths must not poison caches. Recheck opcode/count/access/receiver
conditions per use. Constructor callbacks after super may dispatch via interface
or abstract-class view to derived implementation/default field values. No synthetic
Java frame for graph walking;128 frame cap remains. Interface calls never trigger
interface/class initialization independently.

## Independent gates and staged compatibility
Append~80-110 trusted Java8 stage m4fa/defaultm4fa cases, schema1/kinds1..9 unchanged.
Preserve all prior960 fixture sources/entries/outcomes/budgets EXACTLY. Cover interface
inheritance/diamonds/multiple implementation/inherited superclass method, alternating
receiver class at one b9 site, abstract-class b6 fallback, public class bridges,
int/void/ref args/returns/recursion, fields and interface arrays/multidimensional
covariance, markers, casts/type tests/ASE/CCE/null, ctor callbacks and no interface
initialization (interfaces may have metadata <clinit> not invoked). Use only modest
trusted JVM oracles with finite heap/timeouts. No default bridges/static interface
calls or JRE APIs slipped in; inspect flags AND CP owners/count bytes.

Go verifier: graph kind/access/cycle/duplicate/missing edges, root and unsupported
header/default guards, marker bootstrap parsing, interface/array compatibility,
abstract b6/b9 dispatch/caches/access/count/zero byte/malformed/truncated/branches,
no implementation/selected unsupported bodies, Object fallback without invented
APIs, valid nonimplementor vs null/invalid/uninitialized refs, array dispatch deferral,
no interface init/constructors, caps/frames/outcome/OOG separation. Counterexamples
must isolate actual faults and use valid boundary-aware bytecode construction.

Old Go tests that intentionally rejected ALL interfaces now may be obsolete (e.g.
M4c object instanceof empty I, M4d I[] targets, header implements-interface tests).
Runtime worker reports exact input/old error/new supported behavior to parent,
DO NOT silently skip or weaken old tests. Parent explicitly updates obsolete
profile negatives to supported positive assertions or still-deferred cases with
justification. Other old tests and all960 fixture expectations/budgets stay.

Parent integrates runtime->fixtures->verifier, reviews bootstrap/graph/dispatch and
reported obsolete negatives, independently rebuilds/checks Go/CLI/Python960+oracle,
smoke/fast/demos/AOT/vet plus new probes. Accept last-green then freeze M4f-b
maximally-specific defaults WITH mandatory default-interface initialization.
Do not enable defaults without that ordering. No routine confirmation.

## Ownership / one monolithic writer
Runtime ONLY Solidity/runtimehex/build.js; new runtime/bootstrap/Cloneable.java,
Cloneable.class.hex,Serializable.java,Serializable.class.hex; jvmevm/jvmevm_test.go
EXPECTED HASH ONLY; new jvmevm/interfaces_test.go runtimeM4fa* helpers. Existing
Object source/hex, compiler settings/dependencies, host APIs/CLI/decoder/harness/
fixtures/old tests not owned. Report obsolete tests, don't edit them.
Fixtures ONLY jvmevm/testdata/differential/**; preserve960/schema1, append m4fa.
Baseline runner rejects new stage; use bounded fresh manual trusted JVM checks,
not harness edits/fake EVM-green claims.
Verifier ONLY tools/java_diff.py,tools/test_java_diff.py,tools/JAVA_DIFF.md,
new jvmevm/interfaces_validation_test.go verifyM4fa* helpers. Baseline red expected;
keep exact assertions and document actual failures (never blanket reverts).
Parent owns plans/AGENTS/quickstart/Makefile, approved profile-negative updates and
integration/independent review. No subagents/peer writes/push/global settings/
untrusted oracle runs. Sol/high WITHOUT Fast. Commit scoped files and honestly
report hash/size/bootstrap checks/results/known failures. No full-JVM claim.
