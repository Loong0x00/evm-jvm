# Differential fixtures (schema v1)

These fixtures are inputs to the staged Java-inside-EVM differential runner.
`OracleMain.java` is a host-test-only reflection wrapper; it is not a guest
entry point and is never sent to the EVM interpreter.

The manifest has 2,231 fixed cases: 12 `m1`, 70 `m2`, 119 `m2b`, 67 `m3a`,
73 `m3b`, 85 `m3c`, 72 `m3d`, 115 `m4a`, 100 `m4b`, 79 `m4c`, 100 `m4d`,
68 `m4e`, 99 `m4fa`, 104 `m4fb`, 100 `m4fc`, 120 `m5a`, 110 `m5ba`, 100
`m5bb`, 88 `m5ca`, 130 `m5cb`, 160 `m5cc`, 120 `m5cd`, and 140 `m5da`
cases. Every root entry remains a declared public static `(int...)int` method,
including public interface roots, and guest sources have no `main`. All 2,091
pre-M5d-a entries, including sources, arguments, budgets, tiers, and outcomes,
are unchanged.

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

M4f-b adds 96 value outcomes and eight actual JVM exception outcomes over six
trusted Java 8 sources, which emit 128 classfiles in six bundles (at most 46 in
one bundle). It covers inherited, most-specific, diamond, class-winning, and
superclass-winning public defaults; repeated polymorphic b6 and b9 sites;
class and interface covariant bridges; and legal direct `I.super` calls from
both classes and child interfaces. Default bodies exercise int, void, ordinary
reference, object, int-array, and reference-array arguments/returns, bounded
recursion, and constructor callbacks before derived initialization.

Initialization fixtures observe state only through ordinary helper classes. They
cover superclass/default-interface/class order, classfile-order interface walks,
parent-first diamonds and deduplication, omission of abstract-only and merely
inheriting interfaces, reabstracted descendants, class-wins initialization,
synthetic bridge defaults, repeated allocation, and reentry into a class already
marked initializing. Interface fields are assigned only by their own generated
`<clinit>` through ordinary helper calls; no default/root/helper reads an
interface field, and no interface static method is declared or invoked. Four
initializer failures wrap genuine arithmetic, negative-array, cast, and array-
store failures as `ExceptionInInitializerError`; four matching default-body
paths expose the underlying exception directly.

M4f-c adds 92 value outcomes and eight actual JVM exception outcomes over ten
trusted Java 8 sources, which emit 73 classfiles in seven source bundles (at most
26 in one explicit bundle). It covers legacy and bundled public interface roots;
own and cross-interface static calls and factories; class/interface/default
round trips; reference and array arguments and returns; and null values across
static boundaries. Nonconstant interface fields exercise declaration and
qualifier owners, inherited and hidden names, class qualifiers resolving through
both a superclass and an implemented interface, shared storage, and legal final
reference target mutation.

Initialization cases distinguish interface active use from ordinary class
initialization. They cover parent and default-bearing-parent omission, actual
field declaring owners, repeated use, explicit order, interface/class cycles,
prepared-state reentry, and unchanged class default-interface prerequisites.
Failing parents omitted from child-interface active use stay uninitialized. The
eight outcomes are one direct `ArithmeticException`, two direct
`NullPointerException`, two unwrapped `StackOverflowError` outcomes, and three
`ExceptionInInitializerError` outcomes from failures escaping active interface
initializers.

M5a adds 99 value outcomes and 21 actual JVM exception outcomes over eight new
trusted Java 8 sources, which emit 43 classfiles. Source-valid wrappers retain an
I-only root ABI while internal descriptors use Z/B/C/S across static, private-
special, virtual, interface, default, direct-interface-super, bridge, and
constructor calls. The cases cover signed byte/short and unsigned char
boundaries, source-canonical booleans, conversions, overflow and bounded loops;
static, instance, hidden, inherited, final, interface, and ConstantValue fields;
and atypes 4/5/8/9 with the shared byte/boolean load/store opcodes.

Primitive-array cases cover fields and call transport, full and partial
multidimensional allocation, distinct rows, rank and primitive-leaf identity,
Object/Cloneable/Serializable marker compatibility, nested covariance, and
compatible or rejected stores. The 21 outcomes are four each of
`NegativeArraySizeException`, `NullPointerException`,
`ArrayIndexOutOfBoundsException`, and `ExceptionInInitializerError`, three
`ArrayStoreException`, and two `ClassCastException`. The null cases deliberately
use invalid indices to check null-before-bounds ordering. Constant declarations
have genuine `CONSTANT_Integer` ConstantValue attributes for all four narrow
field descriptors; source reads are javac-inlined and are not misrepresented as
raw `getstatic` or mutated-ConstantValue evidence. Likewise, valid Java source
produces only canonical booleans and explicit source-required argument
conversions; noncanonical raw values remain verifier-owned mutation probes.

