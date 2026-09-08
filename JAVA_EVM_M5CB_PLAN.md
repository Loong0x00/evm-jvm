# M5c-b: scalar IEEE representation, conversions, comparisons and raw-bit services

Authority JAVA_EVM_PROGRAM.md; last-green M5c-a531d72c:1681 oracle cases plus48
probes,36 Python,773 smoke/793 fast and focused gates. Runtime116023 bytes SHA
1ea50d09775eb2422f618d4bb0fd0b1d7b867083c19a48c2e0b84f7390e2753d.
All NEW agents Sol/high WITHOUT Fast/priority; no --fast or enabling preference.
Named java-fast remains an allowed fixture tier. Parent continuously integrates/
independently verifies/advances bounded stages, no routine confirmation.

## Scope/execution boundary
Add scalar F/D representation/constants/locals/fields/calls/returns/conversions/
comparisons and sign negation. Add EXACTLY four raw-bit Java API native bindings
implemented in ordinary EVM bytecode below. Every class parse/link, guest value,
conversion/rounding/comparison and native binding executes INSIDE EVM. Host only
packages unchanged class bytes/int root args, invokes EVM and decodes. No host
floating-point math, evaluator/parser/heap, AOT, native precompile, filesystem/JRE
fallback or consensus changes. Trusted javac/JVM only build/oracle. Local
runtime.Execute only, not deployment/full JVM/Java SE.

Arithmetic add/sub/mul/div/rem is NEXT batch, not quietly approximated here.
F/D ARRAYS/newarray6/7/faload/daload/fastore/dastore and nested F/D leaves remain
deferred until a separate batch. jsr/ret, handlers, monitors, boxing, broader JRE
APIs and array-receiver dispatch remain deferred. Existing I/Z/B/C/S/J/reference/
array/default/interface/initialization/variable-width behavior unchanged. Preserve
1681 old source files/manifest entries/outcomes/budgets and all current limits.
Root remains EXACT static(I...)I; F/D args/return roots MethodError11. No new Java
exception kinds (1..11/schema1/value-or-exception protocol unchanged).

## Representation and supported instructions
Use distinct typed raw IEEE binary32/binary64 bits, never host float or scaled
integer approximations. Float category1 (one JVM word), double category2 (two).
Preserve signed zeros, infinities, subnormals, and raw NaN payload/sign under pure
transport. Keep subtype/width metadata throughout every invocation mode, fields,
locals, caches, constructor tokens, b9 counts and root guards. D locals use the
same overlap/head-tail invalidation discipline as J; mixed J/D permutations work
as category2 but must not confuse kinds. Physical scalar representation allowed
with exact word accounting; one D field remains one logical object field quota.

