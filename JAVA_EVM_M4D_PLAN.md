# M4d: reference arrays and recursive array assignability

Authority JAVA_EVM_PROGRAM.md; last-green M4c d7fc98f:792 fixed JVM/EVM cases,
48 parent probes,34 Python tests,331 smoke/351 fast and all focused gates.
Runtime74469 bytes SHA1e5736e346cea2c55a2aed3963822a1bf9be66eb57c0031b4c64603d64f5c941.
Sol/high with inherited enabled Fast preference; backend priority not guaranteed.
Parent integrates/verifies/advances automatically, no routine confirmation.

## Scope/boundary
Add anewarray0xbd, aaload0x32, aastore0x53. Extend arraylength, reference descriptors,
assignment and checkcast/instanceof to reference arrays and nested array references.
All type/CP resolution, allocation/defaults, heap operations, covariance and Java
outcomes execute inside ordinary EVM bytecode. Host only packages unchanged raw
classes/int root args, invokes EVM and decodes. No host parser/evaluator/heap,
AOT, native precompile, filesystem/JRE fallback, class-specific runtime or
consensus change. Trusted Java/JVM only as build/oracle. Local runtime.Execute,
not CREATE/mainnet deployment (artifact already over EIP-170).

multianewarray0xc5 is EXCLUDED, next separate stage. Interfaces, other primitive
arrays/types, handlers, monitors, strings/class literals, broader Object/JRE APIs
remain deferred. Object constructor-only95-byte bootstrap stays unchanged and is
parsed/executed in EVM. No array-receiver virtual dispatch: retain CallError4
ordering after successful symbolic resolution and valid reference checks for BOTH
int/reference array receivers; missing Object API still CallError3.

