# M4e: bounded multianewarray allocation

Authority JAVA_EVM_PROGRAM.md. Last-green M4d073eecf:892 JVM/EVM cases plus48
parent probes,34 Python,381 smoke/401 fast and full focused gates. Runtime76800
bytes SHA79ab08d94ba5af8ece1560a7a95e0859844844474601215afae6f3bc8b51997f.
ALL NEW workers use openai-codex/gpt-5.6-sol, thinking high, WITHOUT Fast/priority.
Never pass --fast or enable its persisted preference. Parent continues staged
integration/verification automatically; user asleep is not a routine blocker.

## Scope and invariant
Add ONLY multianewarray0xc5 for the array types already supported by M4d: rank1..255
with ultimate leaf int or ordinary class/Object. It allocates one or multiple
levels in a single Java instruction, including partial rank. All CP/type/access
resolution, count validation/planning, allocation, defaults, linking of subarrays
and outcomes happen INSIDE ordinary EVM bytecode. No host parser/evaluator/heap/
AOT/precompile/classpath fallback, no class-specific runtime/consensus changes.
Host packages raw unchanged classfiles/int root args and decodes EVM results.
Trusted javac/JVM only build/oracle. Bootstrap Object95-byte image unchanged,
parsed and constructor interpreted in EVM; no JRE APIs or native services.

Root remains static(I...)I. Preserve all descriptors, heap/ref types, covariance,
field/call/return checks, initialization/constructor lifecycle and previous opcodes.
No interfaces, other primitive leaves, monitors, handlers, strings/class literals,
array-receiver virtual dispatch or numeric-value expansion. Local runtime.Execute
only, not CREATE/mainnet deployment. No full JVM/Java SE claim.

## Instruction and exact validation order
Width4: opcode, u2 CONSTANT_Class index, u1 dimensions. Operand type must be an
ARRAY descriptor rank1..255, not an ordinary class name. dimensions in1..rank.
Keep exact predecode truncation and branch-target boundaries for all three operand
bytes. Structural malformed Class index/tag/name/array-rank remains TypeError1.
A structurally valid non-array target, dimensions0, or dimensions>rank is new
ArrayError(3,pc). Do not silently reinterpret operands as anewarray/newarray.

Order (isolate test faults, no full dataflow verifier claimed):
1 structural CP/type/rank and dimensions validation;
2 resolve ultimate component/access/supported hierarchy WITHOUT initialization;
   missing class LinkError4(pc), inaccessible/interface/deferred primitive leaf
   TypeError2, other unsupported hierarchy/header errors unchanged;
3 require dimensions category-1 int stack values, otherwise underflow Bytecode3
   or kind/uninitialized mismatch Bytecode14;
4 validate ALL signed counts for negativity before ANY allocation/cap check;
   any negative -> Java NegativeArraySizeException4, even after an earlier zero
   dimension, or when an earlier positive count exceeds an implementation cap;
5 preflight resource requirements for ONLY materialized levels;
6 allocate and push the outer array reference, consuming exactly dimensions counts
   and preserving any operand-stack prefix. No new Java method frame is created.

Counts are ordered as written in Java: deepest specified count at stack top,
outermost at stack[sp-dimensions]. Keep int32 interpretation; no unsigned wrap or
Solidity overflow panic. Component resolution precedes counts even for all-zero
or negative counts. Abstract ordinary components are valid (no instantiability
check); component constructors and class initializers NEVER run from allocation.
Prior review checked these rules with bounded local JVM probes and JVMS6.5.

## Shapes, defaults, identity
Example new int[2][3]: outer rank2 reference array length2; two DISTINCT rank1 int
arrays length3, all int elements0. new Node[2][3]: outer rank2 ref array, two rank1
Node[] arrays with NULL slots, no Node instances/ctors. new int[2][3][] (rank3,
dimensions2): outer rank3 array, two rank2 arrays length3 whose elements remain
null; no rank1 rows allocated. Dimension1 is legal even if javac normally emits
anewarray/newarray instead; test it with controlled bytecode construction.

Zero count stops allocation of deeper levels, NOT validation of later negative
counts. new int[2][0][5] creates outer plus TWO distinct empty rank2 arrays, no
deeper arrays. new int[0][hugePositive] creates ONE empty outer array and must not
reject hugePositive against a per-array limit because that level is never created.
new int[0][-1] still throws NASE. Full rank255/counts all1 must remain bounded and
work within existing caps/gas; no recursive Solidity/native stack exhaustion.

Type metadata at each created node must match its actual remaining rank/leaf;
reuse M4d covariance/arraylength/element access, checked casts/type tests and
ArrayStoreException rules. Distinct subarrays stay distinct until guest aliasing
explicitly changes them. Nested references survive calls/field/static storage.
No identity leakage to host; initialized reference tags only, no forged handles.

