# M5b-a: scalar long and category-2 foundation

Authority JAVA_EVM_PROGRAM.md. Last-green M5a e9eaf6c:1383 oracle cases plus48
probes,36 Python,627 smoke/647 fast and focused gates. Runtime103667 bytes SHA
c46e6cce33cca976bae9bdaf9c89f99a93113d319395d74ff7acdee73d9b46fb.
All NEW agents Sol/high WITHOUT Fast/priority; no --fast or preference enabling.
Parent continuously integrates/independently verifies/advances bounded stages.

## Scope/invariant
Add internal scalar J descriptors, long fields/ConstantValue/constants/operations,
and category-2 operand/local/call semantics. Root remains EXACT static(I...)I,
reject J roots MethodError11 like other non-I roots. All parsing/type/slot/64-bit
arithmetic/heap/field/call/init behavior INSIDE ordinary EVM bytecode. Host only
packages unchanged raw classes/int args, invokes EVM and decodes. No host parser/
evaluator/heap/AOT/precompile/JRE fallback or consensus edits. Trusted JVM/javac
only build/oracle. Local runtime.Execute, not deployed/full JVM.

Long ARRAYS are M5b-b, NOT this stage: atype11/laload/lastore/[J and nested J leaves
remain deferred where resolution is required. Null cast shortcuts for structurally
valid [J remain as before. Float/double/CP6 execution, IEEE conversions, handlers,
monitors, wide/switch, Object/JRE APIs and array dispatch remain deferred. No new
JavaException kinds (1..11 unchanged). Preserve1383 old sources/entries/outcomes/
budgets, all3 bootstraps and existing quotas/limits.

## Constants/descriptors/fields
Decode CONSTANT_Long tag5 as exact big-endian64 bits. It consumes TWO logical CP
indices but only tag+8 payload bytes: n+1 must exist within cp_count and is unusable,
next serialized entry is n+2. Preserve parsing of unentered tag6 without executing
it. Malformed/truncated CP structures retain existing ClassError validation;
ldc2_w to CP hole/invalid index/wrong tag (including deferred Double6) Bytecode13.
Ordinary ldc/ldc_w must not load a long as an int/reference.

Add lconst_0/1 (09/0a), ldc2_w14 (u2 operand), lload16/lstore37 and short forms
1e..21/3f..42; lreturnad. J arguments/returns supported across every static/special/
virtual/interface/default/constructor context, preserving exact descriptor lookup
and access/initialization/final/cache rules. V only return, constructors V.

J static/instance fields use full64-bit defaults0/storage/tagging, not truncated
FieldInfo.uint32. Tag5 ConstantValue prepares static J fields; wrong constant tag
FieldError5, instance ConstantValue remains ignored. One long field is ONE logical
Java field/object-quota slot (not two fields), though stack/local width is two.
No narrowing at long argument/return/field boundaries; i2l/l2i do explicit conversion.
Preserve all I/Z/B/C/S declared narrowing behavior and reference safety.

## Category-2 accounting and locals
One logical long value occupies TWO JVM stack depth/local/argument words, not two
independently usable category-1 values. Physical EVM representation is implementation
choice: scalar64+tag with explicit word accounting is valid; no split/forged refs.
max_stack1024 and max_locals1024 remain JVM WORD bounds, MAX_FRAMES128 unchanged.
Do not accidentally halve/increase quotas or authorize roots by long's bit payload.

Long local at n uses n,n+1, no even-index alignment requirement. Only n loads it.
Use explicit head/tail state or equivalent. Every store invalidates any old long
whose two-slot range overlaps destination, then writes the new value/pair. Writing
category1 at former long tail invalidates the old head; writing at head invalidates
old tail; an overlapping lstore can invalidate pairs on either side. This applies
to istore/astore and uninitialized-ref transport too. Do not leave stale tails,
permit half loads, or lose constructor-token alias handling in untouched locals.

Out-of-range n/n+1 Bytecode8. Loading invalidated/uninitialized local Bytecode11;
wrong kind or tail-as-independent-value Bytecode14. Well-formed long load requires
both slots still valid. iinc and int/ref loads/stores don't reinterpret long words.
Existing malformed-input multi-fault precedence isn't a full verifier: isolate
errors. A valid local pair may start at odd index.

Calls count logical parameter values AND JVM words separately. Receiver contributes
one; J contributes two; other supported params one. Copy values to callee locals
at width-aware offsets and consume caller words exactly; preserve stack prefixes.
max_locals accommodates receiver+argument words. invokeinterface count byte MUST
match word count including receiver, e.g. (J)J count3, not2. Keep nonzero/zero-trailing
validation and <=255 encoding. All load/call/return paths preserve long head/value
identity, max_stack word overflow Bytecode9, underflow Bytecode3, type/category
misuse Bytecode14. Return opcode/descriptor mismatch CallError5; long return must
have exactly one complete category2 value, not extra prefix/half value.

## Stack permutation forms
Keep category1 forms including uninitialized ref transport. Operations act on
whole VALUES, max_stack charged by WORDS. Bytecode14 for invalid category forms,
Bytecode3 insufficient operands, Bytecode9 insufficient output word capacity.
pop/dup/dup_x1/swap only category1; never split a long. pop2 accepts one category2
OR two category1, not category1 atop category2. dup2 accepts one category2 or two
category1. dup_x2 accepts three category1 OR category2 below category1.
dup2_x1 accepts three category1 OR category1 below category2.
dup2_x2 has FOUR forms (bottom->top; lowercase cat1, uppercase cat2):
- a,b,c,d -> c,d,a,b,c,d
- a,b,C -> C,a,b,C
- A,b,c -> b,c,A,b,c
- A,B -> B,A,B
All forms must preserve exact long/ref/int values and untouched prefixes. Test
mixed reference/long forms, output capacity, underflows and illegal splits.

## Arithmetic/conversions
Add ladd61,lsub65,lmul69,ldiv6d,lrem71,lneg75, lshl79,lshr7b,lushr7d,
land7f,lor81,lxor83,lcmp94,i2l85,l2i88. All arithmetic modulo2^64, signed lcmp,
ldiv truncates toward zero; division/remainder zero -> Arithmetic1. MIN_LONG/-1
returns MIN_LONG, remainder0 without overflow exception. Mask int shift distance
with63; lshr sign extends, lushr zero fills. Shift consumes long plus category1
int, not long distance. i2l sign extends int32; l2i keeps low32. No host/float proxy.

Non-Errors still wrap EIIE3 when escaping <clinit>; Errors2/7/10/11 unwrapped;
EVM OOG never Java OOM. Class/interface initialization prerequisites and static
field replay stay exact even with category2 values waiting on caller stack.

## Verification and bounded references
JVMS SE8 2.6.1/2.6.2,4.4.5 and6.5 reviewed directly: local tail store invalidates
head, long two words/one value, all permutation forms and b9 count, MIN/-1 behavior.
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-2.html#jvms-2.6.1
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.5
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html
Use bounded trusted Java8 (/usr/lib/jvm/java-8-openjdk/bin/java) raw-class/oracle
probes for valid category2 forms/arguments/CV and arithmetic. Invalid CP/local/
category forms are interpreter validation tests, not a full-JVM verifier claim.
No host memory exhaustion/download/global config.

Append~80-110 trusted Java8 m5ba cases, preserve1383. Roots return int digests via
l2i/high-low folds/comparisons, no long root ABI. Cover64-bit boundaries/constants/
signed operations/shifts, mixed args/returns/all call kinds/defaults/constructors,
odd locals, postincrement/assignment stack forms, static/instance/interface/final/
hidden fields/ConstantValue, init order/reentrancy and arithmetic wrapping. No J[]
allocation/long-array fields or F/D/JRE/boxing/switch/wide surprises. Inspect javap.

Go verifier: CP5 payload/index holes/truncation, ldc2_w malformed/deferredDouble,
rootJ reject, per-word stack/locals/b9counts/argument offsets/returns/underflow,
local overlap invalidations, EVERY category2 stack form/illegal split/capacity,
exact full64bit arithmetic/fields/CV, int/ref/uninit safety, final/access/caches,
classinit replay with long stack prefixes, unchanged quotas/frame/OOG. Derive PC
boundaries and prove arithmetic with actual JVM, no blanket revert assertions.
Old selected long/l2i/descriptor negatives may be obsolete; report exact inputs/
new behavior to parent, not unauthorized edits/skips. Retain [J/F/D guards and
all previous fixture outcomes/budgets. Parent approves obsolete profile updates.

Parent integrates runtime->fixtures->verifier; independently rebuilds pinned
artifact/3bootstraps, Go/CLI/Python1383+oracle/smoke/fast/demos/AOT/vet plus probes.
Accept last-green then freeze long arrays M5b-b separately. No routine confirmation.

Runtime ONLY Solidity/runtimehex; jvmevm/jvmevm_test.go HASH ONLY; new jvmevm/
long_test.go runtimeM5ba* helpers. No host/API/decoder/CLI/bootstrap/build/compiler/
harness/fixtures/other old-test edits. Fixtures ONLY differential/** stage m5ba,
preserve1383/schema1/kinds1..11; baseline stage rejection -> bounded manual trusted
JVM checks, not harness edits/fake EVM-green. Verifier ONLY tools/java_diff.py,
tools/test_java_diff.py,tools/JAVA_DIFF.md,new jvmevm/long_validation_test.go
verifyM5ba* helpers. Baseline red expected, exact failure map needed.
Parent owns plans/AGENTS/quickstart/Makefile and integration/approved profile updates.
One Solidity writer, no spawning/peer writes/push/global settings/untrusted Java.
All agents Sol/high WITHOUT Fast; scoped commits, honest SHA/size/checks/limits.

## Accepted integration evidence
Runtime1652c43→713cef8,fixturesdffc8a8→cd7bdb1,verifier60c620c→01b76ab.
Review18a2187→ebfdf92 repaired category-form vs underflow classification, mutation
padding, and folded final getter with real getfield/JVM8 default-zero proof.
Obsolete J guards explicitly updated; F/D and genuine malformed/word-capacity
coverage retained. No runtime defect demonstrated, artifact unchanged.
Parent final artifact/3bootstraps, Go/CLI,36 Python,1493 full,682 smoke,702 fast,
demos,AOT,focused vet and48 independent probes passed:
`build/java-diff-parent-m5ba/probe-4cp40_7n/results-final/`.
Prior1383 fixture entries/budgets unchanged. Accepted runtime113189 bytes SHA256
`2d450f86e4245488fe2f73eb19338b8f2ac5423c3981bb6be99b397ab9096999`.
Next M5b-b long arrays. All NEW agents NO Fast; make java-fast is merely a fixture
test tier and remains an allowed verification gate, not a priority request.
