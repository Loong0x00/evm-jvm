# Java on EVM: M0

This local harness demonstrates a real path from Java source to execution in the
geth EVM:

```sh
make java-demo
# or explicitly:
mkdir -p build/java-evm
javac --release 8 -d build/java-evm examples/java/Add.java
go run ./cmd/javaevm -class build/java-evm/Add.class -method add -args 20,22 -gas 100000
```

The command prints standard EVM **runtime bytecode**, the signed Java `int`
result, and measured EVM gas. It executes through `core/vm/runtime.Execute`,
not through the host Java runtime. The `java` tool is only used by tests as a
compiler/oracle boundary.

## M0 subset and limits

The selected method must be an unambiguous `static` method with only `int`
arguments and an `int` return. Its `Code` attribute may contain only `iload`
(including `_0` through `_3`), `iadd`, and `ireturn`. The translator ignores
unused methods, such as javac's default object constructor. Unsupported selected
method bytecodes, malformed classfiles, bad argument counts, and EVM out-of-gas
return clear errors.

Each Java `int` is masked to 32 bits after a load and addition, so addition
wraps and negative operands/results have Java `int32` semantics. Arguments are
32-byte calldata words; one generated program is reusable with different
arguments. This is a local EVM harness, not on-chain deployment, a general
classfile reader, a class library, or a complete JVM.

## Tests

```sh
make java-test
```

Focused tests compile Java 8 classfiles and execute them in geth's EVM. They
cover `20+22`, negative operands, `INT_MAX+1`, code reuse with dynamic arguments,
unsupported `imul`, malformed/truncated class input, and out-of-gas.

## Provenance and next steps

Based on go-ethereum upstream tag `v1.16.9`, commit
`95665d5703e1023995a0ff93e4ce9eb77e8a59bd`. M0 changes no consensus VM core.
Possible future milestones only: constants/subtraction, comparisons/loops,
static calls, then heap/objects.
