# Java inside EVM: staged interpreter (M2a)

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
make java-smoke      # 16 fixed JVM/EVM differential cases
make java-fast       # smoke + 20 seeded cases (36 total)
make java-full       # all 82 differential cases
make java-test       # artifact check + Go tests + 11 runner tests + all 82 cases
```

Go 1.24+, a JDK supporting `javac --release 8`, and make are needed for the demo.
Python 3 is needed for differential tests. Node/npm are needed to rebuild/check
the Solidity artifact (`java-test` includes this check), not for the standalone
CLI or demo. First-time builds may download Go/compiler dependencies.

Stage M1 covers 12 add/identity cases. Stage M2 is cumulative: these 12 plus 70
constant/local/arithmetic/comparison/control-flow cases. Before merging M2, V0
was validated against the unchanged M1 interpreter; M2 then passed the combined
suite. Tests are bounded evidence, not a full JVM conformance suite.

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

One unchanged **7,040-byte** interpreter runtime handles all three programs:

| Raw input / entry | Result | Execution gas |
|---|---:|---:|
| Add.class / add(20,22) | 42 | 55,308 |
| Loops.class / sum(100) | 5050 | 1,043,858 |
| Loops.class / fibonacci(20) | 6765 | 375,429 |

Runtime SHA-256:
`e04f1a026a1d8c656a487223e4b5a1b89532e62ac255feb3d2fd74391dcf9036`

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

Unambiguous static methods, only `int` arguments and an `int` return:

- `iconst_m1` through `iconst_5`, signed `bipush` and `sipush`
- `iload`, `istore`, including their `_0` through `_3` forms
- `iadd`, `isub`, signed-byte `iinc`
- `ifeq`/`ifne`/`iflt`/`ifge`/`ifgt`/`ifle`, corresponding `if_icmp*`
- `goto`, `ireturn` (including early returns followed by other code)

32-bit arithmetic wraps like Java; comparisons are signed. Branch offsets are
signed 16-bit, relative to the instruction address. The interpreter validates
all selected-method instructions, including unreachable instructions, before
execution and rejects branches into operands or outside the code. Loads and
increments check local initialization; stores, stack operations and return
shape are bounded/checked at execution time.

Caps: constant pool 4096 entries; Code 65,535 bytes; selected operand stack and
locals 1024 each. Gas bounds execution and allocation. Method descriptors,
selected Code structure and relevant UTF-8 references are checked. Class
initializers (`<clinit>`), selected synchronized/native/abstract/non-static/
overloaded/no-Code methods and exception tables are rejected.

**Deferred:** `ldc`/`ldc_w` (so not arbitrary literal int constants yet), `ineg`,
multiply/divide/remainder, shifts/bitwise operations, wide/goto_w, switch, other
primitive types, method calls, arrays, heap/objects, exceptions, monitors, dynamic
class loading, class libraries and deployment/Minecraft workflows.

This is not a full JVM verifier: no modified-UTF8 validation, general class
hierarchy/linking/type verification, full control-flow dataflow verification,
or validation of every unused member/attribute/constant-pool relationship.
Inputs should be treated as experimental. A gas-bounded EVM failure is not a
Java exception implementation.

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
Broader proposals: [JAVA_EVM_ROADMAP.md](JAVA_EVM_ROADMAP.md). This batch stops at
V0 + M2a; the next instruction/runtime slice needs a new bounded task.
