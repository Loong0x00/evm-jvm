# Differential fixtures (schema v1)

These fixtures are inputs to the staged Java-inside-EVM differential runner.
`OracleMain.java` is a host-test-only reflection wrapper; it is not a guest
entry point and is never sent to the EVM interpreter.

The manifest has 82 fixed cases: 12 `m1` baseline cases and 70 `m2` cases.
Guest methods are dependency-free static `(int...)int` methods with unique
names. They have no `main`, overloads, class initializers, invocations, or
exception handlers.

Compile and inspect the emitted Java 8 bytecode with:

```sh
out="$(mktemp -d)"
javac --release 8 -d "$out" jvmevm/testdata/differential/*.java
for class in M1Baseline Constants LocalsAndArithmetic Comparisons Loops; do
  javap -classpath "$out" -c -p "$class"
done
rm -rf "$out"
```

Only selected static guest methods count toward the interpreter opcode set;
ordinary Java classes also contain javac's unselected `Object` constructor.
The selected methods collectively emit exactly the approved M1/M2a families:
integer constants, loads/stores, `iadd`, `isub`, signed-byte `iinc`, unary and
binary integer conditionals, `goto`, and `ireturn`.
