# Differential fixtures (schema v1)

These fixtures are inputs to the staged Java-inside-EVM differential runner.
`OracleMain.java` is a host-test-only reflection wrapper; it is not a guest
entry point and is never sent to the EVM interpreter.

The manifest has 498 fixed cases: 12 `m1`, 70 `m2`, 119 `m2b`, 67 `m3a`,
73 `m3b`, 85 `m3c`, and 72 `m3d` cases. The 165 smoke cases include 37 from
`m3d`. Every root entry remains a uniquely named, declared public static
`(int...)int` method, and guest sources have no `main`. All 426 entries through
M3c, including their source lists, arguments, budgets, tiers, and outcomes, are
unchanged.

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

`m3a-recursive-stack-overflow` expects the actual reference class
`java.lang.StackOverflowError`.

M3b adds 68 value outcomes and five actual JVM exception outcomes over raw,
explicit multi-class bundles. Every M3b case uses a dotted binary root name in
`class` and a nonempty ordered `class_files` list. Lists contain only explicit
relative paths; they neither request nor rely on host dependency discovery.
Repeated cases vary order, including roots first, in the middle, and last.

The M3b fixtures cover:

- direct, overloaded, zero-argument, void, and discarded-result calls;
- caller locals, operand prefixes, argument order, overflow, and nested frames;
- equal `shared:(I)I` private Methodrefs at constant-pool index 7 in both
  `bundle.isolation.Alpha` and `bundle.isolation.Beta`, plus same-signature calls
  to different owners from one root;
- multi-hop and bounded cyclic `LayerOne -> LayerTwo -> LayerThree -> LayerOne`
  calls, and modest two-class recursion;
- public calls across packages; package/protected calls and a nonpublic class
  within one package; and same-class private helpers while that class is bundled;
- cross-class propagation of real reference-JVM arithmetic and stack-overflow
  outcomes.

The four new arithmetic cases explicitly expect
`java.lang.ArithmeticException`:

- `m3b-error-cross-divide-zero`
- `m3b-error-nested-divide-zero`
- `m3b-error-nested-remainder-zero`
- `m3b-error-void-divide-zero`

`m3b-recursion-stack-overflow` explicitly expects
`java.lang.StackOverflowError`.

M3c adds 78 value outcomes and seven actual JVM exception outcomes over 28 new
trusted Java 8 classes. It covers legacy single-class and explicit bundle paths,
zero-prepared and mutable static `int` fields, `getstatic`, `putstatic`, javac's
category-1 `dup` post/preincrement shapes, int32 overflow, and fresh process/VM
state. Bundles exercise public, package, and private-owner accesses, cross-package
public access, same-named fields in independent owners, class-local state and
class-file input permutations.

Initialization cases cover root initialization with pending arguments, computed
final fields, helper calls, repeated active use exactly once, self-reentrant
prepared-default reads, A/B cycles in both first-use orders, and initialization
before an actual get, put, or call while caller operands/arguments remain live.
Supplied but unused failing initializers are not run. `ConstantHolder.VALUE` and
`M3cStatics.COMPILED_CONSTANT` are genuine javac `ConstantValue` declarations,
but their Java-source reads compile to constants and therefore are deliberately
**not** claimed as `getstatic` coverage. Exact `ConstantValue`-plus-`getstatic`
coverage requires the separately owned test-only raw-classfile mutations.

Five M3c cases expect a genuine
`java.lang.ExceptionInInitializerError`: two root-initialization probes, two
nested-owner probes, and one ordinary-helper-during-initialization probe. One
case keeps arithmetic outside initialization as
`java.lang.ArithmeticException`; one recursive initializer expects the unwrapped
`java.lang.StackOverflowError`. `OracleMain` reports genuine
`ExceptionInInitializerError` and `StackOverflowError` outcomes thrown directly
by `Class.forName`, while class-not-found and reflection/configuration failures
remain nonzero stderr failures.

M3d adds 68 value outcomes and four actual JVM exception outcomes over 30 new
trusted Java 8 classes. Its two- and three-level ordinary-class hierarchies cover:

- exact first-match resolution for inherited and hidden static fields/methods,
  plus one- and two-`int` overload descriptors;
- one declaring-owner field slot observed and mutated through sibling subclasses;
- inherited field, int-method, and void-method active use through symbolic
  children, including a child whose own initializer would fail, proving that the
  resolved declaring owner—not merely the symbolic child—is initialized;
- superclass-before-subclass traces, a middle class with no `<clinit>`, bundle
  orders with roots first and last, and duplicate fresh-process probes;
- parent initialization reads and calls into a child already marked initializing,
  observing the child's prepared default before its initializer completes;
- same-package protected static access, cross-package protected static access by
  a subclass, and public inherited members declared by a nonpublic ancestor and
  referenced externally through its accessible public child.

Three cases expect `java.lang.ExceptionInInitializerError` from arithmetic in a
parent initializer before the child initializer can run. One separate hierarchy
case expects `java.lang.ArithmeticException` from division in entered ordinary
method code, outside initialization.

`ReentrantChild.COMPILED_CONSTANT` has a real `ConstantValue` attribute and is
prepared before parent initialization. However, javac compiles the Java-source
read in `ReentrantParent` to `bipush 7`; it does **not** emit `getstatic` and is
therefore not claimed as source-level proof of ConstantValue-before-parent
visibility. The independently owned verifier must redirect a valid raw
Fieldref/getstatic in test-only class bytes to test that timing rule.

