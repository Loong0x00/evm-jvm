# Java inside EVM: staged interpreter (M5d-a)

A generic JVM-subset interpreter compiled to ordinary EVM bytecode. The host
reads an unchanged `.class` file and ABI-packs raw bytes, an entry name and int
arguments. **Classfile parsing, method lookup, instruction predecode, local/stack
handling, branches, loops and Java computation all execute inside geth's EVM.**
The host does not parse, translate, specialize or evaluate Java on this path.

This is a **limited JVM subset, not full Java or Minecraft**. `javac` and the
Solidity compiler operate at build time. A host JVM is used only as a test oracle.

**Local execution, not mainnet deployment:** the current 154,839-byte runtime
exceeds EIP-170's 24,576-byte deployed-code limit. Geth `runtime.Execute` installs
runtime code directly into its temporary state; no CREATE/deployment is tested.
Execution remains real EVM bytecode, with no host Java fallback or consensus edits.

**Accepted:** M5d-a implicit exceptions, ordered handlers, unwind and captured-ref
rethrow; evidence in `JAVA_EVM_M5DA_PLAN.md`. New Throwable construction/APIs remain
deferred. Target is genuine Minecraft startup-complete output in unmodified EVM,
not necessarily client connectivity. User selected **vanilla Minecraft1.12.2 / Java8**;
official artifact/ready marker pinned in `JAVA_EVM_PROGRAM.md`, static evidence in
`JAVA_EVM_MC_STARTUP_PROPOSAL.md`. No server has run. Separate stock-deployment/continuation
slice S0 is accepted in `JAVA_EVM_STOCK_S0_PLAN.md`: small integer programs execute
through ordinary CREATE and signed resume transactions. It is NOT deployment of
the full interpreter. S1 now also executes the82 original M1/M2 workloads through
EVM-derived reusable metadata, named arguments and bounded branch/loop resumes;
static calls, broader types/libraries and MC startup remain later work.

**Latest priority:** the user permits relaxed local gas budgets for the MC artistic
experiment. Local startup is now first; full standard-chain deployment is not a
prerequisite. Preserve EVM semantics/charging and record explicit finite experiment
budgets/watchdogs. Existing stock acceptance budgets/results remain unchanged and
separate. Reuse the richer monolith for MC prerequisites; no MC startup claim yet.
See `JAVA_EVM_PROGRAM.md` for the resource and continuation boundary.

## Quickstart / stage gates

Run from the fork, not the unrelated home-directory Git repository:

```sh
cd /home/user/evm-jvm/geth
make java-demo       # add(20,22), sum(100), fibonacci(20)
make java-smoke      # 1040 fixed JVM/EVM differential cases
make java-fast       # smoke + 20 seeded cases (1060 total)
make java-full       # all 2231 differential cases
make java-test       # artifact check + Go tests + 36 runner tests + all 2231 cases
```

Go 1.24+, a JDK supporting `javac --release 8`, and make are needed for the demo.
Python 3 is needed for differential tests. Node/npm are needed to rebuild/check
the Solidity artifact (`java-test` includes this check), not for the standalone
CLI or demo. First-time builds may download Go/compiler dependencies.

Stage M1 covers 12 add/identity cases. Stage M2 includes these plus 70 integer
control-flow cases. M2b adds 119 integer-expression cases: 201 total, including
two expected uncaught ArithmeticExceptions. Earlier 82 cases are preserved.
M3a adds 67 call/frame/recursion cases, bringing the total to 268 (261 values,
six ArithmeticExceptions and one StackOverflowError). All previous 201 entries
remain unchanged. Make gates use cumulative `--stage all`; explicit older stages
still select historical subsets. M3b adds 73 raw-bundle cases: 341 total
(329 values, 10 ArithmeticExceptions, 2 StackOverflowErrors). Previous 268 entries
are unchanged. M3c adds 85 field/initializer cases: 426 total (407 values and
19 known Java exceptions). All prior341 entries remain unchanged. Tests are
bounded evidence, not conformance. M3d adds72 hierarchy cases:498 total
(475 values,23 known exceptions); earlier426 entries are unchanged. M4a adds115
int-array cases:613 total (571 values,42 known exceptions). Earlier498 entries
and their budgets remain unchanged.

Additional commands:

```sh
make java-diff-m1                    # M1 regression cases on the current runtime
make java-harness-test               # includes real JVM/EVM smoke, not only mocks
make java-fast JAVA_DIFF_SEED=57      # repeatable alternate sample
python3 tools/java_diff.py --case m2-fibonacci-20
```

