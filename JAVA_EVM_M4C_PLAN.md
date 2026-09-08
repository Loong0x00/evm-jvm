# M4c: virtual dispatch, checkcast and instanceof

Authority JAVA_EVM_PROGRAM.md; last-green M4b9b650dc:713 fixed oracle cases,
46 independent probes,31 Python tests,289 smoke/309 fast and full focused gates.
Runtime57900 bytes SHA df00b2bf5208c28b4923bd305e3f3605780f1ad3d924e52fcf45acacede98eca.
Sol/high with inherited enabled Fast preference; priority acceptance not guaranteed.
Parent continuously integrates/verifies/advances, no routine confirmation.

## Scope/boundary
Add invokevirtual0xb6, checkcast0xc0, instanceof0xc1. All resolution, dynamic
selection, access/type checks and guest execution are in ordinary EVM bytecode.
Host only packages unchanged class bytes/int arguments, calls EVM and decodes.
No host evaluator/parser/heap/classpath fallback, AOT, precompile, JRE shortcut,
class-specific runtime or consensus edit. Trusted Java/JVM only for build/oracle.

Types remain I, int[], ordinary classes and Object; root static(I...)I unchanged.
Preserve M4b descriptors/frames/heap/caps/constructor lifecycle/initialization and
all prior bytecodes. No interfaces/invokeinterface, reference/multidimensional
array allocation/storage, other primitives, handlers, monitors, strings/class
literals or broader Object/JRE APIs. Bootstrap95-byte Object constructor-only,
source/hex/embedded-class/parser/interpreter path unchanged. No native service.
Local runtime.Execute only, artifact already exceeds EIP-170 deployment limit.

## invokevirtual
Use Methodref10 with structural CP validation and exact name+descriptor lookup
against symbolic class and ancestors. Reject constructor/<clinit>/static/private
resolved targets explicitly with CallError4, malformed reference CallError1,
missing method CallError3; class resolution/access retain current conventions.
Resolve/access-check the declaration before checking null. Do not reject resolved
abstract/native/synchronized/no-Code merely for those properties: an ordinary
concrete override may be selected. Descriptor must remain supported. No target
class initialization caused by invokevirtual.

For non-null initialized ordinary receiver, verify assignability to symbolic
owner and cross-package protected receiver restriction against RESOLVED declaring
class: receiver dynamic class must be caller or subclass. Dynamic selection follows
JVMS SE8 5.4.5 overrides relation, not first name/descriptor match:
- private declarations do not override;
- public/protected inherited methods override normally;
- package-private requires same-package or transitive override chain;
- p.A(package f) -> p.B(public f) -> q.C(f) selects C;
- p.A(package f) -> q.B(same signature) -> q.C(f) does NOT override A.f;
- hidden/unrelated same-signature declarations must not hijack the method slot.
A resolved final method selects itself; a descendant instance declaration actually
overriding it is invalid and must reject CallError4, not dispatch. Do not reject
legitimate same-signature declarations that do NOT override a package-private
final across a package gap. Class-final superclass checks stay as before.

Selected method must be ordinary non-static/non-private/non-native/non-abstract/
non-synchronized, exactly one supported Code body. Otherwise CallError4, NOT an
invented AbstractMethodError/native implementation. Return opcode and descriptor
checks, typed/assignable arguments/returns and independent frames use M4b rules;
receiver local0 followed by explicit args. Keep128 frame cap and exact outcomes.
Resolved-site cache and selected dynamic target must be distinct: cache selection
by site AND dynamic receiver class, or don't cache it. Recheck opcode/protected/
private/final/access conditions per use. Shared CP sites across special/static/
virtual paths cannot bypass respective checks. Preserve synchronized-special fix.

Null yields Java NPE6 after successful symbolic resolution/descriptor/opcode/access
checks, before dynamic selection/body loading. Thus null with abstract/native
resolved target can be NPE without executing the unsupported body. Uninitialized
receiver/arguments remain BytecodeError14. Invalid handle/wrong heap kind is
ReferenceError1; incompatible ordinary receiver ReferenceError2. Stack errors and
CallError5 return-opcode mismatch retain exact existing behavior.

Frozen ARRAY RECEIVER DECISION: virtual calls with an actual int[] receiver are
explicitly deferred, CallError4 after successful symbolic resolution and reference
validation. No pretending arrays are field-bearing objects. Missing bootstrap
Object methods still CallError3. Casting/type-testing arrays IS supported below.

Constructor calls after successful super/this may use invokevirtual: selection
uses allocation dynamic class even before derived field initialization. Base
constructor may observe derived fields' default zero/null via overrides. Outer
uninitialized aliases remain governed by M4b's immediate-caller conversion.

## checkcast / instanceof
Both take a2-byte CONSTANT_Class operand. Predecode width3, exact truncation and
branch-boundary validation. Structurally validate CP index/tag/Class name UTF8 and
class/array name grammar; malformed TypeError(uint256 code,uint256 pc) code1.
Int/uninitialized operand BytecodeError14, bad handle ReferenceError1; don't forge
references or reinterpret object/array storage. Isolate malformed-input negatives
instead of relying on unspecified multi-fault precedence.