Across all stages there are 475 value outcomes, 12 ArithmeticException outcomes,
three StackOverflowError outcomes, and eight ExceptionInInitializerError outcomes.
Every gas limit is finite and at most 50,000,000; every subprocess timeout is at
most 10 seconds.

All entered M3b classes are Java 8 classfile version 52 ordinary classes whose
direct superclass is `java/lang/Object`. They have zero fields, zero interfaces,
and no `<clinit>`. Entered methods use only the accepted M2b instruction set plus
M3a `invokestatic`, void `return`, and category-1 `pop`. As with ordinary javac
classes, unselected constructors contain `invokespecial Object.<init>`.

Compile every trusted fixture and invoke representative dotted-name reference
outcomes with:

```sh
out="$(mktemp -d)"
find jvmevm/testdata/differential -name '*.java' -print0 \
  | xargs -0 javac --release 8 -d "$out"
java -cp "$out" OracleMain IntegerArithmetic multiply -7 6
java -cp "$out" OracleMain M3aRecursion recursiveFibonacci 10
java -cp "$out" OracleMain bundle.basic.BasicRoot direct 17
java -cp "$out" OracleMain bundle.cross.CrossRoot crossPackageNested 12
java -cp "$out" OracleMain bundle.errors.ErrorRoot nestedDivide 1 0
java -cp "$out" OracleMain bundle.recursion.RecursionRoot crossStackOverflow 0
java -cp "$out" OracleMain bundle.m3d.resolve.ResolveLeaf overloadDescriptors 3 4
java -cp "$out" OracleMain bundle.m3d.owner.OwnerRoot fieldThroughFailingChild 9
java -cp "$out" OracleMain bundle.m3d.reentrant.ReentrantChild childCompleted 2
java -cp "$out" OracleMain bundle.m3d.external.HiddenAccessRoot publicInheritedField 3
java -cp "$out" OracleMain bundle.m3d.errors.FailureChild entry 0
rm -rf "$out"
```

Inspect every new class (including private helpers), class metadata, and the two
same-index isolation references with:

```sh
out="$(mktemp -d)"
find jvmevm/testdata/differential -name '*.java' -print0 \
  | xargs -0 javac --release 8 -d "$out"
find "$out/bundle" -name '*.class' -print | sort | while read -r file; do
  class="${file#"$out"/}"; class="${class%.class}"; class="${class//\//.}"
  javap -classpath "$out" -c -v -p "$class"
done
javap -classpath "$out" -c -v -p M3cStatics
javap -classpath "$out" -c -p bundle.isolation.Alpha bundle.isolation.Beta
find "$out/bundle/m3d" -name '*.class' -print | sort | while read -r file; do
  class="${file#"$out"/}"; class="${class%.class}"; class="${class//\//.}"
  javap -classpath "$out" -c -v -p "$class"
done
rm -rf "$out"
```

A full local reference compile and 498 fresh `OracleMain` JVM invocations passed
for this fixture revision. This checks each manifest result against the actual JVM
rather than storing hardcoded value answers. The resulting outcomes were 475
values, 12 `ArithmeticException`, three `StackOverflowError`, and eight
`ExceptionInInitializerError` results.

`javap -c -v -p` over the 30 M3d classes found 19 `<clinit>` methods, one
`ConstantValue` attribute, and aggregate instruction shapes of 58 `getstatic`,
41 `putstatic`, and 35 `invokestatic`. Sixteen classes have a supplied ordinary
superclass and fourteen directly extend `java/lang/Object`; all declare zero
interfaces. Every entered descriptor uses only `int` and `void`, and all
non-constructor methods stay within the frozen M3c instruction profile plus the
accepted M3a/M3b static-call operations. The 30 ordinary javac-generated,
unentered constructors contain the only `aload_0`/`invokespecial` constructor
calls. No entered instance call, allocation, reference-array, handler, or
interface path is introduced.

For the prior M3c set, `javap -c -v -p` over its 28 classes found 18 `<clinit>`
methods, two `ConstantValue` attributes, and aggregate field shapes of 83
`getstatic`, 57 `putstatic`, and seven `dup` instructions. Those classes directly
extend `java/lang/Object` and declare no interfaces.

`WideIntegerConstant.loadWide` remains the javac-produced `ldc_w` fixture with a
`CONSTANT_Integer` index greater than 255. Its unselected pool-populating helper
has no `<clinit>`.

The M3b runtime and verifier are integrated. Its accepted suite remains:

```sh
python3 tools/java_diff.py --stage m3b --tier smoke
python3 tools/java_diff.py --stage m3b --tier full
```

All 426 pre-M3d cases pass actual JVM/EVM comparison after M3c parent integration,
including initializers and known Java outcomes. The 72 M3d cases have passing
fresh-process JVM oracle results and classfile-profile evidence; the M3c baseline
runtime cannot execute the new hierarchy cases before the separately owned M3d
runtime/verifier changes are integrated. Earlier 426 entries are unchanged. See
`JAVA_EVM_M3D_PLAN.md` for the frozen integration contract. The runtime is over
mainnet deployment size and used through local runtime.Execute. This remains
subset verification, not full JVM conformance.
