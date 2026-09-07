# M3d: ordinary class hierarchies and declaring-owner semantics

Authority: `JAVA_EVM_PROGRAM.md`. M3c/header guard accepted at **600a1e4**.
Base behavior: 426 fixed cases, integer statics/init, raw bundles;
no new guest opcodes or JavaException kinds in this stage. Parent continues to
heap/reference capabilities after this bounded hierarchy increment.

## Scope
Add ordinary superclass chains for supplied classes, exact inherited static
method/field resolution, superclass-before-subclass initialization, and static
protected-member access. Keep interfaces/default methods, instance/virtual calls,
heap/reference values, handlers and other primitive types/forms deferred.

All superclass names/links, validation, lookup, subtype decisions, declaring-owner
storage and initialization scheduling execute INSIDE EVM. No host hierarchy
scanner, dependency loader, prelinker or evaluator. ABI/CLI/Go Run/RunClasses stay
unchanged. Missing parents are explicit errors, never ignored or loaded from disk.
The legacy single-class entry must inspect its header too: a required unsupplied
non-Object parent now fails as a missing superclass, not a successful wrong value.

## Normative rules to implement
JVMS SE8 §5.4.3.2 field resolution, §5.4.3.3 method resolution, §5.4.4 access and
§5.5 initialization:
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html

1. Validate/cache parent chains on active lookup/entry paths, independent of
   initialization state. Do not confuse legal A/B static initialization cycles
   with illegal superclass cycles. Parsed but unentered/unreferenced bundle
   classes need not eagerly link their parents or initialize.
2. Object may be an implicit terminal when java/lang/Object is absent. If an
   Object classfile is supplied, require its zero superclass; ordinary non-Object
   classes require a superclass. Do not invent native Object methods or a host
   bootstrap fallback. Interfaces/implemented-interface semantics remain rejected.
3. For static Methodref/Fieldref: search exact name+descriptor in symbolic owner
   first, then ordinary ancestors. First matching declaration wins (including
   shadowing); do not skip an inaccessible/nonstatic declaration to find a nicer
   ancestor. Existing Call/Field semantic checks apply after resolution.
4. Return the ACTUAL declaring owner and member index. Shared inherited statics
   have one storage slot in their declaring class; a subclass does not get a copy.
   A hidden field/method declaration is a separate member. Keep per-class CP/cache
   identity and actual declaring-class frame context.
5. Separate symbolic-class access from member access. Public members inherited
   from a nonpublic ancestor can be used through an accessible public subclass.
   Checking the ancestor's class-public flag again would wrongly reject this.
   Private members remain accessible only to their declaring class; package access
   uses caller/declaring packages. For STATIC protected members, same package OR
   caller subclass-of-declaring-owner suffices; no instance-receiver rule here.
6. Active use initializes the DECLARING owner of the resolved static member,
   not automatically the symbolic subclass. Loading/linking a subclass does not
   itself run its initializer. Root entry remains an unambiguous DECLARED static
   int-returning method (inherited root/Java-launcher lookup is still deferred).
7. To initialize C: mark C initializing and apply supported ConstantValues BEFORE
   initializing its superclass (JVMS5.5 step6), then execute C's own initializer.
   Even a class without <clinit> must initialize required superclass first.
   A same-thread request for initializing C from the parent's initializer must
   observe C's prepared/default/constant state without starting C.<clinit> early.
8. Preserve pending root/call/get/put operands/PC and class state across parent
   initialization. Use explicit bounded scheduler/continuation state, not host
   recursion. Final writes still require actual declaring-class <clinit>.
   No repeated constants reset or initializer execution through aliased references.
9. Parent initializer failure prevents child initializer execution. Arithmetic
   escaping an initializer remains kind3 EIIE; Error/StackOverflow remains kind2;
   hierarchy/validation/OOG failures remain genuine EVM errors. Handler/retry/
   erroneous-class observation is not newly claimed.

Maintain frame128/class64/CP4096/code65535/stack-local1024 resource profile. Any
VM continuation accounting must be explicit; avoid needless duplicate frames per
class. No-initializer Object-only old programs retain their existing frame limit.
Artifact already exceeds EIP170; keep direct local runtime execution caveat and
source reproducibility, not a deployment claim or host-native escape.

## Frozen hierarchy errors
Add `error HierarchyError(uint256 code, uint256 classIndex);`:
1. required direct superclass absent from supplied classes; index=child requiring it;
2. superclass cycle; index=first repeated class encountered in current parent walk;
3. attempts to extend a final class; index=offending child;
4. invalid superclass kind/zero-super rule (e.g. parent is interface, ordinary
   non-Object has zero super, Object has nonzero super); index=offending child;
5. inaccessible superclass class across packages; index=offending child.

Malformed superclass CP tags/indices/Utf8 retain ClassError. Root/interface or
implemented-interface profiles remain rejected by existing Method/Link errors;
HierarchyError4 specifically covers using an interface as a superclass.
Keep existing LinkError4 for a missing SYMBOLIC MEMBER OWNER, versus Hierarchy1
for a missing parent of a present class. CallError3/4 and FieldError2/3/4 retain
missing-member/type/access meanings; final writes remain FieldError4. No new host
Java-outcome decoding for hierarchy errors. Invalid-input error precedence beyond
these isolated cases is not full JVM-verifier conformance.

## Fixtures / verifier protocol
- Add cumulative stage m3d/default m3d; schema/CLI/outcomes/bundle paths unchanged.
- Preserve prior426 manifest entries/sources/outcomes/budgets. Append ~60–90
  trusted m3d cases: two/three-level hierarchies, inherited vs hidden fields and
  methods, overload descriptors, shared ancestor storage across siblings, actual
  declaring owner initialization, superclass order, subclass without <clinit>,
  reentrant parent reads/calls into initializing child, same-package/protected
  cross-package/static access, public inherited members of hidden ancestors.
