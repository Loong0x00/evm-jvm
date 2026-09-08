# M4f-b: default methods and mandatory interface initialization

Authority JAVA_EVM_PROGRAM.md; last-green M4f-a ee0314a:1059 oracle cases plus48
independent probes,34 Python,465 smoke/485 fast and focused gates. Runtime92828
bytes SHAea6c940d05f098fe27485d20dadaeaa5f0e1e6c42627da8627632d7f8ce3abe7.
All NEW agents Sol/high WITHOUT Fast/priority. Never --fast or enable preference.
Parent continues bounded implementation/integration/verification automatically.

## Scope / invariant
Enable public interface default Code, default-aware b6/b9 resolution/selection,
InterfaceMethodref b7 for I.super, and the required default-interface initialization
prerequisites of class initialization. Implement EVERYTHING in ordinary EVM bytecode:
raw class parsing/graphs/linking, selection/access, initialization/static slots,
frames/heap/guest instructions/outcomes. Host only packages unchanged classes/int
root args, invokes EVM and decodes. No host parsing/evaluation/heap/AOT/precompile/
classpath fallback, invented JRE services or consensus changes. Trusted Java only
build/oracle. Local runtime.Execute, not deployed/full JVM/Java SE.

Root/API/value descriptors/heap/class caps unchanged. Preserve1059 old fixture
sources/entries/outcomes/budgets. Three verified raw bootstraps unchanged. Interface
statics remain M4f-c except indispensable SELF field accesses in <clinit> below.
No interface external roots, private/native/synchronized interface bodies, other
primitives, monitors, handlers or new Object APIs. Array receiver b6/b9 deferral
and marker closure/covariance remain unchanged.

## Interface shape / defaults
Replace the M4f-a blanket default guard with valid public non-static interface
instance methods: either abstract/no-Code or concrete/exactly-one-Code. Allow
synthetic bridge defaults (0x1041), which count as DECLARED defaults. Retain
InterfaceError4 for private/native/synchronized or abstract/Code-inconsistent
interface instance forms. Default descriptors must be supported; no silently
executed unsupported body. Other graph/header/access/cycle rules unchanged.
Default body instructions are predecoded when entered, as ordinary methods are;
unentered unsupported instructions do not get fabricated implementations.

Abstract-only interface metadata <clinit>/static members remain parseable. Defaults
must NEVER be admitted while skipping their required initialization. A synthetic
bridge default can create this obligation even when source looks abstract.

## Class and interface initialization
When starting ordinary class C initialization, mark C initializing BEFORE its
prerequisites (preserve reentrant M3d behavior). Initialize superclass first. Then
recursively enumerate C's declared interfaces in CLASSFILE order, visiting parents
in their classfile order, parent-first/postorder; deduplicate diamonds by identity.
Initialize each interface that DECLARES a concrete/default instance method,
including synthetic bridges. Merely inheriting a default does NOT qualify. A parent
that declares a default still qualifies even when a descendant reabstracts it or
a concrete class implementation wins dispatch. Then execute C.<clinit>.
Superclass initialization already accounts for its own interface prerequisites.

Initializing a selected interface executes its own <clinit> but does NOT recursively
initialize its parents just because they are interfaces; the enclosing class's
ordered prerequisite list supplies applicable default-declaring parents. Abstract-
only interface <clinit> remains untouched by implements/new/casts/arrays/calls.
Type resolution and default invocation do not independently trigger initialization.
Maintain reentrant state/continuations, existing128 frame cap, and no duplicate
side effects through diamonds or concurrent scheduling within this single VM.

Necessary exception to deferred interface fields: getstatic/putstatic of an
interface's OWN declared field is allowed only while CURRENT frame is that same
interface's <clinit>. Preparation/defaults/ConstantValue and final-own-<clinit>
write rules apply exactly, including cache rechecks. This enables javac's unavoidable
putstatic after ordinary Helper.mark() factories. All external/default-method/
other-interface/ordinary-helper accesses to interface fields remain FieldError3.
Do not infer permission merely from some ancestor active initializer frame.
CP11 invokestatic remains CallError1; forged CP10 interface static remains Call4;
interface root guards remain legacy Method7 / bundle Link5. Static factory methods
on the interface itself are still deferred, even from its <clinit>; use ordinary
helper classes in fixtures. No premature M4f-c expansion.

## Resolution and default selection
Follow JVMS SE8 5.4.3.3/5.4.3.4/6.5. Preserve symbolic declaration versus dynamic
selection. A conflicting default graph is not by itself an allocation/initialization
error: detect conflict when the relevant method resolution/selection is performed.
Class-method resolution searches class/superclass declarations first,
then maximally-specific reachable interface declarations. Interface resolution
searches own declaration, public non-static Object fallback, then maximal parent
interface declarations. No new bootstrap Object APIs.

Maximally specific means a declaration is suppressed by a matching declaration
in a strict subinterface, INCLUDING an abstract redeclaration. Deduplicate paths,
ignore static/private methods, match exact name+descriptor. If interface fallback
resolution has a unique maximal non-abstract default, resolve it; if multiple
maximal defaults, throw ICCE10 at the invocation PC. If only abstract maxima remain,
resolve deterministically and let invocation decide AME. Missing declaration still
CallError3. Conflicts in symbolic resolution precede null; a successfully resolved
b9 I.f with null receiver yields NPE before dynamic default conflict selection.

