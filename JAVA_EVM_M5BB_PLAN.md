# M5b-b: long arrays and full-width element storage

Authority JAVA_EVM_PROGRAM.md; last-green M5b-a dfd02bb:1493 fixed oracle cases,
48 parent probes,36 Python,682 smoke/702 fast and focused gates. Runtime113189
bytes SHA2d450f86e4245488fe2f73eb19338b8f2ac5423c3981bb6be99b397ab9096999.
All NEW agents Sol/high WITHOUT Fast/priority; never --fast/re-enable preference.
make java-fast is only a fixture tier, NOT agent priority, and remains allowed.
Parent continuously integrates/independently verifies/advances bounded stages.

## Scope and execution invariant
Enable newarray atype11, laload0x2f,lastore0x50, [J and nested long-array types.
All raw-class parsing/type metadata/64-bit heap storage/bytecodes/calls/init/errors
remain INSIDE ordinary EVM bytecode. Host only packages unchanged classes/int root
args, invokes EVM and decodes. No host parser/evaluator/heap/AOT/precompile/classpath/
JRE fallback or consensus changes. Trusted javac/JVM only build/oracle. Local
runtime.Execute, not mainnet deployment/full JVM. Preserve1493 fixture sources,
entries/outcomes/budgets, existing class/heap/frame limits and three bootstraps.

Root ABI still EXACT static(I...)I; J and [J roots MethodError11. Arrays are
category1 references even if leaf long: [J parameter consumes ONE word, J consumes
TWO. Internal fields/args/returns of [J/nested J now supported across static/special/
virtual/interface/default calls and initialization. Existing scalar long/primitive/
reference behavior unchanged. Float/double/F/D arrays, IEEE, handlers, monitors,
wide/switch, new Object APIs and array receiver dispatch remain deferred. No new
JavaException kinds (1..11/schema1/value-or-exception protocol unchanged).

## Heap and loads/stores
Store every long element as exact64 bits, NOT current uint32 truncation. A separate
uint64 cell array table or equivalently safe discriminated full-width representation
is allowed. Keep non-long cells/handles safe; don't broaden reference forging or
reinterpret other primitives as long. Ensure every heap table exists regardless
of FIRST allocation kind: object→int/ref→long and long→object/ref mixtures work.
Shared unforgeable handle namespace and immutable actual allocation type metadata.

newarray11 creates rank1 long array, zero64 default cells, distinct identities even
length0. laload consumes reference/index (category1 ints for index), produces one
indivisible long/two JVM words. lastore consumes reference/index/whole long (four
JVM words, three logical values). Preserve operand prefix and M5ba word-depth
max_stack1024/call/local rules. One logical long must not be mistaken for two
independent stack values. Arithmetic on loaded elements preserves full64 bits.

Require actual rank1 primitive LONG for laload/lastore. Other arrays/ranks/object
heap misuse -> ReferenceError1. Wrong int/ref/uninitialized/index/element kind ->
Bytecode14; missing operands Bytecode3, word capacity Bytecode9. For fully formed,
well-typed operands, null array -> NPE6 before bounds; invalid index -> Bounds5;
otherwise load/store. Source operand expressions execute BEFORE the array opcode,
so a dividing-zero value expression may throw Arithmetic1 before a null store
receiver is checked. Don't misstate that source-evaluation order as store order.

iaload/iastore must reject long[], laload/lastore must reject int[]/other primitive
arrays and long[][] (reference components). aaload/aastore operate on long[][] etc,
not rank1 long[]. Reference tag remains separate from long bits, including zero.
All existing M5ba category2 permutation/local/call/return safety must remain exact.

## Types, nested arrays and quotas
Add explicit primitive LONG identity distinct from I/Z/B/C/S and references.
Enable supported [J/nested J descriptors in fields/calls/returns, anewarray component
resolution, multianewarray allocation and checkcast/instanceof. Preserve structural
rank255 and result-rank overflow; full/partial rank shapes/default null subarrays,
zero/negative count ordering and iterative quota planning as M4e. No component
class initialization is associated with a primitive leaf.

long[] is Object/Cloneable/Serializable and marker-superinterface compatible;
long[][] -> Object[]/Cloneable[]; long[] NOT Object[]; long[][] NOT int[][].
Unlike primitive leaves are incompatible. Valid checkcast mismatch CCE8/test0;
Object[] view of long[][] storing int[] triggers ASE9; storing long[] succeeds.
Typed field/argument/return assignment mismatch stays Reference2 (existing domain
misuse distinctions unchanged). Final array refs allow element mutation, not
rebinding outside proper initializer. [J call parameter counts1, not2, in b9 too.

Shared quotas UNCHANGED:1024 TOTAL arrays across all types,65536 elements per
array,262144 aggregate Java ARRAY ELEMENTS. A long counts ONE element, not two
stack words or bytes. Objects keep independent1024 count/1024 fields each/65536
field slots; [J object field is one reference field slot. No GC; unreachable
allocations count, fresh invocation resets heap/statics. Long/int/ref interleaving
must share correct totals/handles. Logical OOM7 distinct from EVM OOG; existing
finite Go-only cap budget250M if measured necessary, never raise old budgets
without parent review or deliberately exhaust host JVM memory.

## Outcomes and coverage
NASE4/Bounds5/NPE6/ASE9/CCE8/arithmetic1 and initializer wrapping unchanged;
Errors2/7/10/11 unwrapped; unknown/noncanonical decoding unchanged. Pinned compiler/
bootstrap checks stay; no host/API/decoder change needed. Descriptor/atype/branch
malformations retain exact existing Array/Type/Bytecode errors. At newarray,
unsupported6(float)/7(double) remain ArrayError1; [F/[D non-null targets stay Type2.

Append~70-100 trusted Java8 m5bb cases, preserve1493. Int roots fold high/low bits
or compare to expose long-array values. Cover0/MIN/MAX/high-bit patterns, signed
sum/search/small sort, aliases/distinct/default/zero length, post/preincrements and
compound assignments producing category2 permutations, scalar/array mixed args
and all invocation modes, static/instance/interface/final fields, init reentrancy/
failures, long[][]/higher partial/full arrays, covariance/markers/casts/stores and
null/bounds/NASE/ASE/CCE/arithmetic. All fresh JVM inputs modest, finite heap/time,
no long root, no float/double/boxing/JRE/native/sync surprises; inspect javap.

Go independent tests full64-bit cells vs truncation, wrong opcode/array rank/type,
category2 stack shape/word capacity/return/call offsets/b9 [J vs J counts, malformed
operands/branch targets, null-before-bounds with valid computed operands and source
value-evaluation precedence, interleaved first allocation kinds, rank255/array
identity/typed descriptor paths, shared cap boundaries with one-long-one-element/
objects independent/noGC/reset, OOM vs OOG, initializer Error/wrapping. Trusted
bounded Java8 probes for valid cases, invalid forms EVM validation not full-verifier
claims. Derive exact PCs at instruction boundaries; don't blanket accept reverts.

Old [J/atype11/laload/lastore blanket negatives now obsolete: report exact cases
and justified new behavior, parent explicitly updates while keeping F/D and genuine
wrong-kind/operand/access/final guards. No old fixtures/budgets changed. Parent
integrates runtime->fixtures->verifier and independently checks artifact/3bootstraps,
Go/CLI/Python1493+fulloracle/smoke/fast/demos/AOT/vet+probes. Accept last-green then
freeze next bounded IEEE/value/exception stage after evidence review, no routine
confirmation/full-JVM/deployment claims.

## Ownership
Runtime ONLY Solidity/runtimehex; jvmevm/jvmevm_test.go expected HASH ONLY;
new jvmevm/long_arrays_test.go runtimeM5bb* helpers. No host/API/decoder/CLI/
bootstrap/build/compiler/harness/fixtures/other old-test edits; report obsolete
profile guards to parent. Fixtures ONLY differential/** stage m5bb preserve1493/
schema1/kinds1..11; baseline stage rejection permits manual bounded trusted oracle
checks, not harness edits/fake EVM-green. Verifier ONLY tools/java_diff.py,
tools/test_java_diff.py,tools/JAVA_DIFF.md,new jvmevm/long_arrays_validation_test.go
verifyM5bb* helpers. Baseline red expected, exact failure map required.
Parent owns plans/AGENTS/quickstart/Makefile/integration/approved profile updates.
One Solidity writer; no spawning/peer writes/push/global settings/untrusted Java.
All agents Sol/high WITHOUT Fast; honest scoped commits/SHA/size/checks/failures.

## Accepted integration evidence
Runtime353aa0f→9b66047,fixtures1e7ee35→35f9b17,verifier7b948d3→8eadfc7.
Reviewda72788→4781859 made scalar call genuinely b9 via interface local; retained
[J count2/J count3. Shared cap probe measured266,290,554 gas with guest constructors,
160,386,777 with zero-field Object; kept1024 arrays+1024 objects and250M budget,
isolating quota from unrelated work. Exact new [J expectations/retained F/D guards
verified. No runtime defect demonstrated or runtime/hash changed.
Parent final artifact/3bootstraps, Go/CLI,36 Python,1593 full,732 smoke,752 fast,
demos,AOT,focused vet and48 independent probes passed:
`build/java-diff-parent-m5bb/probe-xd_c2tax/results-final/`.
Prior1493 cases/budgets unchanged. Runtime111218 bytes SHA256
`ad3aeff4e658741374e76cf2bb76d33e392929f640feca563255fa7f89631dac`.
Next variable-width control flow before bounded IEEE work. No agent Fast.
