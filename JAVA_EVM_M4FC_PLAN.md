# M4f-c: interface static methods, fields and declaring-owner initialization

Authority JAVA_EVM_PROGRAM.md. Last-green M4f-b4824b93:1163 oracle cases plus48
parent probes,36 Python,517 smoke/537 fast and full focused gates. Runtime100472
bytes SHA32a0d8e90202b8538653b236e9142efc53760293dd837faf122ce8998dd6d847.
ALL NEW workers Sol/high WITHOUT Fast/priority; never --fast or enable preference.
Continue bounded integration/independent verification automatically, no routine
confirmation. Java8 oracle available at /usr/lib/jvm/java-8-openjdk/bin/java.

## Scope / invariant
Enable interface invokestatic via InterfaceMethodref11; getstatic/putstatic with
full class/interface field resolution; ordinary or interface static(I...)I roots.
All raw-class parsing/linking/resolution/initialization/static slots/guest execution
remain in ordinary EVM bytecode. Host only packages unchanged class bytes/int args,
invokes EVM and decodes. No host parser/evaluator/heap/AOT/precompile/classpath/JRE
fallback, specialized runtime or consensus changes. Trusted javac/JVM only build/
oracle. Local runtime.Execute only, artifact exceeds EIP-170, no full JVM claim.

No new bytecodes, JavaException kinds, descriptor types, bootstraps or resource
limits. Preserve existing1..11 outcomes, root argument/result encoding, all1163
fixture entries/sources/outcomes/budgets. Root may now name an interface containing
an eligible unambiguous static method; legacy Run and RunClasses both support it.
Root native/synchronized/abstract/non-static/signature/access rejection remains
exact; only blanket interface-root guards become obsolete. External references
still cannot be root args/returns. Interfaces are NOT instantiable by new.
No private interface methods, native/synchronized execution, other primitives,
handlers, monitors, array receiver dispatch or new Object/JRE services.

## invokestatic interface resolution
b8 CP10 is for an ordinary CLASS symbolic owner, retaining inherited class static
method lookup. It must NOT inherit interface static methods. CP10 with interface
symbolic owner remains CallError4. b8 CP11 requires interface symbolic owner,
otherwise InterfaceError1(callPC). Malformed CP/index/name/type tag remains Call1.

Interface static method lookup is EXACT in the named interface: statics are NOT
inherited through parent interfaces or implementing classes. If absent in that
owner, CallError3 (not a new Java NoSuchMethodError taxonomy). Reject constructors/
<clinit> names, non-static or unsupported/private/native/synchronized/abstract/body/
descriptor shapes with Call4. Preserve public/class accessibility and supported
I/reference/V descriptor rules. Local0 is first explicit argument, NOT a receiver.
Calls carry no receiver/null semantics; unrelated null/reference stack prefixes
must not be consumed or cause NPE. Actual instance calls made inside static bodies
retain normal null ordering. Frame/count/return checks and128 frame cap unchanged.

After symbolic resolution/access/selected-method checks, initialize the actual
DECLARING interface and invoke its ordinary Code. Initializing that interface
runs its own <clinit> only, not parent interfaces merely because they are parents,
even if parents declare defaults. Preserve class initialization's distinct M4fb
superclass/default-declaring-interface prerequisites. Reentrant same-thread calls
to an initializing interface see prepared/current state and must not restart it.
Type operations/arrays/b9/default calls still do not independently initialize types.

## Full field resolution and storage
For Fieldref9, validate symbolic class/interface access and exact field name AND
descriptor. Search JVMS8 5.4.3.2 order:
1 declaration in symbolic type;
2 recursively its direct superinterfaces (each declaration before its parents,
  stable classfile order, deduplicate diamonds for traversal);
3 superclass, repeating the same lookup order there (interfaces have no ordinary
  superclass field-search path through Object).
Do NOT search the superclass before direct interfaces or skip an instance/private
same-name exact-descriptor declaration to find a more convenient static field.
Wrong static-vs-instance opcode after successful resolution remains FieldError3;
access/final failures FieldError4, missing declaration FieldError2, malformed Fieldref
FieldError1; preserve supported-descriptor/ConstantValue errors. Ambiguous/evolved
field layouts use bounded Java8 probes rather than guesses; runtime deterministic
classfile interface order is intended. No host lookup/fallback.

Cache actual declaring class/interface plus field index/type, not merely the
symbolic qualifier. Static storage shared across qualifiers. getstatic/putstatic
initialize ONLY actual declaring owner, not the qualifying subinterface/class or
unrelated parents/default-bearing interfaces. Fields accessed through a public
qualifier may be declared on an inaccessible ancestor type: apply symbolic-type
access plus resolved-member access, do not add a bogus public-declaring-type rule.

Drop M4fb's self-<clinit>-only interface field deferral: normal public reads are
now supported from ordinary/default/interface methods and helpers. Final static
writes still ONLY current <clinit> of the ACTUAL DECLARING owner, including after
cache population. A child interface initializer cannot write parent final fields.
Preparation/ConstantValue/default zero/null and typed/assignable reference storage
remain exact. Interface fields in valid Java8 are public static final; do not
silently accept malformed flags via relaxed access checks. Preserve existing
InterfaceError1 header/field-shape guards (e.g. removing required public/static/final
bits is a graph-shape fault, not a valid private-member FieldError4 probe). Existing constant-
variable source folding is not permission to simulate values outside EVM.