Dynamic selection uses the COMPLETE receiver interface closure, not only the
symbolically named interface. An applicable class/superclass instance declaration
wins over defaults. A genuine abstract class declaration suppresses defaults and
produces AME11; private/unrelated declarations must not incorrectly count as public
implementations. Preserve M4c override/package-private/protected/final rules and
M4f-a public interface implementation checks. With no applicable class declaration,
choose maximal interface declarations: unique concrete default wins, >1 concrete
maxima ICCE10, none concrete AME11. A maximal abstract redeclaration suppresses a
less-specific default. Exactly one maximal default may win with other unrelated
abstract maxima (confirm on Java8 for binary-evolution probes).

Ordinary selected native/synchronized/inaccessible/static/private/unsupported Code
shapes still CallError4, NOT native execution or new linkage taxonomy. Proper
abstract/no-Code or genuinely missing implementation now AME11; malformed abstract
WITH Code remains validation failure. Resolved abstract/native/synchronized metadata
can still lead to supported concrete override, as before. Count/access/receiver/
opcode-specific checks remain per use; cache selection by dynamic class or leave
uncached. Constructor callbacks after super use allocation dynamic class/default
field values. Array b6/b9 receivers remain CallError4 after symbolic/ref checks.
Nonimplementor receiver validation stays ReferenceError2, not general ICCE expansion.

## Interface invokespecial
Extend b7 ONLY for InterfaceMethodref11 naming a direct superinterface of the
current class/interface. Resolve inherited defaults through that symbolic owner;
require a supported concrete result, exact descriptor/access, initialized current
this and instance caller context. Execute nonvirtually (not dynamic most-specific
selection). Indirect/non-super qualifiers, static caller or non-current receiver
are CallError4. Non-interface CP11 owner InterfaceError1(callPC); malformed CP
CallError1. Null receiver NPE6 after valid symbolic/caller-form checks; int/uninitialized
receiver BytecodeError14. Abstract result AME11; symbolic default conflict ICCE10.
Retain existing CP10 constructor/private/class-super semantics and final checks.
No interface constructor or private-interface-method support.

## Java outcomes / oracle version
Add exact JavaException10 java.lang.IncompatibleClassChangeError and11
java.lang.AbstractMethodError for the default resolution/selection cases above.
Both are Java Errors and MUST remain unwrapped when escaping <clinit>; update
_throwJava's Error classification, not just the host decoder. Prior1..9 unchanged;
non-Errors still wrap EIIE3, OOG is never Java OOM. Go/CLI/Python decode only canonical
known payloads, unknown/noncanonical rejection and schema1 protocol unchanged.

SEMANTICS TARGET Java8. Fresh well-formed source fixtures may continue ordinary
runner JVM comparisons, but binary-evolution ICCE/AME probes MUST run against real
Java8, not assume Java21 parity. Available locally:
/usr/lib/jvm/java-8-openjdk/bin/java, version1.8.0_504. Use explicit env override
JAVA_EVM_JAVA8 if needed, verify reported major8 and fail clearly if required oracle
is unavailable, rather than silently skip or substitute Java21. No downloads/global
config. Trusted javac --release8 may compile old/new source versions separately;
run unchanged compiled classfiles in a bounded Java8 oracle and EVM. These are
Go-owned fixture-build probes, not host production rewriting/evaluation. Parent
review found Java21 differs on one evolved b9 conflict (AME vs Java8 ICCE).

## Coverage / ownership
Append~80-110 fresh trusted Java8 m4fb source cases, preserve1059. Cover basic/
most-specific/diamond/class-wins defaults, b6/b9 same-site polymorphism, class and
interface bridges, I.super (including interface-to-parent), ref/void/int args and
returns, recursion/ctor callbacks; superclass/default-interface/class init order,
non-declaring interface omission, synthetic bridge initialization, diamonds,
reentrancy, NASE/arithmetic/CCE/ASE wrapping. Use ordinary helper counters/factories,
not external interface fields/static calls or JRE APIs. Source-level conflicts/AME
cannot generally compile: put controlled binary-evolution oracles in Go tests,
not falsified source manifest outcomes or new host compile-overlay machinery.

Independent Go: exact graph/shape/access/malformed CP/count/branches, maximal
abstract suppression/conflicts/class abstract wins, I.super directness/receiver,
init order/dedup/reentrancy/self-field/final/cache rules and retained static guards,
Java8 binary-evolution ICCE/AME/initializer unwrapped Error outcomes, exact decoder/
OOG. Keep finite gas/time/heap, no host OOM. Parent approves obsolete default guards/
missing-implementation expectations explicitly; workers report exact old/new cases,
never weaken tests or modify old fixtures/budgets. Parent independently rebuilds
artifact/3bootstraps, Go/CLI/Python1059+fulloracle/smoke/fast/demos/AOT/vet+probes,
accepts last-green and proceeds automatically to M4f-c static interface members.

Runtime ONLY Solidity/runtimehex; jvmevm.go exact new decoder; jvmevm_test.go hash;
integer_test.go decoder tests; new jvmevm/defaults_test.go runtimeM4fb* helpers.
No bootstrap/build/compiler/CLI/fixture/harness/other old-test edits. Report obsolete
profile negatives to parent. Fixtures ONLY differential/** (stage m4fb, preserve1059,
root protocol); baseline runner rejects new stage, bounded manual trusted oracle
checks okay, no fake EVM-green claims. Verifier ONLY tools/java_diff.py,
tools/test_java_diff.py,tools/JAVA_DIFF.md,new jvmevm/defaults_validation_test.go
verifyM4fb* helpers. Existing runtime baseline red expected, no blanket reverts.
Parent owns plans/AGENTS/quickstart/Makefile and explicit obsolete-test updates.
One Solidity writer, no spawning/peer writes/push/global settings/untrusted Java.
All agents Sol/high WITHOUT Fast, report real commits/SHA/size/tests/failures.