The direct runner assumes `make java-build` has built the current CLI. Make
entry points rebuild it to avoid accidentally testing a stale binary. A full
merge gate also retains the separate M0 checks: `make java-aot-test`.

## Measured demo results

One unchanged **154,839-byte** interpreter runtime handles legacy and bundled inputs:

| Raw input / entry | Result | Execution gas |
|---|---:|---:|
| Add.class / add(20,22) | 42 | 401,174 |
| Loops.class / sum(100) | 5050 | 2,923,901 |
| Loops.class / fibonacci(20) | 6765 | 1,179,716 |
| BasicHelper + BasicRoot / threeArguments(1,2,3) | 10203 | 768,110 |
| M4aArrays.class / fillSum(10,3) | 165 | 3,084,453 |

Typed checks raised sum(100) beyond its old2M demo budget, independently confirmed;
the demo now uses3M. No historical oracle input/budget or semantic assertion changed.

Runtime SHA-256:
`dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`

Gas includes ABI decoding, scanning the **whole input class**, instruction
validation and interpretation. It excludes contract deployment, transaction
intrinsic gas and calldata transaction fees. Changing a class's other methods or
metadata can change gas; values above refer to `make java-demo` inputs.

Build/use the CLI directly:

```sh
make java-build
build/bin/jvmevm -class build/java-evm-interpreter/Loops.class \
  -method fibonacci -args 20 -gas 2000000
```

`cmd/jvmevm` reads bytes and calls `jvmevm.Run`, which ABI-encodes input and calls
`core/vm/runtime.Execute`. The generic runtime is embedded, not generated per
Java class or argument. Errors in Java parsing/dispatch are EVM reverts with
Solidity custom-error data. Insufficient gas is actual EVM out-of-gas; an infinite
Java loop consumes its finite gas budget rather than returning a fake value.

## Raw multi-class input

Repeat `-class` and explicitly name the entry class using JVM internal slashes:

```sh
build/bin/jvmevm \
  -class build/java-evm-interpreter/bundle/basic/BasicHelper.class \
  -class build/java-evm-interpreter/bundle/basic/BasicRoot.class \
  -entry-class bundle/basic/BasicRoot -method threeArguments -args 1,2,3 -gas 5000000
```

One file without `-entry-class` retains legacy `Run`. An explicit entry class
selects `RunClasses`, even for one file; multiple files require it. Go only packs
raw bytes and provided metadata. EVM discovers declared names, rejects duplicates,
selects the entry and resolves direct static owners. File names/order do not
identify classes. Missing owners do not trigger host filesystem/classpath lookup.

Bundle mode allows at most64 classes, ordinary supplied superclass chains and
per-class CP/method caches/frames. Object may be an implicit terminal; other
required parents must be supplied, even for the legacy entry. HierarchyError1–5
identify missing parents, cycles, final-parent extension, invalid superclass kind
and inaccessible parents. Unreferenced bundle classes need not link their parents.
Interfaces/default-method initialization still fail explicitly.

Static member resolution searches exact declarations through the parent chain,
keeps the actual declaring owner and shared storage, and respects hiding/overloads.
Public inherited members of a hidden ancestor work through an accessible public
subclass; protected statics permit a subclass or same-package caller. Private and
unrelated/package-inaccessible accesses fail. Inherited active use initializes the
declaring class, not automatically its symbolic subclass. Root entry still requires
a declared, unambiguous int-returning static method. Known Java outcomes propagate
across classes; legacy external method calls retain CallError2.

## Supported semantics and limits

Unambiguous static root, only `int` arguments and an `int` return (internal
helpers can use int/supported reference parameters, return int/void/references, and be overloaded):

- `iconst_m1` through `iconst_5`, signed `bipush` and `sipush`
- `iload`, `istore`, including their `_0` through `_3` forms
- `ldc` / `ldc_w` for CONSTANT_Integer, resolved inside EVM
- `iadd`, `isub`, `imul`, `idiv`, `irem`, `ineg`, signed-byte `iinc`
- `ishl`, `ishr`, `iushr`, `iand`, `ior`, `ixor`, `i2b`, `i2c`, `i2s`
- `ifeq`/`ifne`/`iflt`/`ifge`/`ifgt`/`ifle`, corresponding `if_icmp*`
- `goto`, `ireturn` (including early returns followed by other code)
- Tag-10 `invokestatic` (same-class or supplied direct bundle owner), internal
  void `return`, category-1 `pop`
