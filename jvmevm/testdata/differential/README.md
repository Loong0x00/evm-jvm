# Differential fixtures (schema v1)

These fixtures are inputs to the staged Java-inside-EVM differential runner.
`OracleMain.java` is a host-test-only reflection wrapper; it is not a guest
entry point and is never sent to the EVM interpreter.

The manifest has 201 fixed cases: 12 `m1`, 70 `m2`, and 119 `m2b` cases. The
35 smoke cases include 19 from `m2b`. Guest entry methods are dependency-free
static `(int...)int` methods with unique names. They have no `main`, overloads,
class initializers, invocations, exception handlers, arrays, stack permutation,
`wide`, or `switch` instructions.

M2b covers integer `ldc`/`ldc_w`, multiply, divide, remainder, negate, signed
and unsigned masked shifts, bitwise operations, and byte/char/short conversions.
Cases include int32 overflow and extrema, all dividend/divisor sign combinations,
`INT_MIN / -1`, negative and large shift distances, and conversion boundaries.
The two explicitly expected uncaught Java outcomes are:

- `m2b-idiv-zero-divisor`
- `m2b-irem-zero-divisor`

Both declare `expected_kind: "java_exception"` and
`expected_exception: "java.lang.ArithmeticException"`. `OracleMain` still
reflectively invokes the guest method and reports the actual thrown cause class;
it does not contain fixture answers.

Compile the Java 8 fixtures and invoke representative reference outcomes with:

```sh
out="$(mktemp -d)"
javac --release 8 -d "$out" jvmevm/testdata/differential/*.java
java -cp "$out" OracleMain IntegerArithmetic multiply -7 6
java -cp "$out" OracleMain IntegerArithmetic divide 7 0
java -cp "$out" OracleMain IntegerConversions toChar -1
rm -rf "$out"
```

Inspect the selected bytecode families and the deliberately high constant-pool
index with:

```sh
out="$(mktemp -d)"
javac --release 8 -d "$out" jvmevm/testdata/differential/*.java
for class in M1Baseline Constants LocalsAndArithmetic Comparisons Loops \
    IntegerConstants IntegerArithmetic IntegerShifts IntegerBitwise \
    IntegerConversions; do
  javap -classpath "$out" -c -p "$class"
done
javap -classpath "$out" -v -p WideIntegerConstant \
  | sed -n '/public static int loadWide/,/LineNumberTable/p'
rm -rf "$out"
```

`WideIntegerConstant.loadWide` is javac-produced `ldc_w` referencing a
`CONSTANT_Integer` at an index greater than 255. Its preceding unselected
static int helper deliberately populates the pool, and the class has no
`<clinit>`. As with every ordinary compiled Java class here, javac also emits an
unselected `Object` constructor containing reference/call opcodes; constructors
are not guest entries and are distinct from the inspected selected methods.

The M2b runtime and exception-aware harness are now integrated. All 201 cases
passed JVM/EVM comparison on the same generic interpreter, including two explicit
ArithmeticException cases. Run `make java-full`; see `JAVA_EVM_M2B_PLAN.md` for
independent acceptance. This is subset verification, not full JVM conformance.