Supported descriptors: I plus ordinary Lclass; and arrays whose ultimate leaf is
I or supported ordinary Lclass;, rank1..255; V only returns. Thus [I, [LBox;,
[[I, [[LBox; etc are supported reference values, with Object as common supertype.
No array classfiles/host class creation needed: array type metadata is constructed
inside EVM. Root stays static(I...)I, reference roots MethodError11. Internal
static/special/virtual calls and fields accept new refs with exact type checks.
Preserve all M4b/M4c initialization, constructor tokens, access/finals/caches and
resource rules. No uninitialized object token may be stored as an array element.

## Allocation/type resolution
anewarray has width3 and CONSTANT_Class operand denoting the COMPONENT type:
ordinary class name p/Box gives [Lp/Box;, [I gives [[I, [Lp/Box; gives [[Lp/Box;.
Resolve component/ultimate leaf/access/hierarchy BEFORE negative length/cap checks,
even if length is zero. Missing named class LinkError4(pc); no phantom class.
DO NOT initialize component classes or invoke component constructors. Abstract
ordinary classes ARE valid component types: don't reuse new's instantiability
check. Arrays contain null element references initially; no nested arrays are allocated automatically.
Nested arrays are built by repeated anewarray/newarray and stores. A fresh
allocation has distinct identity, including zero-length arrays.

Parent bounded Java21/--release8 probe confirmed: new Component[0]/[1] does not run
Component.<clinit>; with missing Component, lengths-1/0/1 all fail JVM class loading
BEFORE NegativeArraySizeException. Present negative length gives NASE4. Our missing
class outcome remains LinkError4, not a new NoClassDefFoundError taxonomy.

Structural Class operand/name validation reuses TypeError1 (CP/tag/name/array rank
malformed). Existing array names can have at most255 dimensions. A valid component
array of rank255 would produce rank256: reject ArrayError2(pc), even length0; rank254
component producing rank255 is allowed. Inaccessible/interface/unsupported primitive
array component target uses TypeError2; unsupported ordinary hierarchy/header shapes
retain existing errors. Null fast paths of casts still skip well-formed missing/
deferred target resolution, but anewarray always resolves its component.

Negative length Java4 before positive logical resource caps, after component
resolution. All existing limits unchanged:1024 TOTAL arrays (int+reference combined),
65536 elements per array,262144 TOTAL allocated elements across BOTH array kinds.
Objects retain separate1024 count/1024 fields each/65536 total slots. Shared unforgeable
handle namespace, no GC; unreachable arrays/elements count until invocation ends.
Limit excess OOM7; reset each invocation. Finite Go-only capacity probes may use
250M as already frozen if measured necessary; never host-JVM OOM exhaustion or
unreviewed budget increases. Keep physical representation efficient; reference
array cells may store raw handles and aaload pack their kind, avoiding pointless
per-element tagged-null initialization, provided all observable typing is exact.

## Loads/stores/length and covariance
arraylength accepts either array kind. iaload/iastore still require int[];
aaload/aastore require an array with reference component (ordinary object or
array). Wrong operation heap kind is ReferenceError1; never treat handles as
integer elements or objects as arrays. Bytecode stack/slot kind checks remain14.
Valid reference consumers reject uninitialized tokens. Invalid handles remain
unforgeable/ReferenceError1; don't bypass guards just to manufacture a test.

aaload pops array/index and returns exact element ref (including null); aliases
share updates across locals/fields/statics/calls/returns. aastore pops array/index/
value, verifies initialized reference and validity, then for well-typed values:
1 null receiver -> NPE6;
2 index negative/out of bounds -> Bounds5;
3 non-null element incompatible with ACTUAL array component type -> ArrayStore9;
4 otherwise store exact reference; null is compatible with any ref component.
No component initialization during accesses/assignment. Parent JVM probe confirmed
out-of-bounds beats incompatible-store exception. Null receiver precedes bounds.
Malformed-slot failures may precede Java checks; isolate negative tests to one defect.

Reference assignability is recursive/covariant, not equal descriptor only:
- Child[] -> Base[] -> Object[] -> Object; Child[][] -> Base[][];
- int[] -> Object but NOT Object[];
- int[][] -> Object[] (each int[] is Object), but NOT Object[][];
- equal int[] leaf types match; other primitive leaves remain deferred;
- unrelated ordinary component classes are incompatible; dimensions and primitive
  vs reference components must be respected. Null matches every supported ref.
Rank bound255 must not cause unbounded Solidity/EVM recursion; prefer bounded
iterative type comparison/normalization and test the structural boundary.

Use actual immutable allocation type metadata for stores, not the widened local/
field/method declaration: Object[] a=new Child[1]; a[0]=new Base() throws ArrayStore9.
checkcast/instanceof on valid refs use the same covariance but return preserved
identity/CCE8 or int1/0, not validation error for an ordinary type incompatibility.
Resolve non-null target without class initialization; null shortcuts unchanged.

Ordinary field/argument/return assignment failures remain validation, not ASE/CCE:
ReferenceError2 for incompatible component/rank/class within valid ref types.
Preserve M4b ReferenceError1 for object-vs-array heap-domain misuse (except Object
supertype accepts every array), and ReferenceError1 for wrong opcode heap kind.
Thus different valid ARRAY types assigned to each other fail ReferenceError2;
int/ref array kind distinction only determines which element opcode is legal.
Final reference fields allow element mutation, not rebinding; typed reference
arrays may be transported through Object and checked back without losing identity.

## Outcomes/ABI and malformed inputs
Add ONLY JavaException9 java.lang.ArrayStoreException and exact canonical Go/CLI/
Python decoding. Non-Error9 escaping <clinit> wraps EIIE3; kinds1..8 unchanged,
Errors2/7 unwrapped, EVM OOG never Java OOM. Unknown/noncanonical payloads remain
errors. Schema1/root result-or-exception protocol unchanged, no host references.
Existing ArrayError1 unsupported newarray atype; new ArrayError2 rank overflow
from valid anewarray component. TypeError1 malformed Class operand/name,2 deferred/
inaccessible component target; missing class LinkError4. Preserve existing precise
predecode truncation/branch errors and field/method descriptor errors. No whole-JVM
verification or linkage-error taxonomy claimed.

## Fixtures/verifier/gates
Append~80-110 trusted Java8 cases stage m4d/defaultm4d. Preserve prior792 sources,
manifest entries/outcomes/budgets EXACTLY. Finite fresh JVM oracle processes.
Cover defaults/zero-length/identity/aliasing, same/crossclass components, ref locals/
static/instance/final fields, static/special/virtual helper arguments/returns,
Object[] heterogeneous values and int[] elements, covariant class arrays/nested
arrays, manually assembled matrices via new int[n][] then rows (NO multianewarray),
recursive casts/instanceof, no component initialization, classinit reference-array
allocation/reentrancy, null/bounds/store failures and ASE/EIIE. No implicit JRE calls
or constant-final folding surprises; inspect CP owners and emitted selected code.

Independent Go verifier: exact malformed anewarray CP/names/rank/operands/branches;
missing-component negative/zero/positive ordering; component no-init; rank254->255
and255->256; numeric/ref/uninitialized confusion; wrong heap operations; actual
component covariance and null/bounds/store order; per-use call/field/return typing;
int/ref shared caps vs independent object caps/noGC/reset; CCE/ASE/EIIE/OOG and
exact decoder. No weakened assertions or forged host heap/unknown revert success.

Parent integrates runtime->fixtures->verifier, inspects scoped changes, reruns
pinned artifact/bootstrap, focused Go/CLI/Python,792+ oracle, smoke/fast/demos/AOT/vet
and new independent probes. Fix actual failures, not budgets/expectations. Accept
last-green then freeze M4e multianewarray with explicit rank/count/zero/negative/
aggregate-allocation ordering; interfaces follow separately. No routine confirmation.

## Ownership / one Solidity writer
Runtime ONLY Solidity/runtimehex; jvmevm/jvmevm.go decoder only;
jvmevm/jvmevm_test.go expected hash only; jvmevm/integer_test.go decoder tests only;
new jvmevm/reference_arrays_test.go runtimeM4d* helpers. No bootstrap/build/compiler,
CLI/fixture/harness/other old-test edits; report genuinely obsolete tests to parent.
Fixtures ONLY jvmevm/testdata/differential/**; stage m4d, preserve792, root protocol
unchanged. Baseline runner rejects new stage until integration: use bounded manual
trusted JVM checks if needed, no fake EVM-green claim or harness edits.
Verifier ONLY tools/java_diff.py, tools/test_java_diff.py, tools/JAVA_DIFF.md,
new jvmevm/reference_arrays_validation_test.go verifyM4d* helpers. Baseline M4c
expected red; preserve exact tests and report failure map, not weakened assertions.
Parent owns plans/AGENTS/quickstart/Makefile, integration and independent review.
No worker spawning, peer writes, remote pushes, global settings or untrusted Java.
Work only assigned tree, commit owned paths, report real checks/hash/size/limits.