Read CP4 exact32 bits and CP6 exact64 with the same two-index/unusable-hole rules
as CP5. ldc/ldc_w accept3 or4; ldc2_w accepts5 or6. Wrong tags/holes retain Bytecode13.
Add fconst0/1/2 (0b/0c/0d), dconst0/1 (0e/0f), fload17/dload18 and short22..29,
fstore38/dstore39 and short43..4a; corresponding wide forms; freturnae/dreturnaf.
Default F/D fields +0 bits, static ConstantValue must be CP4/CP6 respectively;
wrong tag FieldError5, instance ConstantValue ignored. No implicit I/J↔F/D bit
reinterpretation through normal assignments/calls; kind mismatch Bytecode14.
Return opcode/descriptor mismatch CallError5. All max_stack/local/frame limits
are still JVM words, [F/[D remain deferred references, not scalar types.

Add i2f86/i2d87/l2f89/l2d8a/f2i8b/f2l8c/f2d8d/d2i8e/d2l8f/d2f90;
fcmpl95/fcmpg96/dcmpl97/dcmpg98 and fneg76/dneg77. Existing conversions unchanged.
Negation is exact sign-bit flip, including zero/NaN; no other FP arithmetic.

## Conversion/comparison semantics
Implement conversion using bounded integer/bit operations in EVM, with correct
round-to-nearest ties-to-even (RNE) for I/J->F/D and D->F. I->D and finite F->D are
exact; J->D/J->F may round. D->F handles rounding carries, normal/subnormal boundary,
gradual underflow, signed zero, overflow to signed infinity. No flush-to-zero.
Avoid huge shift/multiply loops; all exponent/rank cases bounded by IEEE formats.

F/D->I/J truncates toward zero then saturates to signed MIN/MAX on overflow;
NaN ->0, +infinity ->MAX, -infinity ->MIN. No Java ArithmeticException for these
conversions. Preserve long MIN boundary without Solidity overflow/panic. f2b/c/s
is ordinary f2i then existing explicit integer narrowing, not extra opcodes.

fcmp*/dcmp* returns tagged int -1/0/1: signed numeric comparison; -0==+0;
infinities order normally; any NaN yields -1 for *cmpl, +1 for *cmpg. Never compare
raw sign-magnitude bits as unsigned integers without IEEE handling. Exact J/I vs
F/D kind validation remains; no interpreting long bits as double except native API.

Use standard binary32/binary64 value sets in ALL frames (also non-strictfp), a
permitted Java8 implementation choice. No extended-exponent/x87 promise. Fields,
locals, calls/returns and CP transport preserve chosen bits. Conversion-produced
NaNs deterministically canonicalize to quiet7fc00000/7ff8000000000000; this is an
explicit implementation choice, not a cross-JVM raw NaN payload guarantee. Pure
transport/raw APIs preserve payload; fneg/dneg flip sign. Arithmetic-generated
NaN/rounding rules will be separately frozen next batch.

## Explicit four-method EVM native binding contract
Raw-bit observability under int-only roots is needed for exact verification. Permit
ONLY selected public static native/no-Code declarations with these exact class/
name/descriptors:
- java/lang/Float.intBitsToFloat(I)F
- java/lang/Float.floatToRawIntBits(F)I
- java/lang/Double.longBitsToDouble(J)D
- java/lang/Double.doubleToRawLongBits(D)J
Bindings do ONLY raw payload reinterpretation/tag replacement, in EVM code, with
normal descriptor/kind/word checks and return capacity. Treat them as one entered
call for existing frame-limit checking; no persistent Java Code frame or host JNI.
Resolve/access-check and initialize the DECLARING class normally before binding.
All other native methods, wrong flags (private/nonstatic/abstract/synchronized) or
native+Code shapes stay unsupported CallError4. Other API names are not invented.

Recognize a binding only for a NATIVE declaration. If user supplies a canonical
Float/Double class with an ordinary Code method of the same name/signature, execute
that Code normally—never skip guest Code because a familiar name matched. Supplied
native declarations with exact approved signatures may bind, like a VM native
registry. This is NOT a general native-method allowance, external precompile or
class-specific Java evaluation. No Float.valueOf/isNaN/floatToIntBits/Number APIs.

Append minimal trusted Float/Double class images when absent, never overwrite
user-supplied bytes. Parse inside EVM like existing Object/markers; unchanged64
user class cap, now at most5 internal bootstrap slots (69 classes total). Existing
Object/Cloneable/Serializable images unchanged. Minimal holders are NOT complete
boxed Float/Double classes, not Number subclasses and not boxing implementations.
Source layouts (javac --release8 -g:none -Xlint:-options) parent verified:
`package java.lang; public final class Float { private Float() {} public static native float intBitsToFloat(int bits); public static native int floatToRawIntBits(float value); }`
197 bytes SHA437d784b11d0b632017a94cc2c0d99b35cd93c39f49b98b0660e4316d9960dd4.
`package java.lang; public final class Double { private Double() {} public static native double longBitsToDouble(long bits); public static native long doubleToRawLongBits(double value); }`
202 bytes SHAd9ac93be34df21e1ec5872e307f67b1301c0606c1ccd57ee6a61030b0aa45363.
Build/check source->javac->hex->embedded bytes before unchanged pinned solc settings.
No downloads/global config or runtime host class generation.

## Oracle discipline and tests
Java Float/Double raw-bit APIs can quiet SIGNALING NaNs on some hardware/JVM paths.
Do not claim universal raw signaling-NaN bit parity. Use finite/infinity/signed-zero/
quiet-NaN transport patterns for exact fresh JVM differential tests; explicit EVM
raw-transport guarantee may be checked separately with that caveat. For conversion
NaNs, oracle fixture wrappers may normalize NaN results to canonical bits ONLY
where Java spec leaves payload unspecified; finite results must remain bit-exact.
Add EVM-only exact checks for the documented canonical conversion NaN and raw
payload guarantee. Never normalize away finite rounding or signed-zero mismatches.

Append~100-130 trusted Java8 m5cb cases, preserve1681. Int roots accept float raw
bits or two ints joined to double bits; return exact int bits or separate high/low
long-bit words where needed (avoid only collision-prone hashes). Cover all special
classes/subnormals/rounding halfway and adjacent cases, integer extrema and 2^24/
2^53/2^63 boundaries, all ten conversions, sign negation/comparisons/NaN directions,
F/D fields/ConstantValue/static/instance/hidden/final/default/interface calls,
wide/local/category2 transports, init ordering and reference separation. Only four
approved raw APIs, no arithmetic opcodes/arrays/boxing/JRE shortcuts. Finite Java8
and current-JVM oracle processes; record versions/raw-bit assumptions. Compile
unchanged trusted classes, no host production conversion. No host memory exhaustion.

Independent Go exact raw CP4/6/holes/tags, F/D/J/I/ref confusion, double local overlap/
stack forms/b9 word counts/returns/max_stack, root guards, fields/CV bits/cache/finals,
raw native registry ONLY exact selected signatures and correct normal Code override/
class initialization/depth/errors, markers/user indices69/bootstrap hashes, all
conversion corner cases with actual Java8 and independent expected bit patterns.
Canonical-NaN policy clearly separate from finite bit comparisons. Deferred arithmetic/
array/other native methods remain exact rejection. Unknown exception/OOG unchanged.
Old F/D scalar/wide/CP rejection probes may be obsolete; REPORT exact inputs/new
semantics to parent; no unauthorized old-test changes/skips. Retain deferred F/D
arrays/arithmetic and invalid kind/flags/operand guards. No old fixture budgets
changed. Parent integrates/reviews/independently rebuilds artifact+5bootstraps,
Go/CLI/Python1681+oracle/smoke/fast/demos/AOT/vet+probes, accepts last-green then
freezes software IEEE arithmetic separately. No routine confirmation/full-JVM claim.

## Ownership
Runtime ONLY Solidity/runtimehex/build.js; new bootstrap/Float.java,Float.class.hex,
Double.java,Double.class.hex; jvmevm/jvmevm_test.go HASH ONLY; new jvmevm/ieee_test.go
runtimeM5cb* helpers. No old bootstrap/compiler dependency/settings/host/API/decoder/
CLI/harness/fixture/other old-test edits. Report obsolete tests to parent.
Fixtures ONLY differential/** stage m5cb preserve1681/schema1/kinds1..11; baseline
stage rejection permits bounded manual trusted oracle checks, not harness edits.
Verifier ONLY tools/java_diff.py,tools/test_java_diff.py,tools/JAVA_DIFF.md,
new jvmevm/ieee_validation_test.go verifyM5cb* helpers; baseline red expected.
Parent owns plans/AGENTS/quickstart/Makefile and integration/explicit profile updates.
One Solidity writer; no spawning/peer writes/push/global settings/untrusted Java.
All agents Sol/high WITHOUT Fast; scoped commits/honest SHA/size/checks/caveats.

## Accepted integration evidence
Runtime90f13a1→ea0be6a,fixtures2b243ab→fcefdc2,verifier4edeec4→3b5ec06.
Parent216 independent probes found8 f2d panics despite1811 fixed cases green:
unsigned exponent-127+1023 underflowed normal exponents1..126. Review cfee5da→
98d5c62 independently found/fixed rebias ordering and added regressions; isolated
retagged CP probes from shared ConstantValue fields and updated obsolete F/D guards.
Parent final artifact/5bootstraps, Go/CLI,36 Python,1811 full,839 smoke,859 fast,
demos,AOT,focused vet and216 probes all passed:
`build/java-diff-parent-m5cb/probe-f81bfad2/results-final/`.
One combined shell timed out after successful full+216 checks during smoke; smoke/
fast/demos/AOT/vet were explicitly rerun successfully, not inferred completed.
Prior1681 manifest entries/budgets unchanged. Runtime132118 bytes SHA256
`bab196c80d76db16257f2e2664c9a776c270782e87c3a3c169ecf364e73809f8`.
Finite bits exact, conversion NaNs canonical; signaling-NaN transport portability
caveat retained. Next pure-EVM IEEE arithmetic, no host math. All agents NO Fast.
