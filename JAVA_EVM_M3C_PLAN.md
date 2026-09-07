# M3c: integer static fields and ordinary-class initialization

Continuous authority: `JAVA_EVM_PROGRAM.md`. Last-green M3b: **90ccf13**,
341 oracle cases, 26 runner tests. Parent integrates this batch then continues
with hierarchy/member-resolution prerequisites before heap/reference work.
This remains a bounded slice, not arbitrary-Java/complete JVM or Minecraft.

## Scope
Add **getstatic 0xb2, putstatic 0xb3, category-1 dup 0x59**. Resolve tag9 Fieldrefs
and static **I-descriptor** fields inside EVM. Add class-local integer static
storage and execute `<clinit>()V` once before active use. Support both Run/legacy
single input and RunClasses bundles; unchanged ABI/CLI/result protocol except
one new known Java exception kind below. No host class parsing, static state,
initialization evaluation, prelinking or guest arithmetic.

Keep ordinary Object-superclass profile: custom-superclass initialization/search,
interfaces/default-method initialization, objects/references, non-I field access,
handlers, other types/forms, native/class libraries remain deferred. Do not
silently ignore unsupported semantics when they are accessed/entered. Unused
instance/non-I field metadata can remain unexecuted, like unused methods; this is
not full preparation/verifier support for those types.

## Specification references / semantic obligations
JVMS Java SE8 §5.4.2, §5.5 and §6.5 getstatic/putstatic:
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html
ConstantValue attribute semantics: §4.7.2,
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html

- Prepare supported static fields with zero values. Track each class's
  uninitialized/initializing/initialized state separately from local-variable
  initialization. Apply static I ConstantValue values when initialization starts,
  before `<clinit>` (JVMS5.5 step6), not by running every supplied class eagerly.
  Honor ConstantValue for static I fields even if ACC_FINAL is absent; the
  attribute on a nonstatic field is ignored (§4.7.2). Final-write checks are a
  separate rule, not a prerequisite for applying a static ConstantValue.
- Initialize before root invocation, before invokestatic of a not-yet-initialized
  declared owner, and before getstatic/putstatic of its declared field owner.
  No superclass lookup here; implicit Object is treated as bootstrap terminal.
- Initialize only active owners. Class input order must not determine initialization
  order. Constant literals inlined by javac do not cause the source holder's
  initializer to run merely because its classfile is supplied.
- Reentrant requests from the same executing thread for an initializing class
  succeed without restarting its initializer. Helpers inside `<clinit>` may read
  prepared default values; cycles across classes must match Java ordering.
- Initializers may call ordinary helpers/other initializers. Preserve pending
  root/call arguments and caller operands/PC across initialization. Especially:
  putstatic's value must survive a target initializer and be stored afterwards;
  getstatic must read after initialization, not a prematurely read default.
- No `<clinit>` means transition through initialization without executing code.
  Only one valid static ()V initializer is allowed; direct guest invokestatic
  of `<clinit>` or `<init>` is forbidden (CallError4), even if metadata looks usable.
- Final I writes are allowed ONLY in the declaring class's actual `<clinit>`
  method, not merely a helper called while an initializer is active. Re-check
  this per putstatic even if the Fieldref resolution was cached by a prior read.
- Static storage lives for one complete EVM invocation and is shared across its
  frames/classes. A new Run/RunClasses is a new VM execution with fresh statics,
  matching the current oracle's fresh Java process. No inter-invocation persistence.
- Keep int32 wraparound and class/package/private access rules. Fieldref caches
  must not collide with Methodrefs or same CP indices in another class. Cache
  identity/resolution, not invalid context-dependent final-write permission.

## Exception outcomes / limits
Keep JavaException kinds1 ArithmeticException and2 StackOverflowError.
Add exact kind **3 = java.lang.ExceptionInInitializerError** to the EVM outcome
and Go decoder. An uncaught ArithmeticException escaping ANY active initializer
(including from an ordinary helper it called) is wrapped as kind3. Outside
initialization it stays kind1. StackOverflowError is an Error and must remain
kind2 even during initialization; do not wrap it. OOG, Link/Call/Field/Init/
Class/Bytecode errors remain EVM failures and cannot become Java exceptions.

This is uncaught-outcome support only. Java catch/unwind is deferred; therefore
observable retry after failed initialization (NoClassDefFoundError on an erroneous
class), exception objects/causes, allocation failure during wrapper creation,
thread contention and general handler semantics are NOT claimed in this stage.
Structure state/dispatch so later unwinding can extend it without host escape.

