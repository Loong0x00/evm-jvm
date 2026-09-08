# Differential fixtures (schema v1)

These fixtures are inputs to the staged Java-inside-EVM differential runner.
`OracleMain.java` is a host-test-only reflection wrapper; it is not a guest
entry point and is never sent to the EVM interpreter.

The manifest has 1,059 fixed cases: 12 `m1`, 70 `m2`, 119 `m2b`, 67 `m3a`,
73 `m3b`, 85 `m3c`, 72 `m3d`, 115 `m4a`, 100 `m4b`, 79 `m4c`, 100 `m4d`,
68 `m4e`, and 99 `m4fa` cases. The 465 smoke-marked cases include 50 from
`m4fa`. Every root entry remains a declared public static `(int...)int` method,
and guest sources have no `main`. All 960 entries through M4e, including their
source lists, arguments, budgets, tiers, and outcomes, are unchanged.

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

M4a adds 96 value outcomes and 19 actual JVM exception outcomes over 18 new
trusted Java 8 classes. The fixtures cover zero-filled and zero-length arrays,
length/read/write, fill/sum/search, two modest four-element sorts, aliases versus
distinct allocations (including zero-length identity), null comparisons, typed
locals, and same- and cross-class helper parameters and `int[]` returns. The
post/preincrement, assignment-expression, chained-assignment, and compound-
assignment cases deliberately exercise javac's category-1 array stack
permutations.

Static `int[]` fields cover prepared null, assignment/replacement, aliases,
helper returns, initializer-built arrays, and mutable elements reached through a
`final` reference. Bundles cover inherited declaring-owner storage shared by
siblings, access through a failing symbolic child without initializing that
child, class-file order permutations, and modest same-/cross-class recursive
methods carrying array identity through calls. No M4a root accepts or returns a
reference: every selected entry still has only `int` parameters and an `int`
result; internal methods additionally use only `int[]` parameters/results and
`void`.

The 19 M4a exception cases are two genuine
`java.lang.NegativeArraySizeException`, seven
`java.lang.ArrayIndexOutOfBoundsException`, seven
`java.lang.NullPointerException`, and three
`java.lang.ExceptionInInitializerError` outcomes. They include signed negative,
equal-length, and large indices, null reads/writes with invalid indices to prove
null-before-bounds behavior, and separate negative-allocation, null-access, and
bounds failures while an active initializer executes. There is deliberately no
host-JVM heap-exhaustion fixture: M4a's EVM logical array/element caps are not a
reference-JVM OOM contract and belong in focused runtime tests.

M4b adds 91 value outcomes and nine actual JVM exception outcomes over nine new
trusted Java 8 sources, which emit 37 ordinary classfiles. It exercises:

- default `int`, object, and `int[]` instance fields; constructor writes and
  argument order; field assignment/increment stack shapes; aliases, distinct
  objects, null, identity, and replacement;
- ordinary objects and `int[]` values transported through typed and `Object`
  locals, instance/static fields, private instance methods, and static helpers,
  including interleaved object/array allocations and mixed-heap identity;
- private instance helpers with integer/reference arguments and returns, void
  mutation, and bounded recursion, all selected as Java 8 `invokespecial`;
- `this(...)` and `super(...)` constructor chains, constructor-time nested
  allocation, inherited fields, three independently hidden same-name field
  slots, inherited finals, and direct-super selection of the immediate parent's
  implementation under `ACC_SUPER`;
- constructor-assigned and declaration-initialized final instance fields,
  inherited finals, final object/array references, and mutation of their targets;
- prepared-null and mutable static object fields, initializer allocation,
  reentrant prepared-state observation, initializer aliases, superclass-before-
  subclass initialization, initialization on `new`, and once-only initialization;
- valid package-private, protected, and public field/constructor accesses in the
  same package and across packages, plus public static accessors rather than
  excluded public instance calls.

Two cases propagate `java.lang.ArithmeticException` from ordinary constructors,
five propagate `java.lang.NullPointerException` from a constructor, null
`getfield`, null `putfield`, nested null field access, or a null private-special
receiver, and two report `java.lang.ExceptionInInitializerError` when constructor
ArithmeticException/NPE occurs during active class initialization. Value variants
separately prove the same ordinary constructor paths complete normally.

