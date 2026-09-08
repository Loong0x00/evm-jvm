# M5c-c: scalar software IEEE arithmetic

Authority JAVA_EVM_PROGRAM.md. Last-green M5c-b23f1f40:1811 oracle cases plus216
parent probes,36 Python,839 smoke/859 fast and focused gates. Runtime132118 bytes
SHAbab196c80d76db16257f2e2664c9a776c270782e87c3a3c169ecf364e73809f8.
All NEW agents Sol/high WITHOUT Fast/priority; never --fast/re-enable preference.
make java-fast is only a fixture tier. Parent proceeds through bounded independently
verified stages automatically, no routine confirmation.

## Scope and boundary
Add ONLY fadd62/dadd63,fsub66/dsub67,fmul6a/dmul6b,fdiv6e/ddiv6f,frem72/drem73.
fneg/dneg already supported; preserve their exact sign-bit behavior. Implement all
IEEE decoding, special classification, significand arithmetic/rounding and result
packing with bounded EVM integer/bit operations. NO host floating math, softfloat
host library, AOT, precompile, JRE fallback or new native bindings. The four exact
M5cb raw-bit bindings remain the ONLY permitted native services, inside EVM.
Raw class parsing/linking and guest execution still ordinary EVM bytecode; host
only packages unchanged classes/int args, invokes EVM, decodes. Trusted Java only
build/oracle. Local runtime.Execute, not deployed/full JVM.

No FP arrays/newarray6/7/faload/daload/stores/nested leaves this batch. No boxing/
Math/JRE APIs, handlers, monitors, jsr/ret or IEEE sqrt/FMA/transcendentals. Preserve
all1811 old fixture sources/entries/outcomes/budgets, root exact(I...)I, descriptors,
I/J/narrow/ref semantics, CP/transport/conversions/comparisons/negation, five bootstrap
images, category1 F/category2 D/local overlap/calls/word counts and existing caps.
No new JavaException kinds (1..11/schema1 unchanged).

## Standard-value-set arithmetic
Use standard binary32 (precision24) and binary64 (precision53) at EVERY operation
in all frames, strictfp or not. This is a permitted Java8 value-set implementation;
no extended exponent/x87 precision promise. No fusion/coalescing: each opcode
executes and rounds independently. All ordinary finite results round nearest,
ties-to-even (RNE), with gradual underflow/subnormals, signed zero and overflow to
signed infinity. Do not flush subnormals or saturate finite overflow to MAX.

Centralize checked result packing/rounding where sensible, with enough exact/guard/
round/sticky information to distinguish ties, cancellation and underflow. Avoid
intermediate floating rounding/double rounding. All integer additions/products/
shifts/normalization must be bounded and overflow-safe inside uint256; no unsigned
exponent-underflow recurrence like the fixed f2d bug. No exponent-magnitude linear
loops or huge shifted allocations for max-finite/min-subnormal inputs.

Suggested finite algorithms (implementation may differ with equivalent proof):
- add/sub align exponents with sticky collapse and adequate precision; cancellation
  normalization must retain exact low bits, not sticky-as-an-exact-value errors;
- multiply exact24x24 or53x53 integer significands, then one final pack;
- divide generate sufficient precision+guard information using bounded integer
  division/remainder, sticky records discarded remainder; one final pack;
- remainder exact binary modular reduction (see below), not rounded divide/multiply.

## Special values and signs
Any arithmetic NaN input or invalid operation produces deterministic CANONICAL
QUIET NaN:7fc00000 or7ff8000000000000, regardless operand sign/payload. This is our
explicit permitted generated-NaN policy, not cross-JVM payload equivalence. Pure
raw transport and fneg/dneg preserve prior payload/sign rules.

Add: opposite infinities -> NaN, same infinity/infinity+finite -> that infinity.
Exact nonzero cancellation -> +0 under RNE. -0+-0 -> -0; opposite signed zeros ->
+0. Subtraction behaves as addition with second operand sign flipped, preserving
its special signed-zero distinctions (e.g. -0-(+0)=-0, -0-(-0)=+0).
Multiply: zero*infinity -> NaN; otherwise sign XOR including zero/infinity.
Divide:0/0 or infinity/infinity -> NaN; nonzero finite/zero or infinity/finite ->
signed infinity; finite/infinity or zero/nonzero finite -> signed zero. Result
sign XOR. Floating zero divisors NEVER throw Java ArithmeticException. I/J divide
zero still does. Underflow/overflow/NaN are floating values, not EVM/Java exceptions.

Remainder: NaN operand, infinite dividend or zero divisor -> canonical NaN. Finite
dividend/infinite divisor returns dividend unchanged; zero dividend/nonzero divisor
returns original signed zero. Otherwise sign follows dividend; exact-zero result
retains dividend sign. Divisor sign has no effect on finite remainder magnitude.

## Java remainder, not nearest IEEE remainder
For finite x and finite nonzero y: r=x-y*trunc(x/y), with EXACT mathematical quotient
and operations, NOT a sequence of rounded floating instructions. Java7%4=3, whereas
IEEE nearest-quotient remainder would -1. Correct finite remainder is exactly
representable (may be subnormal), with no precision loss/overflow/underflow.