M5b-a adds 106 value outcomes, two direct `ArithmeticException` outcomes, one
`ExceptionInInitializerError` wrapping long division by zero during class
initialization, and one `StackOverflowError`. Its scalar-long cases cover tag-5
boundary and patterned constants (loaded with `lconst_*` and `ldc2_w`), modulo
64-bit arithmetic, signed comparisons, `MIN_VALUE / -1`, zero divisors, shift
masking, `i2l`, and `l2i` high/low folds. Odd-index locals, long post/preincrement,
assignment expressions, discarded long returns, and field expressions exercise
javac's category-2 local, `dup2`, `dup2_x1`, and `pop2` forms.

Long values cross static, private-special, virtual, interface, default,
direct-interface-super, interface-static, constructor, recursive, and mixed
`J`/`I`/reference call boundaries. The `(JIL...;)J` interface site has the
required count byte 5, while the `(JI)J` default site has count 4. Fields include
prepared static and instance defaults, writes, increments, finals, class and
interface `ConstantValue` declarations, inherited declaring owners, and hidden
static/instance/interface names. Initialization cases cover superclass/default-
interface/class order, once-only use, prepared-default reentry, class cycles,
interface-parent omission versus inherited-owner active use, and a pending long
operand across initialization. No M5b-a fixture uses a long array or `[J` field,
`newarray` type 11, float/double, boxing, switch, `wide`, handler, monitor, or
non-Object JRE method call.

M5b-b adds 81 value outcomes and 19 actual JVM exception outcomes over six new
trusted Java 8 sources, which emit 27 classfiles. Rank-one long arrays cover
zero/MIN/MAX/patterned 64-bit cells, default zeroes, zero-length identity,
aliases, signed sums/searches/sorts, and post/preincrement, compound, assignment,
and chained-assignment category-2 array stack shapes. Internal `[J` and mixed
`J`/`[J` values cross static, private-special, virtual, interface, default,
direct-interface-super, interface-static, constructor, field, and initializer
boundaries while all selected roots retain the int-only ABI.

Full and partial rank-two/rank-three arrays cover default null leaves, distinct
rows, jagged aliases, covariance through `Object[]` and marker arrays, identity-
preserving casts, compatible/null stores, and rejected unlike primitive leaves.
Static, instance, inherited, hidden, interface-final, constructor-final, and
initialized array fields include mutable final targets, replacement, once-only
initialization, and prepared-null reentry. Mixed object, int, reference, narrow-
primitive, and long-array allocation orders exercise both long-first and long-
last heap use. Fixture allocations remain deliberately modest: shared quota and
logical-OOM boundaries are Go-only checks and are not host-JVM OOM fixtures.

The 19 M5b-b outcomes are five `NullPointerException`, four
`ArrayIndexOutOfBoundsException`, three `NegativeArraySizeException`, two each
of direct `ArithmeticException`, `ArrayStoreException`, and
`ClassCastException`, and one `ExceptionInInitializerError`. Null accesses use
invalid indices, multidimensional allocation includes a negative later count
after a zero outer count, and simple long-array stores prove RHS long division
by zero occurs before null or bounds checking. The initializer wrapper likewise
comes from RHS arithmetic before a null array store check.

Across all stages there are 1,660 value outcomes, 20 ArithmeticException
outcomes, six StackOverflowError outcomes, 32 ExceptionInInitializerError
outcomes, 16 NegativeArraySizeException outcomes, 18
ArrayIndexOutOfBoundsException outcomes, 32 NullPointerException outcomes, 13
ClassCastException outcomes, and 14 ArrayStoreException outcomes. Every budget
is finite: the current manifest maximums are 100,000,000 gas and 30 seconds,
while M5c-b uses at most 90,000,000 gas and 20 seconds. New arrays have at most
eight elements, and all finite fixture loops and successful recursions are
bounded and modest; explicitly expected stack-overflow cases recurse until the
reference JVM throws.

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
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fb.dispatch.DispatchRoot b9ThreeReceivers 4
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fb.supercalls.SuperRoot interfaceParentSuper 4
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fb.initorder.InitRoot syntheticBridgeQualifies 4
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fb.errors.ErrorRoot initArrayStoreWrapped 4
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain M4fcLegacy callsOwn -2
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fc.basic.PublicStatics nested 8
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fc.fields.FieldRoot parentThroughChild 2
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fc.init.InitRoot defaultChildStaticSkipsParent 3
/usr/lib/jvm/java-8-openjdk/bin/java -Xmx64m -cp "$out" OracleMain bundle.m4fc.errors.ErrorRoot initNullWrapped 8
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
find "$out/bundle/m4fb" -name '*.class' -print | sort | while read -r file; do
  class="${file#"$out"/}"; class="${class%.class}"; class="${class//\//.}"
  javap -classpath "$out" -c -v -p "$class"
done
find "$out/bundle/m5ba" -name '*.class' -print | sort | while read -r file; do
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