The M4b manifest bundle paths cover exactly these emitted classfiles:

- `bundle/m4b/core/{CoreRoot,CoreCell,CorePair}.class`
- `bundle/m4b/constructors/{CtorRoot,CtorBase,CtorMiddle,CtorChild,CoreToken,DefaultWitness,ArgumentOwner}.class`
- `bundle/m4b/finals/{FinalRoot,FinalHolder,FinalCell,FinalParent,FinalChild}.class`
- `bundle/m4b/init/{InitRoot,InitCell,PreparedOwner,AllocOwner,MutableOwner,ReentrantOwner,InitParent,InitChild,LazyAllocated,OnceObject}.class`
- `bundle/m4b/errors/{ErrorRoot,ErrorCell,NullReadingCtor,FailingParent,FailingChild,ArithmeticInit,NullInit}.class`
- `bundle/m4b/access/api/PublicObject.class`,
  `bundle/m4b/access/base/ProtectedBase.class`,
  `bundle/m4b/access/child/CrossAccessRoot.class`, and
  `bundle/m4b/access/same/{SameAccessRoot,PackageObject}.class`

Every case has an explicit ordered `class_files` bundle, with permutations that
place the entry root first, in the middle, or last. No fixture supplies
`java/lang/Object.class`; M4b and M4c therefore exercise the runtime's separately
owned embedded minimal Object bootstrap path.

M4c adds 71 value outcomes and eight actual JVM exception outcomes over 14 new
trusted Java 8 sources, which emit 44 ordinary classfiles. Its 79 cases cover:

- base, child, grandchild, inherited, and final virtual selection, including
  repeated alternation among dynamic receiver classes at one symbolic call site;
- integer, void, ordinary-reference, `Object`, and `int[]` arguments/returns on
  ordinary object receivers, plus bounded virtual recursion;
- legal cross-package protected calls, the transitive
  `p.A(package) -> p.B(public) -> q.C` override chain, and the contrasting
  `p.A(package) -> q.B -> q.C` non-override gap;
- abstract, native, and synchronized resolved declarations whose dynamically
  selected implementation is ordinary, plus null receiver calls that never
  select the unsupported declaration body;
- constructor-time virtual callbacks that observe derived `int` zero and object
  null defaults before derived field initializers execute;
- ordinary-class, `java/lang/Object`, and `[I` type tests, identity-preserving
  ordinary/array casts, normal true/false combinations, and class/array mismatch
  failures. Java source widening conversions do not emit a redundant
  `checkcast java/lang/Object`; Object target coverage is therefore via genuine
  `instanceof java/lang/Object` instructions.

The eight outcomes are four `java.lang.NullPointerException`, three direct
`java.lang.ClassCastException`, and one
`java.lang.ExceptionInInitializerError` wrapping a cast failure in active class
initialization. No case selects a native or synchronized implementation for a
value outcome, and no actual receiver is an array.

M4d adds 85 value outcomes and 15 actual JVM exception outcomes over seven new
trusted Java 8 sources, which emit 30 ordinary classfiles. Its 100 cases cover
reference-array allocation/defaults/identity/aliases; `Object[]` values holding
ordinary objects, `int[]`, and nested reference arrays; class-array covariance
through widened `Base[]`, `Object[]`, and `Object` references; and recursive
rank/primitive-versus-reference casts and type tests. Both integer and ordinary-
class matrices are assembled one rank at a time (`new int[n][]`, followed by
explicit row allocations); no fixture uses `multianewarray`.

Reference arrays pass through instance, static, and final fields and through
static, private-special, virtual, recursive, and cross-class helper arguments and
returns. Component allocation includes a public cross-package class and abstract
classes. Failing component initializers prove that zero, positive, nested, and
abstract-component `anewarray` operations do not initialize their component.
Separate cases exercise initializer-time allocation and reentrant prepared-null
observation.