- `getstatic`, `putstatic` for I/[I fields
- null/aload/astore, int `newarray`, arraylength/iaload/iastore, internal areturn
- reference equality/null branches, nop, all category-1 pop/dup/swap forms

### Typed integer arrays

Int and reference slots have distinct tags; null is not integer zero. Local,
field, arithmetic, branch, call and return paths validate kinds. Root signatures
still accept only int arguments/return, so host numbers cannot forge references.
Heap identities live inside EVM: aliases share writes, distinct allocations stay
distinct, helper returns preserve identity, and arrays survive frame returns.
Static/inherited [I fields and initializer-created arrays use the same heap;
final references prohibit rebinding, not element mutation.

Array allocation/read/write/identity/null/bounds behavior is implemented in EVM.
Limits:1024 arrays,65536 elements per array,262144 total elements per invocation.
No GC; even unreachable allocations count. A fresh invocation resets heap/statics.
These logical caps do not promise sufficient EVM gas: allocating the total limit
costs about139M gas with Solidity's word-sized array representation. Cap checks use
focused EVM-only tests, not dangerous reference-JVM heap exhaustion.

### Integer static state and class initialization

Static storage is shared across frames for one invocation, fresh on the next
Run/RunClasses. Supported fields prepare to zero; static I ConstantValues are
applied when initialization starts (also when ACC_FINAL is absent), before
`<clinit>` and before superclass initialization. Instance ConstantValue attributes
are ignored. Active use initializes
only the owner, once; same-thread reentrant/cyclic requests observe prepared state
without restarting initializers. Superclass initialization precedes the child's
own initializer, including children without `<clinit>`; child prepared constants/
defaults remain visible to reentrant parent code. Explicit continuations preserve
root/call/get/put operands and PC. Unused supplied initializers are not eagerly run.

Final writes require the actual declaring class's `<clinit>`, not a helper called
by it or cached read permission. FieldError1–5/InitError1 distinguish malformed
references, field/type/access/constant and initializer metadata failures. These
are EVM errors, not invented Java linkage outcomes.

M3a uses independent explicit Java frames in EVM memory: PC, operand stack,
locals and initialization state. Arguments transfer in descriptor order; value
returns preserve caller prefixes and locals. Private helpers and overloaded
helpers resolve by exact name+descriptor; the root entry remains name-unambiguous
and int-returning. Method code is validated/predecoded only when entered, and
Methodrefs are cached within an invocation. Unused constructors/String methods
remain tolerated. Recursive factorial(10)=3628800 and recursive Fibonacci(10)=55
pass the oracle suite (distinct from the iterative demo above).

32-bit arithmetic wraps like Java; comparisons are signed. Branch offsets are
signed 16-bit, relative to the instruction address. The interpreter validates
all selected-method instructions, including unreachable instructions, before
execution and rejects branches into operands or outside the code. Loads and
increments check local initialization; stores, stack operations and return
shape are bounded/checked at execution time.

Caps: constant pool 4096 entries; Code 65,535 bytes; selected operand stack and
locals 1024 each; 128 active frames including root and initialization
continuations. Gas bounds execution
and allocation. Stack capacity does not claim to match OpenJDK's configuration.
Method descriptors, entered Code structure and relevant UTF-8 references are
checked. Root names must be unambiguous and roots static. Entered synchronized/
abstract/no-Code methods are rejected, native calls limited to four raw-bit bindings;
overloaded internal helpers and ordinary instance calls are supported. Valid entered
exception tables are checked and handled. `<clinit>` is VM-scheduled, not directly
invocable by guest code.

M2b division truncates toward zero; remainder follows Java's sign rules.
INT_MIN/-1 wraps to INT_MIN (remainder zero), shift counts are masked with 31,
and byte/short/char conversions preserve their signed/unsigned Java semantics.

**Deferred:** fresh Throwable construction/APIs, Strings/general main launcher,
array-receiver virtual calls, monitors, broad class libraries and standard deployment/
continuation workflows. All primitive scalar/field/array types are implemented.

This is not a full JVM verifier: no modified-UTF8 validation, general class
hierarchy/linking/type verification, full control-flow dataflow verification,
or validation of every unused member/attribute/constant-pool relationship.
Inputs should be treated as experimental. A gas-bounded EVM failure is not a
Java exception implementation.

### Explicit uncaught Java outcomes

Divide/remainder by zero now produces EVM-side `JavaException(uint256)` kind 1.
The host decodes only the exact known selector/length/kind into
`Result.ExceptionClass = "java.lang.ArithmeticException"`; it does not evaluate
the guest instruction. The CLI emits exactly one of `result=<int32>` or
`exception=<class>`, with the same runtime/gas fields. Known Java outcomes exit 0
under this method-invocation protocol; EVM/validation/harness failures exit
nonzero. This is not Java launcher's exit-code compatibility.

The oracle suite explicitly declares expected exception cases and compares
exception classes from actual JVM and EVM. Unknown payloads, Solidity panics,
bytecode/class errors and out-of-gas cannot silently become Java exceptions.
Kind 2 now represents `java.lang.StackOverflowError` when pushing beyond the
128-frame cap. In M5d-a these and all modeled Java faults first search guest handlers;
only unhandled faults use the external ABI. A lower gas limit can fail EVM OOG first.
Kind3 is EIIE for non-Error escaping the actual initializer after local handlers;
Error subtypes are unwrapped. Kind12 is NCDFE on later active use of an erroneous
class/interface. Captured VM exception objects preserve identity on rethrow; root
initialization occurs before its method handlers are eligible. Public Throwable
construction/causes/messages and thread synchronization remain deferred.

M4a adds kinds4 NegativeArraySizeException,5 ArrayIndexOutOfBoundsException,
6 NullPointerException,7 OutOfMemoryError. Null checks precede array bounds;
negative sizes precede positive-cap checks. Non-Error array exceptions escaping
initializers wrap as EIIE; OOM/StackOverflow remain Errors. EVM OOG is never Java
OOM. BytecodeError14 rejects kind confusion; ArrayError1 rejects other newarray
types; defensive ReferenceError1 protects invalid handles.

Call validation has exact `CallError(code,pc)` payloads: malformed reference (1),
external owner (2), missing exact signature (3), unsupported callee semantics (4),
return-kind mismatch (5). Codes 1–4 locate the caller's invokestatic; code 5
locates the mismatched return within the entered method. These remain EVM errors,
not fabricated Java linkage exceptions.

## Differential verification and replay

Fixtures and host-only oracle: `jvmevm/testdata/differential/`.
Runner and protocol/error tests: `tools/java_diff.py`, `tools/test_java_diff.py`.
Detailed flags/format: [tools/JAVA_DIFF.md](tools/JAVA_DIFF.md).

The oracle executes trusted fixture code on the host JVM; this is not a sandbox
for arbitrary untrusted Java. Isolate/review external code before using it here.
The production CLI never invokes the host JVM.

Every selected case executes on real JVM and on the EVM interpreter. Results
are compared exactly as signed int32; unsupported cases are not silently skipped
or counted as passes. Out-of-gas, revert, timeout, unexpected Java exception,
mismatch and harness failure are distinct non-success categories. A run must
use the same generic runtime hash throughout.

Artifacts include IDs/seed, source/class hashes, actual Java/Javac versions,
commands/stdout/stderr, gas and single-case replay commands. The default
`build/java-diff/` and named `build/java-diff-*/` outputs are Git-ignored. Each run
creates fresh `run-*/compiled/` output and archives its report; no pre-existing
compiled directory is deleted. Top-level report files describe the latest run.

Replay recompiles current source with the current toolchain and uses the named
CLI; it is **not a hermetic snapshot**. Check recorded hashes/versions. Fault-
injection tests verify wrong answers cause failure and recorded replay commands
reproduce them. Exact EVM custom-error checks cover malformed branch/local/stack
cases; the nontermination test verifies real out-of-gas.

## Runtime source and reproducibility

Source: `jvmevm/runtime/JVMSubsetInterpreter.sol`.
Embedded artifact: `jvmevm/runtime/JVMSubsetInterpreter.runtime.hex`.
Pinned solc-js: 0.8.30 (`0.8.30+commit.73712a01`), optimizer 200 runs, `viaIR:true`,
Cancun EVM, CBOR/hash metadata disabled. Source rebuild must match the artifact
byte-for-byte; no global compiler/npm configuration is used.

```sh
make java-runtime-build   # regenerate artifact; review changed runtime/hash
make java-runtime-check   # fail unless source rebuild matches
```

`npm ci --ignore-scripts` installs pinned local build dependencies into ignored
`jvmevm/runtime/node_modules`. The existing audit reports two findings (one low,
one high) through solc's `tmp` dependency, involving temporary-file path/symlink
handling. These remain unremediated build-tool findings, not dependencies in the
EVM bytecode. Do not blindly apply the suggested forced compiler downgrade.

## Git history and next stages

The fork is based on geth v1.16.9 (`95665d5703e1023995a0ff93e4ce9eb77e8a59bd`),
on local branch `java-on-evm`, remote `upstream`; no remote push was made.
Consensus VM core and the M0 host-AOT baseline remain unchanged. M0 is explicitly
**not** the JVM-inside-EVM path; use `make java-aot-demo` / `make java-aot-test`.

Three independent worker worktrees supplied fixtures, runtime and runner;
changes were integrated and verified on the combined revision. Task ownership,
protocol and acceptance evidence: [JAVA_EVM_M2_PLAN.md](JAVA_EVM_M2_PLAN.md).
Broader proposals: [JAVA_EVM_ROADMAP.md](JAVA_EVM_ROADMAP.md). Continuous
parent orchestration is authorized by `JAVA_EVM_PROGRAM.md`. Latest M5d-a acceptance
is recorded in `JAVA_EVM_M5DA_PLAN.md`; next is stock-EVM architecture and Java
bootstrap planning toward the genuine MC startup marker.
No full-Java claim or routine re-confirmation.

## M4b ordinary objects and direct instance calls

713 cumulative JVM/EVM cases plus46 independent object probes passed. Supports
new/getfield/putfield/invokespecial, constructors/this/super/private calls,
I/[I/Lclass; storage/arguments/returns, inherited and hidden instance fields,
reference assignability, final writes and per-frame uninitialized-reference rules.
Synchronized entered methods are explicitly rejected; monitors are not ignored.

A95-byte minimal java/lang/Object.class is embedded, parsed and its constructor
executed inside EVM through ordinary frames. It is appended only if not supplied;
source/hex/embedded bytes are reproducibly checked with javac before solc. No host
shortcut or full Object/JRE API is implied. User bundle limit remains64 classes.

Object limits:1024 objects,1024 instance fields each,65536 total instance slots;
array limits unchanged and independent. Unified handles, no GC, reset each run.
Cached base-first layouts preserve defaults/hidden fields;64 objects with1024
fields use about62.13M gas. OOM caps remain distinct from EVM OOG. ObjectError
rejects unsupported allocation/constructor forms; ReferenceError2 rejects class
assignment mismatch. Root remains static int-only. Runtime remains over EIP-170.

## M4c virtual dispatch and type tests

792 cumulative JVM/EVM cases plus48 independent dispatch/type probes passed.
invokevirtual resolves symbolic methods separately from dynamic selection,
including package-private transitive override rules, protected/final checks,
polymorphic call sites, and callbacks during construction. Actual native/abstract/
synchronized bodies are rejected even when an ordinary override is supported.
Array-receiver virtual calls remain deferred; no broader Object/JRE APIs added.

checkcast/instanceof support ordinary classes, Object and int[]. Null casts retain
null without resolving a well-formed missing target; non-null type resolution
does not initialize the target. Invalid casts produce exact ClassCastException
kind8, wrapped as EIIE when escaping an initializer. Array type names are limited
to255 dimensions structurally; M4d below extends supported array execution.

## M4d reference arrays

892 cumulative JVM/EVM cases plus48 independent reference-array probes passed.
anewarray/aaload/aastore and generic arraylength support class/Object arrays and
nested references such as int[][], assembled one level at a time. Recursive
covariance applies consistently to fields/calls/returns/casts/type tests. Stores
check the actual allocated component type, producing ArrayStoreException kind9
(or EIIE when escaping class initialization); null/bounds precede store checks.
Component classes resolve even for zero/negative lengths but are not initialized;
abstract class components are valid. All new operations remain inside EVM.

Int/reference arrays share1024 total array allocations and262144 total elements,
with65536 per array; object limits are independent. No GC. Structural rank255
is supported; anewarray producing rank256 rejects explicitly. Interfaces and
other primitive leaves remain deferred; no broader Object/JRE APIs added.

## M4e multidimensional allocation

960 cumulative JVM/EVM cases plus48 independent multidimensional probes passed.
multianewarray allocates complete or partial int/reference array ranks, iteratively
inside EVM. All counts are checked for negatives before capacity planning, even
beyond a zero dimension. Only materialized levels consume quotas; empty children
have distinct identities, partial-rank leaves stay null, and rank255 is bounded.
Component resolution/access precedes counts and does not initialize components.
No heap limits, host APIs, exception kinds or deployment claims changed.

## M4f-a abstract interfaces

1059 cumulative JVM/EVM cases plus48 independent interface probes passed.
Interface DAGs/diamonds, transitive implementation, invokeinterface and abstract
interface fallback for class-qualified invokevirtual execute inside EVM. Fields,
calls, casts/type tests and nested arrays use interface-aware compatibility.
Default bodies remain explicitly rejected before class initialization, rather
than ignored; abstract-only interfaces are not initialized by implements/calls.

Minimal Cloneable/Serializable interfaces (71/72 bytes) join Object as verified
raw bootstrap classfiles parsed inside EVM. Array compatibility includes their
superinterface closure, including supplied valid marker definitions. No clone,
serialization or broader Object API is implied. User limit64 remains, up to3
internal bootstrap slots. Array receiver dispatch and interface statics remain
deferred. Legacy interface roots retain MethodError7; bundle roots LinkError5.

## M4f-b defaults and required initialization

1163 cumulative JVM/EVM cases plus48 independent default/init probes passed.
Default selection handles class precedence, maximally-specific interfaces,
abstract suppression and I.super. Class initialization performs superclass then
ordered/deduplicated default-DECLARING interface initialization, including synthetic
bridges, then class <clinit>. Merely inheriting a default does not initialize an
interface. Reentrancy and exact initializer outcomes remain in EVM.

ICCE10/AME11 are canonical Java Errors and remain unwrapped through initializers;
Java8 binary-evolution probes verify their target semantics (Java21 can differ).
Self-owned interface fields are allowed only in that interface's <clinit> for now;
external fields/static calls remain deferred. Earlier M4f-a default rejection was
superseded, not silently bypassed. Native/synchronized/private interface bodies,
array receiver dispatch and broader JRE APIs remain unsupported.

## M4f-c interface static members

1263 cumulative JVM/EVM cases plus48 independent interface-static probes passed.
Interface static methods use exact owner CP11 lookup (not inherited); CP10 remains
class-only. Static int-only roots can now be interfaces in either entry API.
Fields resolve declaration, recursive direct interfaces, then superclass; storage
and initialization follow the actual declaring owner, not the qualifier. Active
interface initialization does not initialize parent interfaces merely as parents.
Cross-calls, reentrancy, public external fields and final/cache checks stay in EVM.
Earlier interface root/static/field deferrals are superseded; invalid kind/staticness/
access/native/synchronized and final-write guards remain. No new JRE API implied.

## M5a narrow int-like primitives

1383 cumulative JVM/EVM cases plus48 independent probes passed. Internal Z/B/C/S
methods, fields, ConstantValue and primitive arrays execute in EVM. Invocation
arguments remain full computational ints; fields/returns narrow by declared type:
byte/short sign extension, char zero extension, boolean lowbit canonicalization.
Array type identity distinguishes all primitive leaves, including byte vs boolean,
with nested/covariant reference behavior preserved. Root API remains EXACT (I...)I.
Existing quotas, exception kinds, bootstrap/API/deployment limitations unchanged.

## M5b-a scalar long/category-2

1493 cumulative JVM/EVM cases plus48 independent probes passed. Scalar long
constants/fields/calls/returns/arithmetic/conversions execute in EVM with exact64
bits. JVM word depth/locals/call offsets and b9 counts account for category2;
overlapping local stores invalidate old long pairs, all stack forms preserve whole
values. Signed MIN/-1 and shift masking verified against Java8. Root remains exact
(I...)I. Long arrays/IEEE/handlers are still deferred; quotas and outcomes unchanged.

## M5b-b long arrays

1593 cumulative JVM/EVM cases plus48 independent probes passed. Long arrays store
full64-bit cells; laload/lastore preserve category2 values and word bounds. Nested
types/covariance/markers/casts/stores/calls/fields and initialization remain in EVM.
One long is one Java ARRAY ELEMENT, despite two stack words. Shared-cap probe
still allocates1024 arrays+1024 objects at250M budget, using zero-field Object to
isolate quotas from unrelated guest constructor work (~160.39M gas used).
Root remains exact(I...)I; IEEE/handlers/JRE/deployment limitations remain.

## M5c-a variable-width instructions

1681 cumulative JVM/EVM cases plus48 independent probes passed. tableswitch,
lookupswitch,goto_w and wide int/long/reference locals/iinc execute inside EVM.
Two-pass predecode validates every target, including untaken edges; padding and
wide operands never become instruction starts. Alignment, signed keys/offsets,
wide indices/increments and category2 overlap rules are preserved. Nonzero switch
padding verified with original major52 Code/StackMapTable on Java8 and21.

Generic predecode/start-map and iinc dispatch optimization reduced a large backward
case from166.31M to88.41M gas, without changing its bytecode, inputs or100M budget.
No skipped instructions/AOT or new heap limits. IEEE/handlers/JRE remain staged.

## M5c-b scalar IEEE and four raw-bit services

1811 cumulative JVM/EVM cases plus216 independent boundary/random probes passed.
Scalar F/D constants/fields/typed transport, wide locals, comparisons, sign negation
and all ten conversions use EVM integer/bit algorithms. RNE, subnormals, signed zero,
infinities, integer saturation and NaN policies are explicit. Independent probes
found and fixed unsigned f2d exponent rebias underflow for normal values below1.

Only four exact selected public-static-native raw-bit declarations bind to EVM
services: Float.intBitsToFloat/floatToRawIntBits, Double.longBitsToDouble/
doubleToRawLongBits. No host math/JNI/precompile; user-supplied ordinary Code is
not intercepted. Minimal Float/Double raw class images are parsed like the existing
three bootstraps (64 user classes + at most5 internal). No boxed Float/Double,
Number hierarchy or broader JRE APIs. Pure transport preserves payload; conversion
NaNs canonicalize; cross-JVM signaling-NaN raw parity is not claimed. FP arithmetic/
arrays remain deferred, root protocol remains exact(I...)I.

## M5c-c software IEEE arithmetic

1971 cumulative JVM/EVM cases plus960 parent bit-level probes passed. Scalar F/D
add/sub/mul/div/Java remainder use EVM integer algorithms, RNE and gradual underflow,
with exact finite/signed-zero results and canonical generated NaNs. Java remainder
uses exact truncating-quotient binary modulus, not rounded division/IEEE nearest
remainder; exponent reduction is bounded/logarithmic. No host math/new native APIs.
Independent worst single op ~1.45M/20M gas,16 repeated drem ~4.77M/100M. Raw transport
NaN policy remains separate. FP arrays/handlers/JRE are still staged.

## M5c-d IEEE arrays

2091 cumulative JVM/EVM cases plus192 independent raw-cell probes passed. All
primitive array types now have typed element operations, including exact F32/D64
load/store without arithmetic NaN canonicalization. Positive-zero defaults, signed
zeros, quiet NaN payloads, nesting/covariance/markers and category2 double elements
are preserved. One double remains one Java array element for shared quotas.
Signaling-NaN transport guarantee remains EVM-specific, not cross-JVM parity.
At that checkpoint handlers/athrow/Throwable APIs were pending; M5d-a below adds
handlers/rethrow. Root still exact(I...)I, no host math.

## M5d-a implicit exceptions, handlers and unwind

2231 cumulative JVM/EVM cases,179 parent Java8/21/EVM probes,8 additional Java8
initialization regressions and an EVM-only field-arena boundary passed; prior192
IEEE-array probes retained. All modeled implicit faults are catchable in guest
code, with classfile-order/half-open handler ranges, cleared operand stack, retained
locals, invocation-PC unwind and captured-reference identity on athrow. Null athrow
raises NPE. Invalid bytecode/profile errors and EVM OOG remain uncatchable.

19 new canonical raw Throwable bootstrap images (24 total) parse in EVM on demand.
64 user classes maximum remains. A separate256-record exception arena plus emergency
OOM shares heap identity while ordinary object/array quotas remain unchanged. Its
262144-field budget includes inherited Object fields and emergency storage; no GC.
Templates/validated hierarchy are cached, mutable guest objects never share templates.
Handler tables cap256; unsupported matching pre-chain constructor handlers reject
HandlerError8. This is not a full verifier or general user Throwable implementation.

Initialization handlers run before wrapping. Escaping non-Error becomes EIIE once;
Error retains identity, failed prerequisites mark dependents erroneous, subsequent
active use raises NCDFE12. Parent found and fixed the already-failed default-interface
case even after2231 fixed cases passed. Unentered root handlers cannot catch root
initialization failure. Exact known uncaught ABI kinds1..12 remain host-decoded only.

No fresh Throwable/API/String/main/JRE/deployment/MC claim. Standard-EVM modular
execution and Java bootstrap preflights guide the next bounded stages; see program.

## Separate S0 stock transaction/continuation foundation

```sh
make java-stock-test   # pinned artifacts, JVM, signed/direct replay and negatives
make java-stock-demo   # ordinary CREATE + 3 resume transactions -> Java result12
```

The11132-byte generic step module and3724-byte coordinator template fit ordinary
CREATE limits; exact unchanged classfiles live in STOP-prefixed code pages. The
canonical177-byte class returns12 over3 resumes after3 deployments,4234189 positive
aggregate gas including transactions/code deposit. An extra stale-epoch transaction
fails without changing the VM checkpoint; normal sender nonce/gas effects remain.

This is a deliberately separate straight-line Java-int subset with initialized
locals, int32 overflow, canonical stored stack/state and hash/epoch commitments.
Eight trusted fixtures run under step budgets1/3/16 on signed in-process chains
and direct signed-transaction replay. Parent80 Java8/21 probes,42 gas thresholds
and the reviewed full-CP/full-Code boundary passed. Two real gas-boundary defects
were fixed, not hidden by higher limits. See JAVA_EVM_STOCK_S0_REVIEW.md.

S0 does NOT make all2231 M5d-a cases deployable, supply a persistent general JVM,
or reach Minecraft startup. Those remain separate migration/library milestones.

## Stock S1: real legacy workloads and reusable metadata

```sh
make java-stock-s1-test
make java-stock-s1-demo
```

S1 runs ALL82 unchanged M1/M2 rows (5rawclasses/39named roots), not wrappers or
host-derived offsets. EVM parses each class once, creates an immutable metadata
page, selects `(I...)I` entries and initializes arguments. Signed resumes preserve
up to8locals, int32 arithmetic and branch/loop state; even unchanged PC can be real
progress. A committed instruction cap produces STEP_LIMIT, never a fake Java value.

The parser15271bytes, stepmodule8408bytes and coordinator6328-byte template obey
ordinary deployment limits. At128-step quantum, sum(100) returns5050 after7resumes
(806instructions), fibonacci(30) returns832040 after3resumes (368instructions).
Isolated full setup+execution costs respectively10324488 and9055443gas; these are
NOT the old monolith's per-invocation budgets. Five parsed pages are reusable.

JVM8/21, signed/direct replay, catalogue/root/trace checks,48parent loop probes,
52gas thresholds and maximum metadata registration all pass. Parent fixed a real
registration cost issue and corrected an invalid quota fixture without increasing
caps. Original2231 cases and S0 remain green and counted separately.

This is still single-class, one-frame Java-int execution: no static calls, general
heap, long/FP, handlers, libraries or MC startup on this stock path yet. Those
capabilities in the separate M5d-a monolith are not claimed migrated automatically.
See JAVA_EVM_STOCK_S1_PLAN.md and JAVA_EVM_STOCK_S1_REVIEW.md for exact evidence.

## Stock S2a: integer completion and terminal Java faults

```sh
make java-stock-s2a-test
make java-stock-s2a-demo
```

All201 original M1/M2/M2b rows now run on the ordinary-deployed stock path:
199 values and2 ArithmeticException outcomes,60roots/11classes. Added division,
remainder, signed/unsigned shifts, bitwise operations and narrow conversions retain
Java int32 rules, including MIN/-1. A zero divisor records JAVA_FAULT with the
actual opcode PC and preserved pre-fault operands/locals; it is not a returned0,
EVM revert/OOG or STEP_LIMIT. Fault at exact instruction cap wins; cap before the
fault does not predict it.

Parser15659bytes, step9470bytes and coordinator7694-byte template remain within
stock deployment limits. Signed/JVM8/JVM21/direct-replay tests,312parent arithmetic/
prefix/cap probes and independent review pass. Existing2231 andS0/S1 gates remain
green and counted separately. No runtime defect or artifact change was required
in parent integration; a catalogue verifier's null-vs-numeric-zero assumption was
corrected with stricter lifecycle/operand checks.

S2a is still one frame, without calls, heap, Throwable objects/handlers or libraries.
Next frame-storage and call-metadata prototypes must establish safe gas/dirty
budgets. This is not a Minecraft startup or full-interpreter deployment claim.
