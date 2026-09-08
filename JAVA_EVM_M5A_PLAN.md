# M5a: narrow int-like primitive types and arrays

Authority JAVA_EVM_PROGRAM.md; last-green M4f-c8051225:1263 oracle cases plus48
parent probes,36 Python,567 smoke/587 fast and focused gates. Runtime100297 bytes
SHAefc31ddc4e43d80b459cd1f851c505f47470e24d15b85915539db6818959ba5f.
ALL NEW agents Sol/high WITHOUT Fast/priority; never --fast/re-enable preference.
Parent proceeds through bounded independently verified stages automatically.

## Scope/invariant
Add boolean Z, byte B, char C, short S descriptors/field storage/return semantics
and arrays, using computational category-1 int. All class parsing/type metadata,
normalization/heap/bytecodes/calls/init/outcomes remain INSIDE ordinary EVM bytecode.
Host only packages unchanged raw classfiles/int root args, invokes EVM, decodes.
No host parser/evaluator/heap/AOT/precompile/classpath/JRE fallback or consensus
change. Trusted javac/JVM only build/oracle. Local runtime.Execute, not deployment
or full JVM/Java SE. Preserve1263 previous fixture inputs/outcomes/budgets.

Root ABI deliberately stays exactly static(I...)I (ordinary or interface root).
Z/B/C/S root args/returns are NOT newly accepted: MethodError11. Do not use merely
computational kind==int to authorize a root signature; retain declared subtype.
Existing overload/ambiguity/access/staticness errors remain. Internal methods
(static/special/virtual/interface/default), fields and array leaves now accept
I/Z/B/C/S and existing references; V only method returns. J/F/D remain deferred.
No new JavaException kinds (1..11 same), object/array/frame/input caps unchanged.
No strings/JRE APIs, handlers/monitors, array dispatch, wide/switch or category2.

## Computational type versus declared subtype
All I/Z/B/C/S stack/local values are tagged computational INT with full32 bits.
Keep declared descriptor subtype separately where narrowing is required; don't
invent byte-sized stack slots or lose int/ref/uninitialized safety. Existing
iload/istore/iinc/arithmetic/branches/int conversions still operate on32-bit ints.
i2b0x91/i2c0x92/i2s0x93 ALREADY exist: preserve and extend regression coverage,
not claim they are new opcodes. They explicitly sign/zero extend as before.

Invocation arguments of declared Z/B/C/S are NOT implicitly narrowed at call
boundaries: raw bytecode passing int255 to (B)I passes255; passing int2 to (Z)I
passes2. javac normally inserts required source conversions, but the VM must not
add another conversion. Reference/int checks and b9 historical count still treat
these as one computational slot. Returns ARE narrowed by DECLARED return type
when executing ireturn: I unchanged; B sign-extend low8; S sign-extend low16;
C zero-extend low16; Z lowbit AND1 producing0/1. CallError5 remains opcode versus
return computational-kind mismatch, Bytecode14 remains int/ref/uninitialized mix.

Thus a (Z)I helper testing nonzero int2 can return1, whereas a (Z)Z identity helper
returns0 after ireturn narrowing. Ensure selected/cached method metadata preserves
the actual exact descriptor subtype across b6/b9/default/b7/static dispatch.

## Fields and ConstantValue
I/Z/B/C/S fields all consume one current int slot. Default zero. putstatic/putfield
normalize by declared field type (same I/B/S/C/Z rules as above). getstatic/getfield
produce correctly signed/unsigned/canonical computational ints. All existing
resolution/access/staticness/final/current-own-<clinit>/<init>/cache checks remain.
No implicit narrowing of unrelated locals or caller arguments.

Static ConstantValue for these descriptors uses CONSTANT_Integer (tag3), normalizes
by declared subtype during preparation, and observes existing initialization and
interface rules. Wrong CP kinds/attributes retain FieldError5/etc. Instance
ConstantValue is still ignored; constructor bytecodes initialize actual fields.
Preserve separate inherited/hidden declarations and actual-owner static storage.

Parent bounded Java8 ConstantValue mutation probe verified integer payloads:
2 -> Z=false,B=2,C=2,S=2;
255 -> Z=true,B=-1,C=255,S=255;
-1 -> Z=true,B=-1,C=65535,S=-1;
65535 -> Z=true,B=-1,C=65535,S=-1.
Reviewer verified ireturn/field/array narrowing and NON-narrowed invocation arguments
on Java8. Use controlled compiled/mutated trusted classfiles for extra exact probes,
not host production extraction/evaluation. Boolean semantics are lowbit, NOT !=0.

## Primitive arrays and type metadata
Enable newarray atypes4 boolean,5 char,8 byte,9 short;10 int unchanged.
Add baload0x33/caload0x34/saload0x35 and bastore0x54/castore0x55/sastore0x56.
baload/bastore operate on BOTH boolean[] and byte[], discriminating actual allocated
leaf type: byte sign-extends low8, boolean loads/stores canonical lowbit0/1.
caload/castore zero-extend low16; saload/sastore sign-extend low16. Values/index/count
remain computational ints. Null-before-bounds and negative-size-before-cap ordering
unchanged for well-typed operands. Wrong element opcode/array rank/type ->
ReferenceError1, wrong int/ref/uninitialized operand -> Bytecode14.