Source-level inherited field use must initialize declaration, not qualifier:
ChildFace extends ParentFace with ParentFace.X, ChildFace.X resolves ParentFace.X
and initializes ParentFace only. Class C implements Face referencing Face.X through
C must not initialize C just because C qualifies the Fieldref. Contrast interface
static methods, which are NEVER inherited. Nonconstant fields used in fixtures
must emit actual getstatic, not javac folding/JRE requireNonNull surprises.

Instance-field operations may now encounter interface fields through resolution;
resolve first and reject static mismatch rather than reinterpreting static storage
as object slots. M4b instance layouts exclude static fields; interface fields must
not add object slots. Final-reference array/object element mutation is still valid,
while rebinding final interface fields outside own <clinit> rejects.

## Initialization and outcome details
Allow interface <clinit> to call own/other interface static factories and access
own/other public fields. Initialize actively used DECLARATION, never all ancestors.
Cross interface->class->interface recursion must respect initializing states and
frame limits, preserve operand stack until scheduled initialization finishes, and
not duplicate field stores or invocations after replaying the instruction.

Non-Errors1/4/5/6/8/9 escaping an active initializer wrap EIIE3. Error2/7/10/11 remains
unwrapped; EVM OOG never Java OOM. All canonical decoders/schema1/value-or-exception
outputs unchanged. No catch/retry/erroneous-class reuse semantics newly claimed.
Symbolic resolution/access/staticness errors must not trigger unrelated initializer
side effects or get mislabeled as Java outcomes; malformed multi-fault tests should
be isolated rather than implying a complete JVM verifier/linkage-error taxonomy.

## Tests and gates
Append~70-100 fresh trusted Java8 m4fc cases, preserve1163. Root interface and ordinary
class APIs; same/cross interface static calls and calls into/from classes, defaults
calling interface statics, self factories, inherited field qualifiers/shared storage,
class-interface-superclass resolution, reference/array fields/final element mutation,
interface-parent no-init, default-parent no-init on interface active use, class init
still initializes default prerequisites, reentrant cycles/order/failures, null-related
static arguments/returns and instance calls within static bodies. Use finite JVM
-Xmx64m/timeouts, no host memory exhaustion. Inspect CP tags9/10/11, qualifiers,
emitted class sets and Code owners. Java8 and current JVM fresh-source parity
recommended; binary-evolution precedence/static-noninheritance probes use Java8.

Independent Go exact malformed refs/wrong owner kind/staticness/access/return/stack
prefix, missing interface static even parent declares it, selected body flags,
field-resolution order via trusted old/new separately compiled definitions, final
writes after cache and cross-owner initializers, interface roots/invalid roots,
no qualifier/parent initialization and no descriptor/body side effects before
resolution, reentrancy/replay/frame cap, canonical exceptions/OOG/unwrapped Errors.
Compile trusted unchanged Java8 classfiles for binary evolution; no production
rewriting. Do not weaken assertions or fabricate unknown revert successes.

Old guards rejecting interface roots/static calls/external fields now obsolete;
workers REPORT exact cases/new supported semantics to parent, no unauthorized
old-test edits/skips. CP10 interface statics and wrong-staticness/final/private/
native/sync guards remain. Parent explicitly updates only obsolete expectations.
All historical fixture inputs/outcomes/budgets unchanged.

Parent integrates runtime->fixtures->verifier, reviews old-profile changes,
independently checks pinned artifact/3bootstraps, focused Go/CLI/Python1163+oracle,
smoke/fast/demos/AOT/vet and new probes. Accept last-green then freeze next bounded
remaining-value/exception stage based on dependencies. No routine confirmation.

## Ownership
Runtime ONLY Solidity/runtimehex; jvmevm/jvmevm_test.go expected HASH ONLY;
new jvmevm/interface_statics_test.go runtimeM4fc* helpers. No host/API/decoder/CLI/
bootstrap/build/compiler/harness/fixtures/other old-test edits. Report obsolete
profile assertions, parent owns updates. Fixtures ONLY differential/** stage m4fc,
preserve1163/schema1; baseline runner rejects stage until integration, bounded manual
trusted JVM checks fine, no fake EVM-green. Verifier ONLY tools/java_diff.py,
tools/test_java_diff.py,tools/JAVA_DIFF.md,new interface_statics_validation_test.go
verifyM4fc* helpers; baseline red expected, exact evidence required.
Parent owns AGENTS/plans/quickstart/Makefile and integration/independent review.
One Solidity writer; no spawning/peer writes/push/global config/untrusted Java.
All agents Sol/high WITHOUT Fast; commit scoped paths and report real SHA/size/
checks/limits/failures honestly. No full-JVM/deployment claim.

## Accepted integration evidence
Runtime0633278→80fe607, fixturesa0918f7→336a4dd, verifier actual
4b9d68b7b202ce439ef9a7b20ac75b77f5b81e9b→07f0496 (report SHA corrected locally).
Review8fd0c29→965f51c updated only obsolete interface static/root/field guards;
malformed CP tag9 Call1 retained plus CP11/class-owner Interface1 assertions;
missing-method probe uses a valid absent name. JVM8/source expectations verified,
no runtime changes or demonstrated frozen-contract defect.
Parent final artifact/3bootstraps, Go/CLI,36 Python,1263 full,567 smoke,587 fast,
demos,AOT,focused vet and48 independent probes passed:
`build/java-diff-parent-m4fc/probe-0x87xny3/results-final/`.
Prior1163 inputs/outcomes/budgets unchanged. Accepted runtime100297 bytes SHA256
`efc31ddc4e43d80b459cd1f851c505f47470e24d15b85915539db6818959ba5f`.
Next narrow int-like primitive types before category2/IEEE work. ALL agents NO Fast.