After structural validation, null checkcast preserves exact reference, null
instanceof pushes tagged int0. Do NOT load/resolve a well-formed missing target
for null. This shortcut also needs no lookup of a named interface and may handle
a structurally valid deferred-array target, without claiming allocation/storage
of those types. For non-null, resolve target WITHOUT INITIALIZING IT:
- missing named class LinkError4(pc);
- inaccessible target or interface/deferred-array target TypeError2(pc);
- other unsupported ordinary-class hierarchy/header forms retain existing errors.
Supported non-null targets: ordinary class/internal-name, java/lang/Object, [I.
Object-to-self/super/Object succeeds; int[] matches [I and Object; unrelated
ordinary classes or object/array combinations fail assignability normally.
instanceof returns tagged int1/0; checkcast preserves identity or throws Java
kind8 java.lang.ClassCastException. A valid array vs ordinary target is a normal
false/CCE result, NOT wrong-heap-kind validation. No target <clinit> execution.

Null-before-missing-target behavior was independently checked on local Java21
and JVMS SE8 6.5 checkcast/instanceof: null succeeds, non-null missing class fails
with JVM NoClassDefFoundError. Our supported-profile missing-class outcome stays
LinkError4, not a new linkage-error taxonomy. Review SE8 5.4.3.3/5.4.4/5.4.5 for
resolution/access/overrides; don't infer semantics from superficial method names.

## Java outcomes and ABI
Add ONLY JavaException8 java.lang.ClassCastException, exact canonical selector+
uint256 decoding in Go and exact CLI/Python allowed outcome class. Non-Error8
escaping active <clinit> becomes EIIE3; Errors2/7 and EVM OOG unchanged. No caught
exceptions/Throwable objects. Preserve kinds1..7 and unknown/noncanonical rejection.
Root/API/schema1 and printed value-or-exception protocol unchanged; no host refs.

## Independent tests and gates
Append~60-90 trusted Java8 cases stage m4c/defaultm4c, preserve prior713 sources,
manifest entries/expected outcomes/budgets. Fresh actual JVM comparisons, bounded
loops/heap/time/gas. No reference-JVM OOM or untrusted corpora. Cover base/child/
grandchild/inherited/final dispatch, int/void/reference methods, alternating dynamic
classes at one CP site, recursion, protected access, both package-private chains,
abstract/native/synchronized RESOLVED with ordinary override SELECTED, constructor
virtual callbacks/default derived fields, null NPE, class/array/Object casts/type
tests, direct CCE and initializer wrapping. No broader Object API calls.

Go verifier independently tests malformed CP/names/operands/branches, static/
private/constructor misuse, selected native/abstract/synchronized/no-Code, cache
separation, protected receiver and final-override mutation, bad/uninitialized refs,
array-receiver deferral, missing-target null/non-null ordering, target not initialized,
identity-preserving casts, exact new decoder/CCE/EIIE/OOG outcomes. Interfaces and
other arrays fail explicitly when non-null. For defensive unforgeable handles,
source review suffices; don't bypass earlier kind checks to manufacture fake success.

Parent integrates runtime->fixtures->verifier; independently reviews failures,
keeps exact assertions (fix only proven malformed tests), runs reproducible solc+
bootstrap, focused Go/CLI/31+ Python,713+ full oracle, smoke/fast/demos/AOT/vet and
new parent probes. No blanket budget increase or old expected-outcome relaxation.
Then accept with last-green SHA and advance to next dependency-ordered stage;
interface/reference-array work should be frozen separately after measured review.

## Ownership / isolated worktrees
Runtime ONLY: JVMSubsetInterpreter.sol/runtime.hex; jvmevm/jvmevm.go exact exception
decoder only; jvmevm/jvmevm_test.go expected hash only; jvmevm/integer_test.go decoder
tests only; new jvmevm/dispatch_test.go with runtimeM4c* helpers. No bootstrap/build
setting changes, fixture/harness/CLI/global changes, or other old-test edits. Report
any genuinely obsolete negative to parent for isolation/review, don't weaken it.
Fixtures ONLY jvmevm/testdata/differential/**. Preserve713, append m4c; Oracle root
protocol unchanged. Baseline runner initially rejects stage, use bounded manual
fresh JVM oracle checks if needed, not harness edits or fake EVM-green claims.
Verifier ONLY tools/java_diff.py, tools/test_java_diff.py, tools/JAVA_DIFF.md,
new jvmevm/dispatch_validation_test.go with verifyM4c* helpers. Initially red on
M4b artifact is expected, maintain exact errors and report evidence.
Parent owns AGENTS/plans/quickstart/Makefile and integration/independent review.
One monolithic Solidity writer. No worker spawning/peer writes/remote pushes/
global settings/untrusted oracle runs. Commit scoped owned files and return
hash/size/SHA/real verification/known failures honestly. Keep Sol/high and Fast.

## Accepted integration evidence
Runtime d22fcd4→b09c8f0, fixtures59e5aab→3d061bd, verifier440d285→44ddfaa.
Independent integration found2 negative issues: a supposedly missing method really
existed, and array-receiver deferral wrongly ran ordinary-class assignability.
Followup b7857ff→5bd82f3 corrected missing exact signature without weakening
CallError3 and enforced frozen array CallError4 ordering. Audit also proved/fixed
structural array rank>255 rejection with exact TypeError1 (JVM/JVMS corroborated).

Parent reran final artifact/bootstrap consistency, Go/CLI,34 Python,792/792 full,
331 smoke,351 fast, demos,AOT,focused vet and48 independent probes. Prior713
manifest entries/budgets unchanged. Probe archive:
`build/java-diff-parent-m4c/probe-00zyb_84/results-final/`.
Accepted runtime74469 bytes SHA256
`1e5736e346cea2c55a2aed3963822a1bf9be66eb57c0031b4c64603d64f5c941`.
Still local-runtime only and not full JVM. Next M4d reference arrays/covariance;
multianewarray is a separate following batch for allocation/rank/error-order review.
