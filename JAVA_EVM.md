# Java inside EVM: staged interpreter (M3a)

A generic JVM-subset interpreter compiled to ordinary EVM bytecode. The host
reads an unchanged `.class` file and ABI-packs raw bytes, an entry name and int
arguments. **Classfile parsing, method lookup, instruction predecode, local/stack
handling, branches, loops and Java computation all execute inside geth's EVM.**
The host does not parse, translate, specialize or evaluate Java on this path.

This is a **limited JVM subset, not full Java or Minecraft**. `javac` and the
Solidity compiler operate at build time. A host JVM is used only as a test oracle.

## Quickstart / stage gates

Run from the fork, not the unrelated home-directory Git repository:

```sh
cd /home/user/evm-jvm/geth
make java-demo       # add(20,22), sum(100), fibonacci(20)
make java-smoke      # 55 fixed JVM/EVM differential cases
make java-fast       # smoke + 20 seeded cases (75 total)
make java-full       # all 268 differential cases
make java-test       # artifact check + Go tests + 21 runner tests + all 268 cases
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
still select historical subsets. Tests are bounded evidence, not conformance.

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

One unchanged **13,343-byte** interpreter runtime handles all three programs:

| Raw input / entry | Result | Execution gas |
|---|---:|---:|
| Add.class / add(20,22) | 42 | 113,895 |
| Loops.class / sum(100) | 5050 | 1,669,146 |
| Loops.class / fibonacci(20) | 6765 | 602,675 |

Runtime SHA-256:
`e5da633eda34db0ce3a02563fd6276c8016525d441025eb446b578fdef8a390b`

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

## Supported semantics and limits

Unambiguous static root, only `int` arguments and an `int` return (internal
helpers can return void and be overloaded):

- `iconst_m1` through `iconst_5`, signed `bipush` and `sipush`
- `iload`, `istore`, including their `_0` through `_3` forms
- `ldc` / `ldc_w` for CONSTANT_Integer, resolved inside EVM
- `iadd`, `isub`, `imul`, `idiv`, `irem`, `ineg`, signed-byte `iinc`
- `ishl`, `ishr`, `iushr`, `iand`, `ior`, `ixor`, `i2b`, `i2c`, `i2s`
- `ifeq`/`ifne`/`iflt`/`ifge`/`ifgt`/`ifle`, corresponding `if_icmp*`
- `goto`, `ireturn` (including early returns followed by other code)
- Same-class tag-10 `invokestatic`, internal void `return`, category-1 `pop`

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
locals 1024 each; 128 active Java frames including root. Gas bounds execution
and allocation. Stack capacity does not claim to match OpenJDK's configuration.
Method descriptors, entered Code structure and relevant UTF-8 references are
checked. Class initializers (`<clinit>`), overloaded root names, entered
synchronized/native/abstract/non-static/no-Code methods and exception tables are
rejected; overloaded internal helpers are supported.

M2b division truncates toward zero; remainder follows Java's sign rules.
INT_MIN/-1 wraps to INT_MIN (remainder zero), shift counts are masked with 31,
and byte/short/char conversions preserve their signed/unsigned Java semantics.

**Deferred:** non-integer constants, wide/goto_w, stack permutation forms, switch,
other primitive types, external/interface/instance calls, multiple-class loading,
static state/initialization, arrays, heap/objects, exception handlers, monitors,
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

Call validation has exact `CallError(code,pc)` payloads: malformed reference (1),
external owner (2), missing exact signature (3), unsupported callee semantics (4),
return-kind mismatch (5). Codes 1–4 locate the caller's invokestatic; code 5
locates the mismatched return within the entered method. These remain EVM errors,
not fabricated Java linkage exceptions.

## Differential verification and replay

Fixtures and host-only oracle: `jvmevm/testdata/differential/`.
Runner and protocol/error tests: `tools/java_diff.py`, `tools/test_java_diff.py`.
Detailed flags/format: [tools/JAVA_DIFF.md](tools/JAVA_DIFF.md).

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
parent orchestration is authorized by `JAVA_EVM_PROGRAM.md`. M3a acceptance is
recorded in `JAVA_EVM_M3A_PLAN.md`; the next stage is raw multiple-class loading
and EVM-side linking, followed by static state/initialization. No full-Java claim
is made and routine per-stage re-confirmation is not required.