For M4f-b, one fresh `javac --release 8 -g:none` compilation was followed by 104
separate bounded `OracleMain` processes on explicit OpenJDK 8 1.8.0_504 and the
current Java 21.0.9 runtime. Both runs matched all manifest outcome kinds and
produced identical ordered outputs: 96 values and eight declared exceptions,
with SHA256
`c6fac79c371f0dabb79ef022a0a7f82f0b7f8acf327c9c5d8dc44b9a66aabd38`.
The sorted compact canonical JSON SHA256 of the unchanged old 1,059-entry prefix
is `53d5515887867e33bffe05d09b51440ef7fcb7f6d56f8b8b3c330587c342a13d`,
identical to base revision `72e7f9d`. The baseline runner intentionally rejected
stage `m4fb` at that pre-integration fixture revision; this evidence was
reference-JVM-only and made no EVM-green claim.

For M4f-c, one fresh OpenJDK 8 `javac -source 8 -target 8 -g:none` compilation was
followed by 100 separate bounded `OracleMain` processes on OpenJDK 8 1.8.0_504
and Java 21.0.9. Every process used `-Xmx64m` and a ten-second outer timeout.
Both runs matched all manifest outcome kinds and produced identical ordered
outputs: 92 values and eight declared exceptions, with SHA256
`1118707a929f283455597e10109f960c0fb8a5adb2b1e2c3fbc4fa101bbfe91a`.
The sorted compact canonical JSON SHA256 of the unchanged old 1,163-entry prefix
is `2951fe8ad52f292b535c12008fc3fcb5900b60d4fe2dc80ea196e1ef62b6aae8`,
identical before and after the append. The baseline runner intentionally rejects
stage `m4fc`; these are trusted reference-JVM checks, not an EVM-green claim.

`javap -c -v -p` over all 73 emitted M4f-c classfiles found only Java 8 major
version 52 and 45 interfaces. Constant-pool inspection counted 96 Fieldrefs
(tag 9), 96 Methodrefs (tag 10), and 73 InterfaceMethodrefs (tag 11); entered
instructions included 98 `getstatic`, 43 `putstatic`, 88 interface-owner
`invokestatic`, and 53 ordinary-class-owner `invokestatic` operations. The
field instructions retain declared-parent, child-interface, implementing-class,
ordinary-superclass, and inaccessible-declaring-parent/public-qualifier symbolic
owners. Every bundle's emitted classfile set exactly matches its manifest set.
Inspection found no native/synchronized/private interface method, monitor,
invokedynamic, handler, explicit throw, other-primitive allocation, or non-Object
JRE call.

`javap -c -v -p` over all 128 emitted M4f-b classfiles found only Java 8 major
version 52. It found 23 `invokeinterface`, 44 `invokevirtual`, 230
`invokespecial`, and 99 `invokestatic` instructions. Seven public synthetic
bridges have Code, including three interface defaults; the abstract-source
covariant declarations emit the intended synthetic concrete bridges. Inspection
found no native/synchronized/private interface body, monitor, invokedynamic,
non-Object JRE method reference, or `invokestatic` with an InterfaceMethodref.
All interface-field bytecodes are generated self-`putstatic` operations in that
same interface's `<clinit>` after an ordinary-helper factory call.

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

For M5a, one fresh OpenJDK 8 `javac -source 8 -target 8 -g:none` compilation was
followed by 120 separate bounded `OracleMain` processes on OpenJDK 8 1.8.0_504
and Java 21.0.9. Every process used `-Xmx64m` and a ten-second outer timeout.
Both runs matched all manifest outcome kinds and produced identical ordered
outputs: 99 values and 21 declared exceptions, with SHA256
`5e5faecc1a7fa8f55d64b83c403720b7b32a28d75740c7adf21177251b3cc43e`.
The sorted compact canonical JSON SHA256 of the unchanged old 1,263-entry prefix
is `a580859c132a96222752113b0bce76e9aeeff2666d9d31bb377b87ac40014fb2`,
identical to base revision `297cb56`.

Isolated Java 8 compilation of each of the eight source lists exactly matched
its manifest classfile set. `javap -c -v -p` over all 43 emitted classes found
only major version 52. It found all four newarray operands (boolean, char, byte,
short), `baload`/`bastore` on both boolean and byte arrays, `caload`/`castore`,
`saload`/`sastore`, and full/partial nested primitive arrays. Call sites retain
Z/B/C/S descriptors under ordinary and interface constant-pool owners, including
synthetic covariant bridges and direct `I.super`. ConstantValue attributes use
integer payloads with declared Z/B/C/S fields. No native/synchronized method,
handler, monitor, explicit throw, invokedynamic, category-2 operation, boxing,
String use, or non-Object JRE method reference was found; the only JRE method
reference is the required `java/lang/Object.<init>()V` constructor chain.

The M3b runtime and verifier are integrated. Its accepted suite remains:

```sh
python3 tools/java_diff.py --stage m3b --tier smoke
python3 tools/java_diff.py --stage m3b --tier full
```

For M5b-a, one fresh OpenJDK 8 `javac -source 8 -target 8 -g:none` compilation
was followed by 110 separate bounded `OracleMain` processes on OpenJDK 8
1.8.0_504 and Java 21.0.9. Every process used `-Xmx64m` and a ten-second outer
timeout. Both runs matched all manifest outcome kinds and produced identical
ordered outputs: 106 values and the four declared exception outcomes, with
SHA256 `93a269d209d79b284c1994b4b6454d74683c04745d173ab0e3a3b69ff113d224`.
The sorted compact canonical JSON SHA256 of the unchanged old 1,383-entry prefix
is `3acee2e957ebc44611168fac006c97de730e497217e3c9c2bbd4ba7692b63565`,
identical to base revision `54afeb0`.

Isolated Java 8 compilation of each of the seven new source lists exactly matched
its manifest classfile set. `javap -c -v -p` over all 36 emitted M5b-a classes
found only major version 52 and nine interfaces. It found tag-5 constants with
reserved following indices, `lconst_0`, `lconst_1`, `ldc2_w`, all scoped long
arithmetic/conversion instructions, long fields, all intended call owners, and
long local pairs starting at odd indices. Method Code limits remain small (at
most 9 stack words and 8 local words). Inspection found no `[J`, long-array
opcode, float/double descriptor, boxing, switch, actual `wide` opcode, handler,
monitor, explicit throw, invokedynamic, or non-Object JRE method reference.

For M5b-b, one fresh OpenJDK 8 `javac -source 8 -target 8 -g:none` compilation
was followed by 100 separate bounded `OracleMain` processes on OpenJDK 8
1.8.0_504 and Java 21.0.9. Every process used `-Xmx64m` and a ten-second outer
timeout. Both runs matched all manifest outcome kinds and produced identical
ordered outputs: 81 values and the 19 declared exceptions, with SHA256
`07d7ce93164c6d85a77cd7253b5b711feea28ecc5202f40f8053d51b51dcf9fc`.
The compact canonical JSON SHA256 of the unchanged old 1,493-entry prefix is
`74b81b6ed2136a0335cb86ded26bf1bf8600599dde0f1ca8b175f06077d66e0e`,
identical before and after the append.

Isolated Java 8 compilation of each of the six new source lists exactly matched
its manifest classfile set. `javap -c -v -p` and raw classfile inspection over
all 27 emitted classes found only major version 52, with maximum Code limits of
nine stack words and seven local words. It counted 62 `newarray long`, 97
`laload`, 118 `lastore`, 13 `multianewarray`, 15 `checkcast`, nine `instanceof`,
and six `invokeinterface` instructions. Constant-pool tags 9/10/11 numbered
32/54/7. Raw b9 inspection confirmed a zero trailing byte and exact count bytes:
`([J)[J` uses 2, `([JJ)[J` and `([JJ)J` use 4, and `(J[JI)J` uses 5, proving
`[J` consumes one argument slot while `J` consumes two. Symbolic owners and
field/method descriptors retain the intended ordinary/interface classes and
`[J`/nested-long-array identities. Inspection found no exception handler,
explicit throw, float/double array or descriptor, boxing, switch, actual `wide`,
monitor, native/synchronized method, invokedynamic, or non-Object JRE method
reference.

For M5c-a, six trusted Java 8 source lists emit exactly 14 declared guest
classfiles. The 88 bounded cases cover dense, negative, and sparse integer
switches (including `Integer.MIN_VALUE` and `Integer.MAX_VALUE` keys), defaults,
fall-through, nested switches and loops, calls, default interface methods,
virtual dispatch, statics, initialization, arrays, references, and longs. There
are 86 value outcomes and two genuine `ExceptionInInitializerError` outcomes
from switch-selected initialization failures.

Fresh OpenJDK 8 1.8.0_504 and Java 21.0.9 compilations and 176 separate
`OracleMain` invocations used `-Xmx64m`; each invocation had a ten-second outer
limit. Both JVMs matched all declared outcome kinds and produced identical
ordered outputs. SHA256 over `id`, tab, output, newline records is
`50db2684a6fbf5737ba1ef7fd1793329b10913898571eefa20bdf55cd13c3b7e`.
The sorted compact canonical JSON SHA256 of the unchanged old 1,593-entry prefix
is `27846d154113a13c97234fd8a5350829db00dfa6594caf7cedbe8c1e8776a63f`.