The 15 M4d outcomes are two `NegativeArraySizeException`, three
`NullPointerException`, three `ArrayIndexOutOfBoundsException`, three direct
`ArrayStoreException`, two direct `ClassCastException`, and two
`ExceptionInInitializerError` outcomes. The store cases include an actual
`Child[]` widened through `Object[]`, nested-array incompatibility, and explicit
null-before-bounds and bounds-before-incompatible-store ordering.

M4e adds 59 value outcomes and nine actual JVM exception outcomes over six new
trusted Java 8 sources, which emit 22 ordinary classfiles. Every case executes a
real `multianewarray`, directly in its root or in an entered helper or class
initializer. Full and partial rank-two through rank-four int and ordinary-class
arrays cover lengths, defaults, writes, distinct generated children (including
empty children), zero outer/inner/middle dimensions, null partial-rank leaves,
aliasing, and jagged mutation. Rank-three int/reference covariance, casts, type
tests, and nested stores include three `ArrayStoreException` and one
`ClassCastException` outcome. Nested references also cross instance/static/final
fields and static, private-special, and virtual helper arguments and returns.

Component allocation includes abstract and failing-initializer classes without
running component initializers or constructors. Separate holder initializers
allocate int and reference matrices. Dimension expressions prove left-to-right
count evaluation. Four direct `NegativeArraySizeException` cases cover negative
outer/inner counts and later negative counts after a zero outer or middle count;
one initializer-time negative count is reported as
`ExceptionInInitializerError`. Public cross-package component arrays cover full
and partial allocation without host classpath discovery.

M4f-a adds 93 value outcomes and six actual JVM exception outcomes over eight
new trusted Java 8 sources in seven source bundles, which emit 68 classfiles.
Its abstract-only interface graph includes parent/child chains, a shared-parent
diamond, multiple direct
interfaces, transitive class implementations, and a public method inherited from
a superclass that does not itself declare `implements`. Reused call helpers vary
dynamic receiver classes at one `invokeinterface` site. Separate cases cover
bounded interface recursion, integer/void/reference arguments and returns,
interface-typed instance/static fields, public class bridge methods, cross-package
public interfaces, and the `invokevirtual AbstractBase.apply` fallback where the
abstract class has no matching declaration beyond its implemented interface.
Constructor callbacks exercise both that class view and an explicit interface
view before derived field initializers run.

Interface-leaf arrays use both `anewarray` and `multianewarray`, pass through
fields, and exercise class-to-interface array covariance, casts, type tests,
stores, and nulls. Array marker cases cover `Cloneable` and `Serializable`,
including `int[]`, reference arrays, `int[][] -> Cloneable[]` and nested marker
stores; `Object[]` is deliberately not a `Cloneable[]`. Two cases each expect
`ArrayStoreException`, `ClassCastException`, and `NullPointerException`.
Four abstract interface DAG nodes have metadata `<clinit>` methods whose field
initializers could increment an ordinary helper counter, but allocation, calls,
arrays, casts, and tests prove those interfaces remain uninitialized. No entry
reads an interface static field or invokes an interface static method.

