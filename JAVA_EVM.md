# Java inside EVM: staged interpreter (M4c)

A generic JVM-subset interpreter compiled to ordinary EVM bytecode. The host
reads an unchanged `.class` file and ABI-packs raw bytes, an entry name and int
arguments. **Classfile parsing, method lookup, instruction predecode, local/stack
handling, branches, loops and Java computation all execute inside geth's EVM.**
The host does not parse, translate, specialize or evaluate Java on this path.

This is a **limited JVM subset, not full Java or Minecraft**. `javac` and the
Solidity compiler operate at build time. A host JVM is used only as a test oracle.

**Local execution, not mainnet deployment:** the current 74,469-byte runtime
exceeds EIP-170's 24,576-byte deployed-code limit. Geth `runtime.Execute` installs
runtime code directly into its temporary state; no CREATE/deployment is tested.
Execution remains real EVM bytecode, with no host Java fallback or consensus edits.

## Quickstart / stage gates

Run from the fork, not the unrelated home-directory Git repository:

```sh
cd /home/user/evm-jvm/geth
make java-demo       # add(20,22), sum(100), fibonacci(20)
make java-smoke      # 331 fixed JVM/EVM differential cases
make java-fast       # smoke + 20 seeded cases (351 total)
make java-full       # all 792 differential cases
make java-test       # artifact check + Go tests + 34 runner tests + all 792 cases
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

One unchanged **74,469-byte** interpreter runtime handles legacy and bundled inputs:

| Raw input / entry | Result | Execution gas |
|---|---:|---:|
| Add.class / add(20,22) | 42 | 196,581 |
| Loops.class / sum(100) | 5050 | 2,269,737 |
| Loops.class / fibonacci(20) | 6765 | 836,222 |
| BasicHelper + BasicRoot / threeArguments(1,2,3) | 10203 | 511,083 |
| M4aArrays.class / fillSum(10,3) | 165 | 2,067,619 |

Typed checks raised sum(100) beyond its old2M demo budget, independently confirmed;
the demo now uses3M. No historical oracle input/budget or semantic assertion changed.

Runtime SHA-256:
`1e5736e346cea2c55a2aed3963822a1bf9be66eb57c0031b4c64603d64f5c941`

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
helpers can use I/[I/Lclass; parameters and return I/V/[I/Lclass;, and be overloaded):

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
checked. Overloaded root names, entered synchronized/native/abstract/non-static/
no-Code methods and exception tables are rejected; overloaded internal helpers
are supported. `<clinit>` is VM-scheduled, not directly invocable by guest code.

M2b division truncates toward zero; remainder follows Java's sign rules.
INT_MIN/-1 wraps to INT_MIN (remainder zero), shift counts are masked with 31,
and byte/short/char conversions preserve their signed/unsigned Java semantics.

**Deferred:** non-integer constants, wide/goto_w, category-2 values, switch,
other primitive/array types, reference/multidimensional arrays, interface calls,
array-receiver virtual calls, non-I/[I/Lclass; fields, handlers, monitors,
class libraries and deployment workflows.

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
128-frame cap. Kind 1 propagates from callees. These are **uncaught outcomes
only**, not catch/handler support; a lower gas limit can fail OOG first.
Kind 3 is `ExceptionInInitializerError`: genuine arithmetic escaping an active
initializer (including from its helper) is wrapped. StackOverflowError is already
an Error and is not wrapped. OracleMain also records actual root-initialization
errors during Class.forName. Retry after failed initialization, Java exception
objects/causes and thread synchronization are not implemented.

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
parent orchestration is authorized by `JAVA_EVM_PROGRAM.md`. M4c acceptance is
recorded in `JAVA_EVM_M4C_PLAN.md`; next are reference arrays.
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
to255 dimensions structurally; other array types still lack execution support.