Java 8 `javap -c -v -p` and raw classfile inspection found only major version
52, seven `tableswitch`, 16 `lookupswitch`, and four `goto_w` instructions.
`GotoWideRoot.forward` has Code length 33,018 and a forward displacement of
+33,010; `backward` has Code length 33,021 and a backward displacement of
-33,012. `WideRoot` has Code/max-locals pairs 5,433/263 and 4,663/267, with
actual wide int, long, and reference loads/stores and signed `iinc_w` constants
-32,768, -30,000, 30,000, and 32,767. The largest M5c-a constant pool has 74
entries, far below 4,096, and the largest Code attribute remains below 65,535.
There are no handlers, float/double operations, `jsr`/`ret`, monitors,
invokedynamic instructions, or non-constructor JRE method calls. Source uses of
`Integer.MIN_VALUE`, `Integer.MAX_VALUE`, and `Long.MIN_VALUE` compile to
constant bytecodes, not JRE field accesses.

All 1,593 cases through M5b-b are the accepted baseline. The baseline runner
intentionally rejects manifest stage `m5ca` until the separately owned verifier
lands; this fixture evidence is reference-JVM-only and does **not** claim an
M5c-a EVM pass. Raw nonzero switch padding, malformed variable structures,
zero-pair lookup payloads, typed stack-prefix probes, invalid switch targets,
and wide local boundary/type errors remain verifier/runtime-owned checks. The
runtime remains over mainnet deployment size and runs through local
runtime.Execute, not CREATE. This remains subset verification, not full JVM
conformance.

## M5c-b scalar IEEE fixtures

M5c-b appends 130 trusted value cases from five Java 8 sources (12 emitted guest
classfiles). Integer roots carry binary32 bits directly and binary64 bits as
explicit high/low words; outputs are likewise exact 32-bit words rather than
hashes. The cases cover CP4/CP6 constants, `fconst_*`/`dconst_*`, scalar locals
(including wide F/D indices), static/instance/hidden/final/ConstantValue fields,
required default-interface initialization, constructors, recursion, reference
separation, and static/private-special/virtual/interface/default/direct-interface-
super/interface-static calls. They also cover all ten scoped conversions,
`fcmpl`/`fcmpg`/`dcmpl`/`dcmpg`, and exact-sign-bit `fneg`/`dneg`, with signed
zeros, infinities, normal/subnormal boundaries, quiet NaNs, and RNE cases around
2^24, 2^53, 2^63, gradual underflow, and float overflow.

The only JRE calls in emitted guest constant pools are the four approved raw-bit
APIs: `Float.intBitsToFloat`, `Float.floatToRawIntBits`,
`Double.longBitsToDouble`, and `Double.doubleToRawLongBits` (plus ordinary
`Object.<init>` constructor chains). No fixture emits F/D add, subtract,
multiply, divide, remainder, array operation, boxing, handler, monitor,
`invokedynamic`, or other JRE method call. Explicit `class_files` bundles omit
`java/lang/Float` and `java/lang/Double`; those minimal native holders are a
separately owned runtime responsibility.

OpenJDK 8 1.8.0_504 and Java 21.0.9 each used a fresh Java-8-target compilation
and 130 separate `OracleMain` processes with `-Xmx64m` and the manifest's finite
outer timeout. Both JVMs produced identical ordered outputs; SHA256 over
`id`, tab, output, newline records is
`c9aaed43a3834cdb7da457bc786147cec2fa676d76df9739db20c328bc5e46a3`.
All 130 outcomes are values. The sorted compact canonical JSON SHA256 of the
unchanged 1,681-entry prefix is
`dec76d35636b40f747f35c1d89c90eb3fc95d6c3e993745f3b38df994aee6d86`,
identical to base revision `83fd908`. The corresponding M5c-b case-list SHA256
is `675f28faa6c270909a6012f40051ddf8c400a38325ecb4570cedf3e41d50843d`.

Java raw-bit APIs may quiet signaling NaNs on some JVM/hardware paths, so these
cross-JVM exact transport cases use only quiet NaNs and make no signaling-NaN
payload claim. The two conversion wrappers normalize only a NaN result to
`0x7fc00000` or `0x7ff8000000000000`; finite values and signed zeros always use
unaltered raw bits. Exact signaling-payload transport and the runtime's stated
canonical conversion policy remain EVM-only verifier responsibilities. The
baseline differential runner at this fixture-only revision intentionally rejects
stage `m5cb`; the checks above are bounded trusted reference-JVM evidence, not a
claim that the unintegrated EVM runtime is green or that general Java is
supported.

## M5c-c scalar IEEE arithmetic fixtures

M5c-c appends 160 trusted value cases from three Java 8 sources (11 emitted
classfiles), leaving every parsed object in the accepted 1,811-case prefix
exactly equal to base revision `70a2eba`. There are 61 one-operation binary32
cases, 40 binary64 vectors
with separate high- and low-word entry cases (80 entries), 16 mixed feature
entries, and three fixed 16-remainder performance entries. Every root accepts
only signed `int` words: binary32 operands are raw 32-bit words and binary64
operands are explicit high/low pairs. Thus every operand crosses the root call
and each tested operation remains in emitted Code rather than being folded by
`javac`; binary64 results are never reduced to a hash.