Across all stages there are 970 value outcomes, 14 ArithmeticException outcomes,
three StackOverflowError outcomes, 17 ExceptionInInitializerError outcomes, eight
NegativeArraySizeException outcomes, ten ArrayIndexOutOfBoundsException outcomes,
21 NullPointerException outcomes, eight ClassCastException outcomes, and eight
ArrayStoreException outcomes. Every gas limit is finite and at most 70,000,000;
every subprocess timeout is at most 10 seconds. New arrays have at most eight
elements, and all fixture loops and recursions are bounded and modest.

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
java -cp "$out" OracleMain M4aArrays insertionSort 4 3 2 1
java -cp "$out" OracleMain M4aArrays nullRead -1
java -cp "$out" OracleMain bundle.m4a.helpers.ArrayRoot crossClassAlias 71
java -cp "$out" OracleMain bundle.m4a.inheritance.InheritanceRoot siblingSharedWrite 1 99
java -cp "$out" OracleMain bundle.m4a.init.InitRoot helperCalledOnce 0
java -cp "$out" OracleMain bundle.m4a.errors.NegativeInit entry 0
java -cp "$out" OracleMain bundle.m4b.core.CoreRoot privateRecursion 6
java -cp "$out" OracleMain bundle.m4b.constructors.CtorRoot directSuperSelection 5
java -cp "$out" OracleMain bundle.m4b.init.InitRoot reentrantPreparedNull 53
java -cp "$out" OracleMain bundle.m4b.errors.ErrorRoot nullPrivateSpecial 5
java -cp "$out" OracleMain bundle.m4b.access.child.CrossAccessRoot protectedDirectSuper 74
java -cp "$out" OracleMain bundle.m4c.dispatch.DispatchRoot alternatingBaseChild 2
java -cp "$out" OracleMain bundle.m4c.bridgeok.q.C bridgeSelectsC 6
java -cp "$out" OracleMain bundle.m4c.bridgegap.q.C gapKeepsAForC 8
java -cp "$out" OracleMain bundle.m4c.resolved.ResolvedRoot resolvedNativeOverride 63
java -cp "$out" OracleMain bundle.m4c.constructors.ConstructorRoot childSeesNull 72
java -cp "$out" OracleMain bundle.m4c.types.TypeRoot castArrayIdentity -93
java -cp "$out" OracleMain bundle.m4c.types.TypeRoot castSiblingFails 1
java -Xmx64m -cp "$out" OracleMain bundle.m4fa.graph.GraphRoot alternatingDirectChild 5
java -Xmx64m -cp "$out" OracleMain bundle.m4fa.abstractview.AbstractRoot directFallback 7
java -Xmx64m -cp "$out" OracleMain bundle.m4fa.types.TypeRoot intMatrixAsCloneableArray 9
java -Xmx64m -cp "$out" OracleMain bundle.m4fa.init.InitRoot diamondDoesNotInitialize 11
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
javap -classpath "$out" -c -v -p M4aArrays M4aStatics
find "$out/bundle/m4a" -name '*.class' -print | sort | while read -r file; do
  class="${file#"$out"/}"; class="${class%.class}"; class="${class//\//.}"
  javap -classpath "$out" -c -v -p "$class"
done
find "$out/bundle/m4b" -name '*.class' -print | sort | while read -r file; do
  class="${file#"$out"/}"; class="${class%.class}"; class="${class//\//.}"
  javap -classpath "$out" -c -v -p "$class"
done
find "$out/bundle/m4c" -name '*.class' -print | sort | while read -r file; do
  class="${file#"$out"/}"; class="${class%.class}"; class="${class//\//.}"
  javap -classpath "$out" -c -v -p "$class"
done
find "$out/bundle/m4fa" -name '*.class' -print | sort | while read -r file; do
  class="${file#"$out"/}"; class="${class%.class}"; class="${class//\//.}"
  javap -classpath "$out" -c -v -p "$class"