Active-frame cap128 still includes initializer/pending frames as implemented;
record the exact profile and keep OOG distinct. Existing CP/code/local/stack/class
caps stay. Artifact may grow beyond EIP170's 24,576-byte deployment limit: this is
already a local runtime.Execute/SetCode harness, NOT a deployment workflow. Report
size honestly; do not add host execution or disable consensus checks to mask it.
Prefer shared loader/core code over duplicated legacy/bundle logic.

## Frozen validation errors
Add `error FieldError(uint256 code, uint256 location);`:
1. invalid Fieldref/Class/NameAndType/Utf8 tag/index/structure; location=get/put PC;
2. no unique declared name+descriptor field; location=get/put PC;
3. resolved field is nonstatic or descriptor unsupported (not I); location=PC;
4. illegal class/package/private/final-write access; location=PC;
5. invalid/duplicate/ill-sized I static ConstantValue attribute/index/tag;
   location=declared field index in its class (not an instruction offset).

Missing field owner uses LinkError4 at referencing instruction PC. Keep legacy
external METHOD CallError2. Existing LinkError5 remains entered interface/custom
superclass/other unsupported class profile, but no longer rejects `<clinit>` by
itself. Existing method/code errors otherwise retain meanings.

Add `error InitError(uint256 code, uint256 classIndex);`, code1 for duplicate or
invalid initializer signature/flags/missing/unusable Code/caps. Unsupported guest
opcodes or return-kind mismatch in otherwise entered initializer Code retain
ordinary BytecodeError/CallError semantics. Host does not decode these as Java
outcomes. Any failure precedent on multiply-malformed input is not full JVM
verification conformance.

## Fixture/oracle/harness extension
- Add cumulative stage `m3c`, default m3c. Schema1/outcome/bundle paths unchanged.
- Preserve all341 existing manifest entries/sources/budgets/outcomes; append
  roughly60–90 M3c cases. Include default-zero, ConstantValue fixtures, mutable
  field reads/writes, postincrement via dup, same names across classes, final
  initialization, private/package/public fields and caller-state preservation.
- Include root initializer, helper calls during init, repeated active use once,
  self/default-value reads, A/B initialization cycles in both first-use orders,
  unused supplied initializer and inlined final-constant holder (no eager init),
  target initializer before actual put/get, and fresh invocation reset.
- Expected kind3 uses existing `expected_kind:java_exception` plus
  `expected_exception:java.lang.ExceptionInInitializerError`. Add arithmetic
  outside init (kind1), during nested/helper init (kind3), and initializer
  recursion overflow (kind2), with reasonable finite gas/time.
- OracleMain currently initializes the root in Class.forName before reflective
  invoke. Extend it to serialize genuine initialization ExceptionInInitializerError
  and StackOverflowError thrown there, not mislabel them as harness crashes.
  Keep ClassNotFound/configuration errors nonzero, original value/body-exception
  behavior, and exact one-line protocol. It must ACTUALLY execute the reference
  JVM initializer, never invent an expected exception name.
- Non-hermetic oracle remains trusted test code running on host. Don't execute
  untrusted external corpora or add native/IO code to these fixtures.

## Parallel ownership
Assigned worktrees only, explicit local commits, no main/peer/remote/global edits
or spawned agents. Parent owns Make/shared docs/plans/integration. Workers use
own trusted inline fixtures or mock/reference tests; do not wait/poll peers.