The scalar tables exercise all ten scoped opcodes (`fadd`/`dadd`, `fsub`/`dsub`,
`fmul`/`dmul`, `fdiv`/`ddiv`, and Java `frem`/`drem`). Coverage includes quiet
NaNs in both operand positions across the suite, invalid infinity/zero forms,
both infinity signs, all signed-zero result rules, exact cancellation, absorption,
normal/subnormal transitions, gradual underflow, finite overflow, and RNE
halfway cases with even and odd lower significands. Remainder cases distinguish
Java `7 % 4 == 3` from nearest-quotient IEEE remainder, retain the dividend sign
for negative and exact-zero results, ignore the divisor sign, and include
max-finite/three exponent gaps and min-normal/max-subnormal. The repeated gates
execute the same max-finite/three operands 16 times in a bounded bytecode loop.
Single scalar entries have a 20,000,000 gas bound; mixed call/object entries use
30,000,000; repeated-remainder entries use the frozen 100,000,000 bound. No old
gas, timeout, smoke, source, entry, or outcome metadata changed.

The feature source covers ordinary and `strictfp` arithmetic, static and virtual
calls, interface defaults and direct-interface-super invocation, constructor
field initialization, float and double field post-increment, a static compound
update, and class initialization. `M5ccInit.<clinit>` contains actual `fdiv` and
`ddiv` instructions for `1.0f / +0.0f` and `0.0d / 0.0d`; reading both initialized
fields verifies infinity and NaN values rather than `ArithmeticException`.

Each arithmetic result wrapper tests NaN with bytecode comparison and maps only
a generated NaN result to the stage policy (`0x7fc00000` or
`0x7ff8000000000000`). Finite values, infinities, and signed zeros go unchanged
through the raw-bit APIs and must compare exactly. Inputs use quiet NaNs only.
These cases make no signaling-NaN payload/quieting or raw-transport portability
claim; exact raw transport remains the separate M5c-b concern. Emitted constant
pools reference only the four approved raw-bit APIs
`Float.intBitsToFloat`, `Float.floatToRawIntBits`,
`Double.longBitsToDouble`, and `Double.doubleToRawLongBits`, plus fixture methods
and ordinary `Object.<init>`. There are no FP arrays, array allocation, handlers,
boxing, `Math`, FMA, monitor, `invokedynamic`, or other JRE calls.

Fresh OpenJDK 8 1.8.0_504 (`javac -source 8 -target 8`) and Java 21.0.9
(`javac --release 8`) compilations were each followed by 160 separate
`OracleMain` processes using `-Xmx64m` and the manifest's 10-, 15-, or 30-second
outer timeout. All 320 bounded invocations completed as values and both JVMs
produced identical ordered output. SHA256 over `id`, tab, full `value=...`
output, newline records is
`bddf7a9936ca57b0fb221de8227a7bf2117767b749e92d7f45256085c6a4a076`.

Java 8 `javap -c -v -p` inspection found major version 52 for all 11 classes and
actual arithmetic instruction counts of four `fadd`, two `fsub`, two `fmul`,
three `fdiv`, three `frem`, three `dadd`, one `dsub`, two `dmul`, two `ddiv`, and
three `drem`. The two repeated methods contain a loop bound of 16 and execute
`frem`/`drem` on unchanged local operands. The largest constant pool has 147
entries. No exception table or deferred/forbidden instruction listed above was
emitted, and each source's compiled class set exactly matches every manifest
`class_files` bundle.

The sorted compact canonical JSON SHA256 of the unchanged 1,811-entry prefix is
`dff49e76cf167ac985c8ac3eca6470ff767860d6546a3057d77c3dc78db9c920`.
The corresponding 160-case M5c-c suffix SHA256 is
`10cbb30d84b86e4b0c2a50d7c2a061bce62bd42c4bf2c306cfef1c90b294ba2e`,
and its ordered ID SHA256 is
`0db3ba6528885f6600664c2be7b980d10b870ed258ea4f3689768f06c0658652`.
The baseline differential runner intentionally rejects
manifest stage `m5cc` until the separately owned verifier lands. Therefore this
fixture revision records bounded trusted reference-JVM evidence only; it does
not claim an EVM pass, measured EVM gas, FP arrays, general Java support, or
mainnet deployment compatibility.

## M5c-d IEEE array fixtures

M5c-d appends 120 trusted cases from six Java 8 sources (30 emitted guest
classfiles), leaving every parsed object in the accepted 1,971-case prefix
exactly equal to base revision `60b9ae6`. All 120 entry descriptors remain
`(I...)I`: binary32 values use one signed raw-bit word and binary64 values use
explicit high/low words, including separate exact high- and low-result entries.
The suffix has 98 value outcomes and 22 existing schema-1 Java outcomes: six
NPE, four bounds, four NASE, two ASE, two CCE, two arithmetic, and two wrapped
initializer failures. No exception kind, old source, entry, outcome, budget, or
other old metadata changed.

