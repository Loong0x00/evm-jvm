# Java inside EVM: tiny interpreter (M1)

This fork contains a generic JVM-subset interpreter compiled to ordinary EVM
runtime bytecode. At run time the host reads a complete, unchanged `javac`
`.class` file and ABI-encodes those raw bytes together with an entry-method name
and signed `int` arguments. The EVM runtime itself scans the classfile and
constant pool, selects and validates the method and `Code` attribute, dispatches
JVM instructions, and returns the result. The host does not parse, extract,
predecode, translate, specialize, or evaluate Java on this path.

This is a **tiny JVM subset, not a full JVM or Java SE implementation**.

Prerequisites are Go 1.24+, a JDK supporting `javac --release 8`, Node/npm, and
make. The checked-in interpreter artifact makes the demo runnable without a
Solidity compiler install:

```sh
cd /home/user/evm-jvm/geth
make java-demo
```

Representative output from this tree is:

```text
engine=evm-jvm-subset-interpreter
runtime_bytes=5044
runtime_sha256=e93a3281bde126b8ea87972d75e0ac03a53d0de17fbffb6402fce9764bec2c20
result=42
gas_used=46391
```

Gas is measured by geth for the runtime call, including ABI decoding,
classfile parsing, method lookup, and JVM dispatch. It excludes deployment,
transaction intrinsic gas, and calldata transaction fees.

Build the standalone CLI and reuse the exact same interpreter with different
raw classes and arguments:

```sh
go build -o build/bin/jvmevm ./cmd/jvmevm
mkdir -p build/java-evm-interpreter
javac --release 8 -d build/java-evm-interpreter \
  examples/java/Add.java examples/java/Identity.java

build/bin/jvmevm -class build/java-evm-interpreter/Add.class \
  -method add -args 2147483647,1
# result=-2147483648

build/bin/jvmevm -class build/java-evm-interpreter/Identity.class \
  -method identity -args=-123
# same runtime_sha256, result=-123
```

The CLI only reads the named file and calls `jvmevm.Run`, which uses geth's ABI
encoder and `core/vm/runtime.Execute`. Invalid class bytes and unsupported Java
instructions therefore fail with an EVM revert and Solidity custom-error data,
not a host classfile-parser error. `-gas` is a finite EVM gas limit; insufficient
gas is reported as an actual EVM out-of-gas failure.

## Supported semantics and defensive limits

The selected method must have an unambiguous name, be `static`, accept only
`int` arguments, and return `int`. Its code can contain only:

- `iload` and `iload_0` through `iload_3`
- `iadd`
- `ireturn`

The interpreter uses 32-bit stack values and unchecked 32-bit addition, giving
Java `int` wraparound and signed return behavior. It checks classfile bounds,
constant-pool tags and relevant UTF-8 references, method/descriptor/access
requirements, argument/local/stack bounds, terminal return shape, and selected
`Code` structure. Constant pools are capped at 4096 entries and selected
`max_stack` at 1024.

Selected native, abstract, synchronized, non-static, overloaded, no-Code, or
exception-table methods are rejected. A class declaring `<clinit>` is rejected
because class-initialization semantics are absent. `imul` and every other JVM
opcode are rejected by the EVM dispatcher.

This is not a JVM verifier. It does not validate modified-UTF8 encoding,
constant-pool relationships irrelevant to selection, class hierarchy or type
safety, unused methods, most class/field/nested attributes, StackMapTable, or
all JVM access/linking rules. There are no branches, loops, constants,
subtraction, calls, arrays, heap/objects, exceptions, monitors, class loading,
class libraries, on-chain deployment workflow, or Minecraft. Inputs remain
resource-bounded by EVM gas, but should be treated as experimental.

## Runtime source and reproducibility

Source is `jvmevm/runtime/JVMSubsetInterpreter.sol`; the checked-in generic
runtime is `JVMSubsetInterpreter.runtime.hex`. Its compiler is pinned by
`package.json` and `package-lock.json` to solc-js 0.8.30
(`0.8.30+commit.73712a01`). The build uses the standard JSON interface with:

- optimizer enabled, 200 runs
- `viaIR: true`
- `evmVersion: cancun`
- metadata CBOR and metadata bytecode hash disabled

No global npm configuration or globally installed compiler is used. Rebuild or
check exact source/artifact consistency with:

```sh
make java-runtime-build   # regenerates the reviewed artifact
make java-runtime-check   # fails unless source rebuild is byte-for-byte equal
make java-test            # consistency check, focused tests, and CLI build
```

`npm ci --ignore-scripts` installs only the lockfile-pinned local build
dependencies under `jvmevm/runtime/node_modules` (ignored by Git).
The current lockfile audit reports two findings (one low and one high) through
solc's `tmp` dependency, involving temporary-file path/symlink handling. These
Node packages are build-time tools and are not included in the EVM runtime;
the findings have not been remediated. Do not blindly run `npm audit fix --force`
(the suggested compiler downgrade would change this pinned build).

## M0 host-AOT baseline

The earlier M0 experiment remains unchanged in `javaevm/` and `cmd/javaevm/`.
It parses and translates one Java method on the host before EVM execution, so it
is explicitly not the JVM-inside-EVM path. Its commands are retained only as
labeled baselines:

```sh
make java-aot-demo
make java-aot-test
```

Neither path changes geth's consensus VM core. The M1 interpreter path is the
primary `make java-demo` / `make java-test` workflow.
