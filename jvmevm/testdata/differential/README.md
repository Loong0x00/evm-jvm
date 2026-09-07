# Differential fixtures (schema v1)

These fixtures are inputs to the staged Java-inside-EVM differential runner.
`OracleMain.java` is a host-test-only reflection wrapper; it is not a guest
entry point and is never sent to the EVM interpreter.

The manifest has 268 fixed cases: 12 `m1`, 70 `m2`, 119 `m2b`, and 67
`m3a` cases. The 55 smoke cases include 20 from `m3a`. Every root entry remains
a uniquely named static `(int...)int` method, and guest sources have no `main`.
The M3a roots call same-class static helpers with int parameters and int or void
returns; helpers may be private or overloaded, but root names are unambiguous.
The fixtures have no class initializers, exception handlers, objects, arrays,
fields, `wide`, `switch`, external positive calls, or unsupported stack
permutation instructions.

M2b covers integer `ldc`/`ldc_w`, multiply, divide, remainder, negate, signed
and unsigned masked shifts, bitwise operations, and byte/char/short conversions.
Cases include int32 overflow and extrema, all dividend/divisor sign combinations,
`INT_MIN / -1`, negative and large shift distances, and conversion boundaries.
The two explicitly expected uncaught Java outcomes are:

- `m2b-idiv-zero-divisor`
- `m2b-irem-zero-divisor`

Both declare `expected_kind: "java_exception"` and
`expected_exception: "java.lang.ArithmeticException"`.

M3a adds 62 value outcomes and five actual JVM exception outcomes. It exercises
declaration-order argument transfer (up to six arguments), zero-argument and
private helpers, exact descriptor selection among internal overloads, nested
calls, caller operand-prefix and local isolation, int and void returns, discarded
int results, direct and mutual recursion, factorial, and recursive Fibonacci up
to 10. Four cases propagate `java.lang.ArithmeticException` from a callee:

- `m3a-call-callee-divide-zero`
- `m3a-call-callee-remainder-zero`
- `m3a-call-nested-divide-zero`
- `m3a-void-callee-divide-zero`

`m3a-recursive-stack-overflow` has no guest catch or base case and expects the
actual reference class `java.lang.StackOverflowError`; its subprocess remains
bounded by the manifest's 10-second timeout. The M3a runtime contract represents
this as JavaException kind 2 when its 128-active-frame cap is exceeded. In total,
the manifest has 261 value outcomes, six ArithmeticException outcomes, and one
StackOverflowError
outcome. `OracleMain` reflectively invokes the selected root and reports the
actual return value or thrown cause class; it does not contain fixture answers.

Compile the Java 8 fixtures and invoke representative reference outcomes with:

```sh
out="$(mktemp -d)"
javac --release 8 -d "$out" jvmevm/testdata/differential/*.java
java -cp "$out" OracleMain IntegerArithmetic multiply -7 6
java -cp "$out" OracleMain IntegerArithmetic divide 7 0
java -cp "$out" OracleMain IntegerConversions toChar -1
java -cp "$out" OracleMain M3aStaticCalls multiArgumentOrder 1 2 3
java -cp "$out" OracleMain M3aFrames discardInt 37
java -cp "$out" OracleMain M3aRecursion recursiveFibonacci 10
java -cp "$out" OracleMain M3aRecursion unboundedRecursion 0
rm -rf "$out"
```

Inspect the selected bytecode families and the deliberately high constant-pool
index with:

```sh
out="$(mktemp -d)"
javac --release 8 -d "$out" jvmevm/testdata/differential/*.java
for class in M1Baseline Constants LocalsAndArithmetic Comparisons Loops \
    IntegerConstants IntegerArithmetic IntegerShifts IntegerBitwise \
    IntegerConversions M3aStaticCalls M3aFrames M3aRecursion; do
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

The selected M3a methods use only the accepted M2b instruction set plus
`invokestatic` (`0xb8`), void `return` (`0xb1`), and category-1 `pop` (`0x57`).
Inspect private helpers as well as public roots: calls and recursion depend on
helper bytecode and exact name-and-descriptor resolution. Ordinary javac
constructors remain unselected and contain `invokespecial` as noted above.

M3a runtime and verifier are integrated: all 268 cases passed actual JVM/EVM
comparison on one generic interpreter, including callee ArithmeticExceptions
and StackOverflowError. Prior 201 entries remain unchanged. See
`JAVA_EVM_M3A_PLAN.md` for independent acceptance. This is subset verification,
not full JVM conformance.