Decode |x|=A*2^a, |y|=B*2^b. Compute exact modulus at common binary scale without
building an exponent-sized integer. For a>=b, use (A*2^(a-b) mod B)*2^b, with bounded
modular exponentiation/squaring or equivalent exact reduction. EVM mulmod is allowed
as integer arithmetic. If |x|<|y| return x; handle remaining exponent cases exactly,
not by assuming a relation without proof. Magnitude significands are bounded24/53
bits; maximum exponent difference is finite and modular powering logarithmic. Zero
modulus must be handled by special-value classification before integer modulus.

Parent checked JVMS SE8 2.8 and6.5 f/d arithmetic/rem plus JLS15.17.3:
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-2.html#jvms-2.8
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html
https://docs.oracle.com/javase/specs/jls/se8/html/jls-15.html#jls-15.17.3
These specify RNE, gradual underflow, Java remainder quotient selection, exact
finite remainder and absence of floating arithmetic traps. Verify any uncertainty
locally/against these sources, not host-language operator assumptions.

## Interpreter integration and errors
Consume two logical values of exact F or D kind, produce one of same kind. F two
input words->one, D four->two; preserve prefixes and all whole-value stack rules.
Missing operands Bytecode3, wrong int/J/ref/F-vs-D/uninitialized kind Bytecode14,
existing stack capacity/return descriptor errors unchanged. Do not accidentally
reuse integer arithmetic paths or treat long bits as double. Fields, defaults,
interface calls, native raw bits and init replay remain exact. No new arithmetic
exception class; existing guest integer/long errors from evaluating operands still
occur before the floating opcode and retain initializer wrapping/Error/OOG rules.

## Bit-exact oracle and resource gates
Fresh oracle comparisons use actual Java8 and current JVM with standard/strictfp
fixtures. Root returns raw32 or separate raw64 high/low words using ONLY approved
bindings; finite/zero/infinity bits must match EXACTLY. Normalize ONLY generated
NaN payloads in comparison fixtures to our canonical form; do not hide finite or
signed-zero errors. Explicit EVM-only tests require documented canonical generated
NaN; raw/sNaN transport retains M5cb portability caveat. No new host ABI/math oracle
in production, no native Math API, no fixture expected values derived from EVM.

Add fixed finite performance gates in minimal trusted root wrappers: each single
worst-case arithmetic operation <=20M gas, and16 repeated worst-case remainders
<=100M (same original operands each time, no shortcut/coalescing). Include maximum
exponent gaps, max-finite/min-subnormal, near cancellation and subnormal quotients.
Record measured gas, not just limits; fail/report before changing budgets. These
are new focused benchmark bounds, not old-case budget increases. No host OOM,
no unbounded shift/exponent loops. Prior1681/1811 budgets and all heap caps unchanged.

Append~120-160 trusted Java8 m5cc source cases, preserve1811. Feed raw operands as
int/hi-lo roots so javac cannot fold the operation. Cover each opcode, every special
class/sign matrix, nearest-half/adjacent/tie-even cases, cancellation, absorption,
normal/subnormal/overflow boundaries, signed-zero remainder, Java7%4 distinction,
extreme modulus, mixed calls/defaults/constructors/field compound updates, strictfp
and ordinary contexts, classinit with FP0 division yielding values rather than
ArithmeticException. No FP arrays/JRE/boxing/FMA/handlers. Inspect actual Code.

Independent Go: exact boundary tables and seeded finite/raw-bit operation vectors
against Java8/current JVM with NaN-only normalization; malformed kind/stack/return/
CP/prefix tests; signed-zero/NaN policies; raw registry boundaries retained; category2
compound/permutation/local/call behavior; fixed gas benchmarks. Independent expected
bit patterns for critical ties and subnormals, not only randomized oracle parity.
Old FP-arithmetic rejection probes may be obsolete: report exact inputs/new behavior,
parent explicitly updates while retaining FP-array/unknown-native/wrong-kind guards.
No blanket weakening or old fixtures/budgets changed.

Parent integrates runtime->fixtures->verifier, independently reviews software math,
rebuilds pinned artifact/5bootstraps, runs Go/CLI/Python1811+oracle/smoke/fast/demos/
AOT/vet plus broad parent probes and performance gates. Accept last-green then
freeze FP arrays separately, followed by exception/unwind/library stages. No routine
confirmation/full-JVM/deployment claims.

## Ownership
Runtime ONLY Solidity/runtimehex;jvmevm/jvmevm_test.go HASH ONLY;new jvmevm/
ieee_arithmetic_test.go runtimeM5cc* helpers. No bootstrap/build/compiler/host/API/
decoder/CLI/harness/fixtures/other old-test edits. Report obsolete guards to parent.
Fixtures ONLY differential/** stage m5cc preserve1811/schema1/kinds1..11; baseline
stage rejection -> bounded manual trusted oracles, not harness edits/fake EVM-green.
Verifier ONLY tools/java_diff.py,tools/test_java_diff.py,tools/JAVA_DIFF.md,new
jvmevm/ieee_arithmetic_validation_test.go verifyM5cc* helpers; baseline red expected.
Parent owns plans/AGENTS/quickstart/Makefile/integration/approved profile updates.
One Solidity writer, no spawning/peer writes/push/global settings/untrusted Java.
All agents Sol/high WITHOUT Fast; honest scoped commits/SHA/size/measurements/errors.