done
rm -rf "$out"
```

A full local reference compile and 613 fresh `OracleMain` JVM invocations passed
for the prior accepted fixture revision. For M4b, seven fresh per-bundle
`javac --release 8` compilations followed by 100 separate `OracleMain` JVM
invocations with a finite 64 MiB heap and per-case timeout all passed. This checks
each manifest result against the actual JVM rather than storing hardcoded value
answers. The M4b run produced 91 values and exactly the nine declared exception
outcomes; the ordered `(case id, value)` results have SHA256
`2bc61e2e626632aa337aaeb845e7c83f3bb0c0ea7de76a2aa39324aaa5a64151`.
The resulting outcomes match the cumulative counts above.

For M4c, one fresh compilation of all 140 trusted fixture sources with
`javac --release 8` was followed by 79 separate `OracleMain` JVM processes, each
with a 64 MiB maximum heap and a ten-second timeout. All 79 matched the manifest:
71 values, four NullPointerExceptions, three ClassCastExceptions, and one
ExceptionInInitializerError. The ordered `(case id, value-or-exception)` results
have SHA256 `6b2eeb6053c5e37959f64621412ecd661e741f414039a6bdeeeb7dda9b75b751`.
The canonical JSON SHA256 of the old 713-entry prefix is
`4a62dba268fcbfdd613203ee191f1cc31643d6b0cf34c6ae358dd92858caab7e`,
identical to the same prefix at the M4b base revision.

For M4d, one fresh compilation of all 147 trusted fixture sources with
`javac --release 8` was followed by 100 separate `OracleMain` JVM processes, each
with a 64 MiB maximum heap and a ten-second outer timeout. All 100 matched the
manifest's outcome kind: 85 values and exactly the 15 declared exceptions. The
ordered tab-separated `(case id, value-or-exception)` results have SHA256
`fa2aa0b03648b68fc938c83acbd08a827321dd025be87b0eaebf277fadcc1ad5`.
The canonical JSON SHA256 of the unchanged old 792-entry prefix is
`daa105cbed3db2d1156bc07b5f6a632c689b53697d64114dcf120b4ee2af8ff9`,
identical to the M4c base revision. The baseline M4c runner intentionally rejects
stage `m4d` and `ArrayStoreException` until the separately owned verifier lands;
these are reference-JVM checks, not an EVM-green claim.

For M4e, one fresh compilation of all 153 trusted fixture sources with
`javac --release 8` was followed by 68 separate `OracleMain` JVM processes, each
with a 64 MiB maximum heap and a ten-second outer timeout. All 68 matched the
manifest: 59 values and exactly the nine declared exceptions. The ordered
`(case id, value-or-exception)` results have SHA256
`dcc917e97b1828f86ac40e0688896b289db21b2cf62bf1a4763d07dfbf17106d`.
The canonical JSON SHA256 of the unchanged old 892-entry prefix is
`194aebc17a953f42c2370748a577e53bb20edb587b88de582e921b66c8115ae0`,
identical to base revision `8b42dc8`.

For M4f-a, one fresh compilation of all 161 trusted fixture sources with
`javac --release 8 -g:none` was followed by 99 separate `OracleMain` JVM
processes, each with `-Xmx64m` and a ten-second outer timeout. All 99 matched the
manifest: 93 values, two `ArrayStoreException`, two `ClassCastException`, and
two `NullPointerException` outcomes. The ordered tab-separated
`(case id, value-or-exception)` results have SHA256
`12fc18ff0a4ff10116ee1d8f25bd450bb97c723d93ab3fab50e180726ed82b60`.
The sorted compact canonical JSON SHA256 of the unchanged old 960-entry prefix
is `11a4d3b361881a262e734ca625398737001ece747a7e87b9eeb1f3c1e43ea7f5`,
identical to base revision `6507e5d`. The baseline runner intentionally rejects
stage `m4fa` until the separately owned runtime and verifier integrate it; these
are trusted reference-JVM checks, not an EVM-green claim.

`javap -c -v -p` over all 22 emitted M4e classes found only Java 8 major version
52 classfiles, zero declared interfaces, and 69 actual `multianewarray`
instructions: 51 with dimensions two, 17 with dimensions three, and one with
dimensions four. The operands name int or ordinary-class array descriptors of
rank two through four, including full and partial allocations. Inspection found
only `int` among `newarray` primitive operands, and no interface/dynamic calls,
monitors, throws, handlers, class literals, or non-Object JRE method references.
Constant-pool call owners retain the intended fixture static, private-special,
and virtual helper owners and nested-array descriptors. Each manifest source
bundle's exact emitted classfile set matches its explicit `class_files` list.

`javap -c -v -p` over all 68 emitted M4f-a classes found only Java 8 major
version 52 classfiles and 20 interfaces. It found 54 `invokeinterface`, 15
`invokevirtual`, eight `multianewarray`, 25 `anewarray`, 18 `checkcast`, and 15
`instanceof` instructions. Raw Code-attribute inspection confirmed every b9 CP
operand has tag 11, every trailing operand byte is zero, and all 54 count bytes
exactly equal receiver plus category-1 argument slots (seven count 1, 41 count
2, three count 3, and three count 4). All seven `ACC_BRIDGE` methods are public
class methods with Code. No interface method has Code except the four deliberate
metadata `<clinit>` methods, so there are no default or synthetic default bridge
bodies. There are no native/synchronized methods, monitors, handlers, `athrow`,
`invokedynamic`, or non-Object JRE method references. Every manifest bundle has
exactly its source's emitted classfile set (at most 19 user classes).

`javap -c -v -p` over all 30 emitted M4d classes found only Java 8 major version
52 classfiles and zero declared interfaces. Aggregate relevant instruction shapes
include 114 `anewarray`, 116 `aaload`, 86 `aastore`, 17 `arraylength`, 22
`checkcast`, 19 `instanceof`, 15 `invokevirtual`, 99 `invokespecial`, nine
`invokestatic`, and 11 `areturn` instructions. It found no `multianewarray`,
interface/invokedynamic call, monitor, or `athrow` instruction. Full constant-pool
inspection found no JRE method reference except constructor chains ending at
`java/lang/Object.<init>()V`; array helper references retain their exact ordinary,
array, and nested-array descriptors.

`javap -c -v -p` over all 44 emitted M4c classes found only Java 8 major version
52 classfiles and zero declared interfaces or exception tables. It found 38
`invokevirtual`, ten `checkcast`, and ten `instanceof` instructions. Full
constant-pool inspection confirmed the intended symbolic owners, including
`DispatchBase.select`, inherited `FinalChild.fixed`, `ProtectedRoot.score`, both
`A.slot` package-private sites, all three unusual resolved `apply` declarations,
constructor callbacks, and `TypeAnimal.virtualValue`; all other method references
name fixture classes or `java/lang/Object.<init>`. There are no interface calls,
reference/multidimensional/other-primitive array allocations, monitor bytecodes,
throws, invokedynamic instructions, or non-Object JRE method references. The
sole synchronized and native declarations are the deliberately resolved base
methods; every selected value-producing override is ordinary.

`javap -c -v -p` over all 37 emitted M4b classes found only Java 8 major version
52 classfiles and zero interfaces. Aggregate selected-profile instruction shapes
include 100 `new`, 112 `getfield`, 62 `putfield`, 157 `invokespecial`, 12
`invokestatic`, seven `newarray int`, five `iaload`, five `iastore`, nine
`areturn`, and six `aconst_null`. Inspection found zero `invokevirtual`,
`invokeinterface`, `checkcast`, `instanceof`, reference/multidimensional array,
handler/throw, monitor, invokedynamic, or excluded library-API calls (the
required constructor chains end at `Object.<init>()V`). In particular,
`CtorChild.directSuper` names `CtorMiddle.selected:(I)I`, and private helper
calls and recursion use `invokespecial`; public cross-package behavior uses
fields, constructors, and static helpers only.

`javap -c -v -p` over the 18 M4a classes found only Java 8 major version 52
classfiles, zero interfaces, 13 `[I` fields, five `I` fields, seven `<clinit>`
methods, and three `final` array references whose elements are mutated by cases.
Aggregate array/reference instruction shapes include 46 `newarray int`, 31
`arraylength`, 83 `iaload`, 74 `iastore`, 12 `areturn`, seven `aconst_null`,
seven `dup2`, and eight `dup_x2`, plus typed `aload`/`astore`, reference/null
branches, and static/call instructions. Every entered method uses only the frozen
M3d operations plus the exact M4a integer-array/reference operations. The 18
ordinary unentered constructors contain the only `invokespecial` instructions;
there is no entered object allocation, other array kind, multidimensional or
reference array, cast, handler, monitor, native/library call, or category-2
operation.

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

All 960 cases through M4e are the accepted baseline. The 99 M4f-a fixtures have
passed the actual JVM oracle and full classfile/constant-pool profile checks, but
the baseline runner intentionally rejects stage `m4fa` until separately owned
verifier and runtime integration; this fixture revision does **not** claim an
M4f-a EVM pass. Selected native or synchronized concrete interface
implementations are intentionally verifier-only rejection probes: representing
them as successful differential cases would contradict the frozen CallError4
profile. The runtime remains over mainnet deployment size and runs through local
runtime.Execute, not CREATE. This remains subset verification, not full JVM
conformance.