The fixtures exercise `newarray` float/double, `faload`/`fastore`,
`daload`/`dastore`, default positive-zero cells, exact full-width copies and
aliases, signed zeros, normal/subnormal boundaries, infinities, and multiple
signed quiet-NaN payloads. Raw array load/store/copy/call/field/cast transport
always returns `floatToRawIntBits` or `doubleToRawLongBits` directly and never
normalizes a NaN. Only methods that actually perform FP arithmetic normalize a
generated NaN to the established M5c-c canonical value; finite values,
infinities, and signed zeros remain exact. Signaling-NaN portability is not
claimed by these cross-JVM fixtures and remains an EVM-only verifier probe.

Coverage also includes javac's array post-increment and compound category forms;
static/private-special/virtual/interface/default/direct-interface-super and
interface-static calls; mixed reference/double argument slots; constructors;
static, instance, hidden, inherited, final, and interface array fields; final
reference element mutation; ordinary and reentrant initialization; partial,
jagged and full multidimensional allocation; covariance and marker closure;
compatible/null/ASE stores and CCE casts; F-vs-I and D-vs-J primitive
invariance; null/bounds/NASE precedence; left-to-right dimension/store
expressions; integer failure before a null store; FP zero division before a null
store; and EIIE wrapping. First-allocation permutations cover float, double,
long, reference, and object storage, and a mixed gate allocates and checks all
eight Java primitive array kinds without requesting host-OOM-sized arrays.

Fresh OpenJDK 8 1.8.0_504 (`javac -source 8 -target 8 -g:none`) and Java
21.0.9 (`javac --release 8 -g:none`) compilations were each followed by 120
separate `OracleMain` processes with `-Xmx64m` and each manifest's finite outer
timeout. Both JVMs produced identical ordered outputs. SHA256 over `id`, tab,
full output, newline records is
`be2ab84f43b6a3cd3966cd92f921262d96116c92d0bc3e88af5a8eb0733cf8e0`.
The sorted compact canonical JSON SHA256 of the unchanged 1,971-entry prefix is
`bc8f5c0504eac5d2fe54d6cf772f302a08085e7ca4e66ef85b6d860df1965010`;
the 120-case suffix SHA256 is
`c05b99cdef27be5422e72f103909431c55b0c01843e63fcc0edb362c898402fc`,
and its ordered ID SHA256 is
`9399140feda0c8931ce350fb75ec9b7075bd53b7be6e5dff969fd74de5217117`.