- Include parent arithmetic initializer failure and normal arithmetic outside
  init; record true reference Java outcomes, not hardcoded answers. Interfaces,
  object construction, invokevirtual/invokespecial in entered code remain absent;
  javac's unentered constructors naturally contain invokespecial and are tolerated.
- Literal constants are often inlined: verifier should use valid test-only raw
  Fieldref redirection to force getstatic of a child ConstantValue while parent
  initializer runs, proving step6 timing rather than merely observing ldc.
- Fresh JVM process per oracle case; trusted code only. Keep bundle order variants,
  finite new-case gas<=50m/time<=10s, runtime hash equality and error separation.

## Parallel ownership
Assigned worktree only; no main/peer edits, other agents, remote push or global
configuration changes. Parent owns shared docs/Make/plans and integration.

| Worker | Allowed write set | Task |
|---|---|---|
| M3d-runtime | Solidity source/runtime hex; jvmevm/jvmevm_test.go(hash only); jvmevm/bundles_test.go(only obsolete custom-super negative); jvmevm/header_profile_test.go(only missing-parent and zero-super hierarchy expectations); NEW jvmevm/hierarchy_test.go | graph/link/access/init scheduler + inline tests + artifact/old regression |
| M3d-fixtures | jvmevm/testdata/differential/** only | new trusted hierarchy fixtures/manifest/reference runs, preserve old426 |
| M3d-verifier | tools/java_diff.py; tools/test_java_diff.py; tools/JAVA_DIFF.md; jvmevm/bundles_validation_test.go(only obsolete custom-super negative); NEW jvmevm/hierarchy_validation_test.go | stage metadata + independent exact hierarchy/access/storage/init tests |

Custom-superclass negative tests with parent supplied are obsolete feature tests:
replace only those with positive inherited/init behavior, retain interface errors.
The recent legacy header-guard missing-parent test must now expect Hierarchy1
instead of broad Link5; the zero-super ordinary-class case now uses Hierarchy4.
Keep actual-JVM initializer-effect rationale, exact malformed-super ClassError
location and interface guards. Do not run unrelated go test/vet ./...; focused
java package gates suffice and upstream broader checks have known environment issues. Do not edit Go exception decoder/ABI/CLI or other runtime tests.

Verifier should cover exact errors1–5, missing parent with file on disk but not in
bundle, duplicate-name/cyclic CP-parent alias handling, shared inherited storage,
hiding/overloads, symbolic-public vs declaring-hidden class access, static
protected rights vs unrelated callers, and initializer order/default/constant
visibility. Isolate the intended failure: don't include other unsupported opcodes
(e.g. l2i) when testing a field/access error. New tests are expected red on M3c;
compile/protocol checks may pass independently, never weaken/skip new assertions.
Use own trusted inline Java/test-only CF mutations, not peer worktree polling.

## Gate and continuation
Full old+new oracle suite, focused/runtime+independent Go validation, runner tests
with real smoke, pinned artifact, AOT/vet and parent independent probes. If a gas
budget genuinely regresses, worker reports measured failures; only parent may
explicitly version a performance allowance without weakening values/outcomes.
Commit last-green, update hierarchy/profile/init limitations, then automatically
plan primitive-array/reference heap work. No routine user re-confirmation.

## Status / independent acceptance

**M3d accepted; parent continues to integer-array/reference heap work.**

- Runtimeeec1f15→be0d910, fixtures0157727→30c1882,
  verifier5d60601→9410d57 reviewed/integrated in dependency order.
- Integration caught a Go test-helper name collision across disjoint files.
  Parent mechanically renamed only verifier helper/references to
  verifyM3dHierarchyClassIndex; no assertions/runtime semantics changed. Future
  worker contracts require role/stage-prefixed helper names.
- Pinned artifact matches source:32148 bytes, SHA-256
  `5540b5b5c5aede45bda17f89fa0b99313ad03d8f9249156ac613c2902031a920`.
  Still exceeds EIP170; direct local runtime.Execute only, no deployment claim.
- All prior426 manifest entries unchanged. Combined498/498 JVM/EVM outcomes pass;
  smoke165/165, fast185/185, 26 enabled runner tests, all focused Go/CLI including
  independent hierarchy validation, artifact checks, AOT regression and vet pass.
- Parent reviewed touched-path graph validation/cache, declaring-owner resolution,
  symbolic-class vs member access, protected static subtype checks and explicit
  initialization continuations. No host parsing/linking/evaluation additions.
- Exact independent HierarchyError1–5, malformed CP/interface guards, hiding/
  overload/private/public-hidden/protected access, sibling shared storage,
  declared-owner-only initialization, forced-getstatic child ConstantValue before
  parent, inherited final writes, errors/OOG and declared-root boundary all pass.
- Parent additionally generated40 fresh JVM/EVM cases combining parent/child
  reentrant init in both first-use orders, sibling shared storage, random int32
  values and shuffled bundle order. An unreferenced supplied class with missing
  parent and failing initializer stayed unlinked/uninitialized. All passed;
  evidence: `build/java-diff-parent-m3d/probe-z1cez4l5/results/`.
- Interface/default-method semantics, general objects/heap, handlers, remaining
  numeric/instruction forms and class libraries are still deferred. Resource cap
  counts root, Java frames and initialization continuations; no OpenJDK-capacity
  or general Java conformance claim.