| Worker | Allowed write set | Task |
|---|---|---|
| M3c-runtime | Solidity source/runtime hex; jvmevm/jvmevm.go (kind3 decode); jvmevm/jvmevm_test.go (hash + obsolete clinit-negative only); jvmevm/integer_test.go (decoder kind3 tests only); jvmevm/bundles_test.go (obsolete clinit-negative only); NEW jvmevm/statics_test.go | execution/storage/init scheduling, exact errors, inline semantic/failure tests, pinned artifact/regression |
| M3c-fixtures | jvmevm/testdata/differential/** only | append cases/sources + OracleMain root-initialization outcome handling; all reference runs |
| M3c-verifier | tools/java_diff.py; tools/test_java_diff.py; tools/JAVA_DIFF.md; jvmevm/bundles_validation_test.go (obsolete clinit-negative only); NEW jvmevm/statics_validation_test.go | stage/outcome tests and independent initialization/field validation |

Old Go assertions rejecting `<clinit>` are now obsolete FEATURE-negative tests,
not protected failures. Remove/replace just those cases and cover the formerly
rejected class as a positive initializer test; keep interface/superclass/native/
synchronized errors. Runtime worker changes its old basic/root and bundle tests;
verifier changes only its own bundles_validation initializer case. No weakening
other negative checks. Verifier new Go tests are test-first red on M3b: report
that honestly, compile-check if possible, do not skip or accept any generic revert.

Verifier should assert exact FieldError1–5/InitError1, readonly-cache-then-final-
write and helper-inside-init final-write rejection, bad constant/tag references,
root/callee initialization outcomes vs OOG, once/order/cycles and raw-EVM state.
Test-only classfile mutations are allowed to force true getstatic on ConstantValue
fields (javac normally inlines constants), but never in production APIs.

## Gates / automatic continuation
- Artifact match; focused Go/CLI + independent validation; Python tests including
  real legacy smoke; prior341 + new complete oracle suite; AOT and vet.
- Aim to retain prior gas budgets. Workers must not edit old cases to hide a
  slowdown: report reproducible measurements if a budget becomes a blocker.
  Parent may explicitly review/version a performance-budget change, never silently
  weaken semantic expectations or count OOG as a Java result.
- Parent independently probes initializer ordering/state isolation, operand
  preservation/final rules and known Java errors vs true EVM failures. Record
  size/deployment caveat, scope and last-green commit, then continue to hierarchy
  prerequisites/heap in a fresh bounded plan without routine confirmation.

## Status / independent acceptance

**M3c accepted after independent fixes; continue to M3d hierarchy prerequisites.**

- Runtime135fe43 integrated3676463; fixturesd442719→55ed126;
  verifier7134bef→e2fc661. Old341 manifest entries remain unchanged.
- Initial combined Go gate found a verifier-isolation error: a non-I field probe
  also emitted unimplemented l2i, so predecode correctly failed first. Follow-up
  verifier3ed2487→4a46313 changed that probe to getstatic B + ireturn, kept exact
  FieldError3, and retained a separate exact BytecodeError(6,3) l2i-order test.
- Parent then found a REAL legacy header gap: custom-super/interface initializers
  were silently omitted, giving0 where actual JVM gave7/9. Follow-up runtime
  guard4b3ae0f→f156299 validates superclass metadata and rejects unsupported
  legacy headers with LinkError(5,0), preserving MethodError7 for direct interface
  roots. No host parent loading or fake success. Parent/probe evidence and new
  header_profile_test.go guard this until M3d provides actual hierarchy support.
- Final pinned artifact: **29899 bytes**, SHA-256
  `92735b7f7272587b3e4109a3cbfd84d9fa5e019e40b0392f3a8d030799e76796`.
  Above EIP170's24576 deployment limit: accepted only in this direct temporary
  runtime.Execute/SetCode harness. No CREATE/mainnet deployment claim/core changes.
- Final make java-test passes focused Go/CLI and independent static/header
  validations, 26 enabled Python tests, and **426/426** actual JVM/EVM outcomes:
  407 values, 11 ArithmeticExceptions, 3 StackOverflowErrors, 5 EIIEs. Prior341
  inputs/budgets preserved. AOT, focused vet and artifact rebuild checks pass.
- Parent reviewed static storage/ConstantValue timing, retry-PC/operand retention,
  same-thread initializing state, final-write permission after cache hits, actual
  initializer frames and exact error/outcome decoding. Independent tests include
  FieldError1–5/InitError1, static-nonfinal ConstantValue, ignored instance value,
  helper final-write denial, initialization cycles/laziness/reset, EIIE vs Error/OOG.
- Parent generated36 new JVM/EVM initialization-trace/cycle/postincrement/overflow
  cases with shuffled bundles and fresh runs: all passed. Local replay evidence:
  `build/java-diff-parent-m3c/probe-t_rixta4/results/`. Header divergence/guard
  evidence: `build/java-diff-parent-m3c-header/probe-26p490yl/`.
- Pre-header-guard runtime worker measured old341 aggregate gas +4.14% with all
  budgets passing; final header guard adds small validation cost. No semantic
  expectations or historical budgets were weakened. Demo remains within limits.
- Worker additionally attempted broad upstream checks: reported a node test blocked
  by an existing port7878 listener and an existing logger vet warning. These are
  outside this scoped acceptance; no unrelated service/config/core changes made.
- Still no superclass/interface semantics, heap/reference types, handlers, retry
  of failed initialization, full exception objects/causes, class library or JVM
  conformance claim. Those remain queued capability work.