## Resource planning and allocation
Same shared limits:1024 total int/ref arrays;65536 elements per MATERIALIZED array;
262144 total elements across all array kinds; objects remain independent1024
objects/1024 fields each/65536 total object slots. No GC, unreachable allocations
still count. Shared handles bound2048, fresh invocation resets heap/statics.
multianewarray creates NO ordinary objects and consumes NO object-field quota.

Precompute bounded array count/element totals before allocation, using remaining
quotas and overflow-safe arithmetic. At level0 one array is needed; level j has
product(counts[0..j-1]) arrays of length counts[j]. Accumulate only while this
multiplicity is nonzero and j<dimensions. Check multiplication against remaining
quotas BEFORE multiplying; don't loop huge counts or overflow uint256. All negative
counts already checked. Any per-array/count/element cap excess -> Java OOM7,
not EVM OOG/validation. Example [1023][0] uses1024 arrays/1023 elements, whereas
[1024][0] exceeds array quota. Earlier allocations reduce both remaining quotas.

Allocate iteratively with bounded work/queue/level counters, not recursion tied
to rank or a synthetic Java frame per level. Charge each actual array and slot
exactly once, preserve allocation-type metadata and normal shared handle validity.
Budget planning may fail before any allocation; no guest code executes during it.
Retain finite gas/time bounds; logical caps never promise gas sufficiency. Existing
Go-only resource tests may use250M if measured necessary; don't increase prior
fixture/test budgets without parent review. Never exhaust host JVM memory.

## Outcomes and tests
No new Java kinds:1..9 unchanged. Negative4 escaping active <clinit> wraps EIIE3;
OOM7/StackOverflow2 remain Errors; EVM OOG is not Java OOM. All existing exact
Go/CLI/Python decoding/schema1/root/value-or-exception protocols remain unchanged.
No production host API/decoder modifications needed.

Append~50-80 trusted Java8 m4e cases, preserving prior892 source files, manifest
entries/expected outcomes/budgets EXACTLY. Cover rectangular/jagged-by-mutation
int/reference arrays, defaults/dimensions/alias/identity, zero outer/inner, partial
ranks, nested covariance/casts/ASE, static/instance fields and static/special/virtual
helper args/returns, no component init/ctors and abstract components, initializer
allocation/order, ordinary negative counts and EIIE. Keep oracle sizes modest,
finite heap/timeouts; huge quotas/rank mutations are focused Go-only where needed.
Inspect actual multianewarray operands/owners, no accidental interfaces/JRE calls.

Independent Go verifier: rank/dimensions boundaries including controlled dimension1
and255, malformed CP/names/operands/branch targets, non-array target, insufficient
stack/int-ref confusion/exact PC; ordering missing/access before negative, ALL
negatives before caps despite zero/huge positives; unmaterialized large counts
allowed, per-array/count/element shared caps and preexisting arrays/objects/noGC/
reset; distinct empty child identities and partial-rank nulls; no initialization;
Java NASE/EIIE/OOM vs EVM OOG. Derive instruction PCs with valid boundaries and
verify handcrafted stack flows, not arbitrary raw-byte scans through operands.

Parent integrates runtime->fixtures->verifier; independently reruns artifact/
bootstrap, focused Go/CLI/Python,892+ full oracle, smoke/fast/demos/AOT/vet plus
new probes. Fix real defects/test isolation, don't weaken semantic assertions.
Accept last-green then freeze next bounded interface stage after review, continuing
automatically. No routine confirmation or full-JVM/deployment claims.

## Isolated ownership
Runtime ONLY jvmevm/runtime/JVMSubsetInterpreter.sol + runtime.hex;
jvmevm/jvmevm_test.go EXPECTED HASH ONLY; new jvmevm/multidimensional_test.go
runtimeM4e* helpers. No host/decoder/CLI/bootstrap/build/compiler/harness/fixtures/
other old-test edits; report any genuinely obsolete negative to parent.
Fixtures ONLY jvmevm/testdata/differential/**, stage m4e, preserve892/root protocol.
Baseline runner rejects new stage until integration: bounded fresh manual trusted
JVM checks are fine; no harness edits or fake EVM-green claim.
Verifier ONLY tools/java_diff.py, tools/test_java_diff.py, tools/JAVA_DIFF.md,
new jvmevm/multidimensional_validation_test.go verifyM4e* helpers. Baseline red
expected; preserve exact tests and report them, never weaken to pass old runtime.
Parent owns plans/AGENTS/quickstart/Makefile and integration/independent review.
One Solidity writer, no subagent spawning/peer writes/push/global config/untrusted
oracle runs. Keep Sol/high WITHOUT Fast, commit only owned paths and report real
checks/SHA/size/limits/failures honestly.
