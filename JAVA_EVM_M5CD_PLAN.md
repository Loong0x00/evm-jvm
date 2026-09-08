# M5c-d: IEEE float/double arrays

Authority JAVA_EVM_PROGRAM.md; last-green M5c-c6e5fb6d:1971 oracle cases plus960
parent probes,36 Python,864 smoke/884 fast and focused gates. Runtime136564 bytes
SHAb59cf3ff60ed775d21c6344eb832770e980d397721398a70fa1cf3037ba91069.
All NEW agents Sol/high WITHOUT Fast/priority; never --fast or re-enable preference.
Named make java-fast is only a fixture tier. Parent continuously integrates and
independently verifies bounded stages, no routine confirmation.

## Scope/invariant
Enable newarray atypes6 F/7 D, faload30/daload31/fastore51/dastore52, [F/[D and
nested F/D leaves through all existing type/heap/call/field/array operations.
All parsing/type metadata/allocation/raw-cell transport/bytecodes/outcomes remain
INSIDE ordinary EVM bytecode. Host only packages unchanged raw classes/int root
args, invokes EVM and decodes. No host parser/evaluator/heap/floating math/AOT/
precompile/JRE fallback or consensus changes. Trusted javac/JVM only build/oracle.
Local runtime.Execute, not deployment/full JVM. Preserve1971 fixture sources/
entries/outcomes/budgets, root exact(I...)I, all previous operations, limits and
five bootstrap images. No new native bindings beyond the four exact raw-bit APIs.
No new JavaException kinds (1..11/schema1 unchanged). Handlers/monitors/jsr/ret,
boxing/Math/Object/JRE expansion remain deferred.

## Raw cells and default values
Float array cells are exact32-bit encodings, double cells exact64-bit encodings.
Default elements POSITIVE zero bits. Pure load/store/copy preserves signed zero,
subnormals, infinities and NaN sign/payload; do NOT route array transport through
arithmetic canonical-NaN packers or numeric conversions. EVM raw signaling-NaN
transport guarantee retained, with cross-JVM portability caveat (some JVM paths
may quiet signaling NaNs). Quiet-NaN/finite/signed-zero transport bit-exact oracle;
EVM-only signaling cases explicitly labeled. Array transport never canonicalizes
merely because a payload is NaN.

Use safely discriminated uint32/uint64 cell tables or equivalent. Reusing J's64-bit
storage for D is fine only with immutable distinct primitive leaf identities and
correct opcode guards. No long/double or int/float reinterpretation except explicit
approved native bit APIs. Test first-allocation F/D/J/ref/object in different
orders; all backing tables and shared handles valid regardless first kind.

## Instructions and category rules
newarray6/7 use signed int count, existing negative-before-cap and no initialization
rules. faload/daload consume array ref + int index, return one F(category1) or
D(category2) value. fastore consumes ref/index/F (3 words); dastore consumes ref/
index/D (4 words,3 logical values). Preserve stack prefixes, max_stack WORD bounds,
whole-value categories, call/local overlap rules and exact kind checks. [F/[D are
category1 REFERENCES for fields/calls/b9 counts, while scalar D is category2.

Require actual rank1 primitive F for F element opcodes, D for D; wrong array/rank/
object/opcode domain ReferenceError1, wrong I/J/F/D/ref/uninitialized operands
Bytecode14, missing logical operands Bytecode3, output word capacity Bytecode9.
Never accept iaload int operations on F, laload on D, or aaload on primitive rank1.
For already-computed valid operands: null array NPE6 before bounds, invalid signed
index Bounds5, otherwise raw load/store. Operand expressions execute BEFORE opcode:
an integer/long division in a store value computation can throw Arithmetic1 before
a null receiver check; FP divide-by-zero instead produces a value as M5cc specifies.

No implicit field-like narrowing or numeric FP conversion at array stores; input
kind already F or D. Array element assignments/increments/compound operations use
normal software IEEE arithmetic followed by raw store. fneg/dneg payload sign-flip
and conversion/generated-NaN policy remain separate from array transport.

## Types, covariance, nested allocation and quotas
Extend primitive leaf identity with distinct F and D alongside I/J/Z/B/C/S. [F/[D
and nested ranks supported in descriptors, fields, returns, all call modes,
anewarray components, multianewarray, casts/type tests and reference-array stores.
All primitive types are now supported; invalid atypes (e.g0/3/12) still ArrayError1.
Invalid array descriptors (e.g[V, rank>255) retain TypeError1, no invented primitive.

Every F/D array is Object/Cloneable/Serializable plus canonical marker superinterface
closure. Primitive arrays invariant: float[] != int[], double[] != long[]/float[].
float[][] -> Object[]/Cloneable[], but NOT double[][]; exact leaf/rank required
when target primitive leaf. Valid cast mismatch CCE8, instanceof0; storing double[]
into Object[] view of float[][] -> ASE9; compatible float[]/null succeeds. Field/
argument/return mismatch remains existing Reference2/domain validation distinctions.
Final array refs allow element mutation, not illicit rebinding. No new array receiver
virtual/interface dispatch; existing CallError4 after symbolic/ref checks stays.

Nested/rank255/newarray/anewarray/multianewarray preserve partial shapes, distinct
empty children, all-negative-count-before-caps, missing component/rank/access rules,
zero stopping deeper allocation and no component initialization. Primitive FP
leaves have no class initializer. Per-array immutable type metadata must survive
aliases/static/instance fields/calls/returns.

ALL array types share1024 total arrays,65536 elements each,262144 TOTAL Java ARRAY
ELEMENTS. Double counts ONE element, not two stack words/eight bytes. Objects keep
independent1024 count/1024 fields each/65536 total slots; array fields one ref slot.
No GC; unreachable allocations count; fresh invocation resets state. Full-width
storage must not alter quotas or cause integer overflow in multiarray preflight.
Logical OOM7 distinct from EVM OOG; fixed finite Go cap probes may use250M as before,
no old-budget increases without parent review, no host JVM memory exhaustion.

## Outcomes, fixtures and independent gates
No new exception kinds or API output changes. NASE/Bounds/NPE/ASE/CCE and Java
initializer wrapping/Errors/OOG remain as before; all raw bits operate inside EVM.
Append~90-120 trusted Java8 m5cd cases, preserve1971. Int roots accept raw bits/
hi-lo words and return exact raw32 or separate64-bit words; use only four approved
native raw-bit APIs. Cover every special/raw class (quiet NaNs cross-JVM), default
+zero/negative zero, load/store/copy/full-width/postinc/compound category forms,
all calls incl default/interface statics/ctors, fields/final/static initialization,
nested/multiarray covariance/markers/casts/ASE, null/bounds/negative/allocation
order/evaluation and initializer failures. Include arithmetic using arrays without
normalizing away transport payload or finite/signed-zero arithmetic mismatches.
Generated arithmetic NaN-only normalization may be used as M5cc; raw transport
comparison must NOT normalize quiet NaN payload. No boxing/JRE/Math/FMA/handlers.
Fresh bounded Java8/current JVM oracles and exact emitted Code/CP/type sets.

Independent Go exact raw32/64 cells and signaling-NaN EVM-only guarantee, F/D vsI/J
kind/array identity, wrong rank/opcode, category2 word depth/call count/prefix and
local/return handling, malformed atype/operand/branch/descriptor, all type paths/
rank255/multiane/marker closure/ASE/null/bounds/evaluation order, first allocation
kinds, shared quotas one-double-one-element/object independence/noGC/reset/OOG,
canonical generated NaN versus raw transport. Finite/zero/infinity/quiet payloads
bit-exact against JVM; never broad-normalize. Keep focused simple-access probes
<=20M gas and shared quota cases<=250M with measured gas before acceptance.

Old FP-array rejection probes are now obsolete: report exact cases/new supported
behavior to parent; parent explicitly updates while retaining invalid atypes,
unknown natives, wrong kind/rank/opcodes/access/final guards. No unauthorized old
fixture/budget/test changes or blanket revert success. Parent integrates runtime->
fixtures->verifier, independently checks pinned artifact/5bootstraps, Go/CLI/Python
1971+oracle/smoke/fast/demos/AOT/vet plus probes. Accept last-green, then freeze
bounded exception/unwind foundation separately; no routine confirmation/full-JVM
or deployment claims.

## Ownership
Runtime ONLY Solidity/runtimehex;jvmevm/jvmevm_test.go HASH ONLY;
new jvmevm/ieee_arrays_test.go runtimeM5cd* helpers. No bootstrap/build/compiler/
host/API/decoder/CLI/harness/fixtures/other old-test edits; report obsolete guards.
Fixtures ONLY differential/** stage m5cd preserve1971/schema1/kinds1..11; baseline
stage rejection permits bounded manual trusted oracles, no harness edits/fakegreen.
Verifier ONLY tools/java_diff.py,tools/test_java_diff.py,tools/JAVA_DIFF.md,new
jvmevm/ieee_arrays_validation_test.go verifyM5cd* helpers; baseline red expected.
Parent owns plans/AGENTS/quickstart/Makefile/integration/approved profile updates.
One Solidity writer; no spawning/peer writes/push/global settings/untrusted Java.
All agents Sol/high WITHOUT Fast; honest scoped commits/SHA/size/checks/caveats.

## Accepted integration evidence
Runtime1a53d30→be1b23b,fixtures04698c5→cafe22f,verifierf14af6c→7f6eaec.
Reviewc6950f8→49cd899 updated7 obsolete FP-array guard groups, retained invalid
atypes0/3/12/255/unknownnative/wrongkind/rank/CP/final/root checks, and added double
local-overlap/store-operand-order regressions. No runtime defect demonstrated.
Parent final artifact/5bootstraps, Go/CLI,36 Python,2091 full,945 smoke,965 fast,
demos,AOT,focused vet and192 raw-array probes passed:
`build/java-diff-parent-m5cd/probe-h0q_rbce/results-final/`.
Prior1971 fixture entries/budgets unchanged. Runtime135652 bytes SHA256
`cf68495083ebcd2df93f6d676e16afad87192a3401bd743a0301d805d5a8cd15`.
Quiet payloads/signedzero exact; signaling NaNs remain EVM-only portability case.
Next implicit-exceptions-first handler/unwind foundation; preflight architecture/
JVM oracles before freezing scope. All agents NO Fast, no full-JVM claim.