Java 8 `javap -c -v -p -s` inspection found major version 52 in all 30
classfiles, exact source-to-manifest class sets, and a largest constant pool of
166 entries. Emitted Code contains 44 float and 40 double `newarray` sites, 47
`faload`, 48 `fastore`, 43 `daload`, 40 `dastore`, ten `multianewarray`, and
both `[F` and `[D` descriptors throughout fields and calls. The two
`invokeinterface` sites encode count 3 for receiver/[F/F and count 4 for
receiver/[D/D, demonstrating that array references count one word while scalar
D counts two. Constant-pool Java method references are limited to the four
approved raw-bit APIs and ordinary `Object.<init>`; no handler table, monitor,
`invokedynamic`, `jsr`, `ret`, boxing, `Math`, or FMA was emitted.

At this fixture-only revision the baseline runner intentionally rejects stage
`m5cd`; the checks above are bounded trusted reference-JVM evidence. They do not
claim an EVM pass, signaling-NaN cross-JVM behavior, logical-quota/OOM coverage,
mainnet deployment compatibility, or general Java support.

## M5d-a implicit-exception and handler fixtures

M5d-a appends 140 trusted Java 8 cases from 11 sources (64 emitted guest
classfiles), leaving every parsed object in the accepted 2,091-case prefix
exactly equal to base revision `1353b03`. There are 127 value outcomes and 13
uncaught Java outcomes: one ArithmeticException, two NullPointerException, one
each ArrayIndexOutOfBoundsException, NegativeArraySizeException,
ClassCastException, and ArrayStoreException, four
ExceptionInInitializerError, and two NoClassDefFoundError. Ninety-five new
cases are smoke-marked. Ordinary cases use a finite 60,000,000 gas/15 second
bound and initialization cases use 80,000,000 gas/20 seconds; these are fixture
bounds, not measured baseline EVM gas.

The source fixtures cover all non-resource implicit kinds reachable from
ordinary Java source in this slice, with exact catches and matches through
IndexOutOfBoundsException, RuntimeException, Exception, Throwable, LinkageError,
and Error. They exercise classfile-ordered exact/fallback and multi-catch tables,
nesting, overlapping compiler cleanup ranges, javac 8 catch-all finally tables,
rethrow, null `athrow`, fresh identity, handler faults, side effects before a
fault, end-exclusive ranges, and complete operand-prefix clearing. A handler
retains live I/F/D/J locals (the Java 8 class has a full stack-map frame with
`int, int, long, float, double`) and uses them after unwind.

Captured VM exceptions travel without construction through locals, static and
instance fields, Throwable/Object arrays, arguments, returns, checked casts, and
repeated cross-frame rethrows. Static, virtual, interface, interface-default,
direct-interface-super, private-special, constructor, and interface-static call
sites all have bounded unwind cases. Constructor fixtures distinguish body,
argument, `this(...)`, super-argument, and superclass-body failures caught by
the caller; separate constructors catch only after a normal `super(...)` return
and continue. User subclasses of Throwable, Error, RuntimeException, and
ArithmeticException occur only as ordered catch types. Their compiler-emitted
constructors are never entered and no Throwable object is created by guest
source.

Initialization fixtures cover a fault caught inside `<clinit>`, continuation
after that catch, fresh EIIE followed by fresh NCDFE in the same invocation,
NCDFE matching through its exact type and canonical supertypes, active-use
get/put/call/new forms, an EIIE identity propagated unchanged through a
dependent initializer, reentrant prepared/default reads, superclass and
default-declaring-interface prerequisites, a supplied but unused failing class,
and four failures before root method entry. One root-initialization case lets an
actual NCDFE escape after a dependency has become erroneous. `OracleMain` was
therefore extended only inside its `Class.forName` initialization block, with
explicit AME, ICCE, and NCDFE catches. Missing classes, bad arguments, missing or
inaccessible entry methods, reflection failures, and unrelated Errors retain
the prior harness-failure paths.

Fresh OpenJDK 8 1.8.0_504 (`javac -source 8 -target 8 -g:none`) and Java 21.0.9
(`javac --release 8 -g:none`) compilations were each followed by 140 separate
`OracleMain` processes. All 280 bounded invocations matched their manifest kind,
and the two JVMs produced identical ordered `id<TAB>outcome` records with
SHA256 `7350165011f8a5b477597a1db69e5b82d8b51b5d0c3fb1f6700d5bc721b692f3`.
Evidence is under ignored `build/java-diff-m5da-fixture-oracle/`. The sorted
source-hash manifest (11 files) has SHA256
`4d46534b317ba91802a0ac576567d0b1221877d96cf856e3681c38de72be976f`;
the Java 8 and Java 21 class-hash manifests (64 files each) have SHA256
`3f9c57304d7f233a3497ec669b67279e82789da28dc8d22afba1db345c5b509f` and
`82dc4ac4a6a1809051bf7bf42837ff44048444f1d00ac8068d666c470f28d979`.
All 64 Java 8 classes are major version 52, every manifest class path exists,
and the largest per-case bundle is 20 classes. Full `javap -c -v -p` evidence
contains all four invoke opcodes, 19 `athrow` instructions and five catch-all
rows, with no jsr, ret, monitor, or invokedynamic opcode. Apart from ordinary
Object constructors and the never-entered user-Throwable constructor metadata,
there is no JRE method call in guest classes.

The compact sorted canonical JSON SHA256 of the unchanged 2,091-entry prefix is
`df6a8e3adce6f8085e9730c262e9894fefd0602253d19b699e0dc22e80fa2025`.
The corresponding 140-case suffix SHA256 is
`69bd596fe106295968132f57409cb11eac495b2770acea3d8127917fd5cc8b0e`,
and its ordered ID SHA256 is
`14ee38aac1100e17613959079c2b0a76d1cf2275c353b40ce832c4df9acf2d31`.

ICCE and AME require binary evolution and cannot honestly be produced by one
fresh joint schema-1 source compilation. The frozen, separately compiled Java 8
preflight is retained at
`m5da-oracles/build/java-diff-m5da-oracle-preflight`: its trusted source and
evidence archives have SHA256
`b1ebda62c51c10794153d0785e8432ce8f5d4b70fe065ac053539a841b4e149d` and
`7ecf6e00d5b70b4c481dfeed402286b1fef27e284b47d4ee681fdd358a8a634a`.
The preserved-old-class AME oracle agrees on Java 8/21 (`direct=121`, then AME,
then NCDFE). The preserved-old-class ICCE oracle is Java-8-authoritative
(`direct=111`, then ICCE, then NCDFE); Java 21 instead reports AME for the
initializer trigger, the expected secondary-version difference. Those
class-replacement probes remain focused runtime/verifier tests rather than fake
fresh-source differential cases; no harness schema or production host path is
changed here.

There is deliberately no new host OOM or SOE exhaustion case. Arena, ordinary
heap quota, frame cap, malformed handler tables, lazy missing catch types, and
binary-evolution replacement are runtime/verifier-owned probes. At this
fixture-only revision the baseline runner rejects stage `m5da` before EVM
execution because its stage/kind allowlists have not yet landed, and the
baseline runtime lacks handlers. The reference evidence above does not claim an
EVM pass, alter expected outcomes to appear green, or claim general Java or
mainnet deployment support.