iaload/iastore ONLY int[]; aaload/aastore ONLY reference-component arrays; baload
must not consume byte[][] references as bytes or int[] values as bytes. Boolean[]
and byte[] are distinct array TYPES even though sharing opcodes/storage shape.
Primitive values may use current uint32 cells if correct observable normalization
is maintained. All int/byte/boolean/char/short/reference arrays share existing
1024 total arrays,65536 per-array length,262144 total elements. Object limits
independent1024 objects/1024 fields each/65536 total slots, no GC, reset each run.

Generalize ArrayType's primitive leaf identity: zero class id must no longer mean
all primitive arrays are int[]. Preserve explicit I/Z/B/C/S leaf distinction
through newarray/anewarray/multianewarray, rank255, fields/calls/returns/casts/type
tests/covariance/markers and array stores. Any primitive array is Object/Cloneable/
Serializable (and marker superinterfaces); unlike primitive leaves are incompatible,
not covariant just because computational int. byte[][] -> Object[] succeeds,
byte[] -> Object[] fails, boolean[] -> byte[] fails, byte[][] -> int[][] fails.
Reference arrays of primitive arrays remain supported and aastore checks actual
component identity, producing ASE9 for incompatible primitive-array values.
Valid cast mismatches CCE8 and instanceof0; assignment validation Reference2,
wrong heap/element opcode Reference1, same distinctions as M4d.

anewarray/multianewarray of new primitive leaves follow existing resolution/no-init/
negative-all-counts/materialized-quota/rank/error ordering. [J/[F/[D remain deferred
for non-null targets/allocation; malformed array names TypeError1; null type-test
shortcuts still structurally validate then skip resolution. At newarray unsupported
atypes6/7/11 and invalid others still ArrayError1. No float/long surrogate values.

## Verification and ownership
Append~90-120 trusted Java8 m5a cases, preserve1263 entries/sources/outcomes/budgets.
Root remains I-only: wrapper roots expose internal byte/boolean/etc methods/fields.
Cover sign/zero/lowbit boundaries, loops/conversions/overflow, all invocation kinds
including defaults/bridges/constructors/interface statics, hidden/inherited/final/
constant fields, primitive array loads/stores and nested multidimensional types,
covariance/markers/ASE/CCE/NPE/bounds/NASE/EIIE. Valid source javac generally emits
conversions; noncanonical argument/return/field/ConstantValue cases use independent
Go bytecode mutations and bounded Java8 oracles. Inspect actual descriptors/CP/
opcodes/owners, avoid accidental strings/boxed/JRE calls. Finite JVM heap/time,
no host OOM. Current JVM/Java8 parity preferred, Java8 exact semantics authoritative.

Go verifier independently validates root subtype rejection (not just kind), exact
raw argument non-narrowing vs field/return narrowing, ConstantValue payloads, boolean
lowbit vs truthiness, all field/call contexts and caches, wrong-kind/rank/opcode/
atype/truncation/branches, primitive type identity/casts/stores/nested ranks and
shared quotas/noGC/OOG. Confirm every handcrafted PC is an instruction boundary,
one defect isolated, actual JVM arithmetic expected. Old unsupported byte/boolean/
char/short descriptor/array negatives may be obsolete; workers report exact cases
and parent updates justified profile expectations, preserving unsupported J/F/D,
invalid tags/operands and all old fixture outcomes. Never blanket accept reverts.

Parent integrates runtime->fixtures->verifier, reviews primitive identity/return
subtype/root guards and old-profile changes, independently checks pinned artifact/
3bootstraps, Go/CLI/Python1263+fulloracle,smoke/fast/demos/AOT/vet plus new probes.
Accept last-green then freeze category2 long or other dependency-ordered remaining
stage. No routine confirmation or full-JVM/deployment claims.

Runtime ONLY Solidity/runtimehex; jvmevm/jvmevm_test.go HASH ONLY; new
jvmevm/narrow_primitives_test.go runtimeM5a* helpers. No host/API/decoder/CLI/
bootstrap/build/compiler/harness/fixture/other old-test edits. Report obsolete
profile guards, parent owns updates. Fixtures ONLY differential/** stage m5a,
preserve1263/schema1/kinds1..11; baseline stage rejection means manual bounded
trusted oracle checks, not harness edits/fake EVM-green. Verifier ONLY tools/
java_diff.py,tools/test_java_diff.py,tools/JAVA_DIFF.md,new jvmevm/
narrow_primitives_validation_test.go verifyM5a* helpers. Baseline red expected.
Parent owns plans/AGENTS/quickstart/Makefile and integration/independent review.
One Solidity writer; no spawning/peer writes/push/global settings/untrusted Java.
All agents Sol/high WITHOUT Fast; scoped commits and honest hashes/size/tests.
