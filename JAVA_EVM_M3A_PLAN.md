# M3a: same-class static calls, explicit Java frames and recursion

Authority: `JAVA_EVM_PROGRAM.md` (continuous parent orchestration). Previous
last-green M2b checkpoint: **3e53fae**, 201 oracle cases, 19 harness tests.
Parent integrates this batch and then proceeds to the next class/heap capability
slice; workers implement only their assigned scope. No Minecraft tasks.

## Scope and execution boundary
Implement same-class `invokestatic` (0xb8), internal void `return` (0xb1), and
category-1 `pop` (0x57, for discarded int call results). Preserve every M2b opcode
and outcome. Root entry remains an unambiguous named static `(int...)int` method;
ABI remains raw single class + name + int32 args. Internal static methods may be
private and/or overloaded; resolve using exact **name AND descriptor** from the
constant pool. Internal returns may be I or V; parameters remain I only.

Every guest method lookup, constant-pool reference resolution, argument transfer,
frame creation, PC/operand/local handling and return runs INSIDE EVM. No host
pre-linking, call evaluation, method extraction, recursion or native shim.

### JVM references / expected semantics
Reference: Java SE 8 JVMS §6.5 invokestatic/ireturn/return, §2.6 frames and §6.3
VM errors: https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html
No receiver for invokestatic; caller pops descriptor-ordered arguments into
callee local slots starting at zero. Value return pushes one int to caller;
void return pushes nothing. Caller resumes immediately after its call and keeps
its own remaining stack/locals. Recursion requires independent frames.

The full JVMS also permits InterfaceMethodref static calls; **this stage accepts
only CONSTANT_Methodref (tag10) for the same ordinary class**. Interface/external
owners and non-int descriptors remain explicit unsupported capabilities.

## Runtime design constraints
- Parse enough CONSTANT_Class, CONSTANT_Methodref, CONSTANT_NameAndType and Utf8
  relationships inside EVM to resolve calls. Validate tags/indices and method
  signatures; compare owner class names, not just CP index identity.
- Preserve unselected constructor/other-method tolerance. Do NOT reject all
  unused String-returning/unsupported methods: M2b ldc_w tests intentionally
  contain 270 unused String methods. Only entered methods require this execution
  subset. Store bounded metadata and lazily validate/predecode entered methods;
  cache within the invocation where useful to avoid reparsing per recursion.
- Prefer an explicit iterative Java-frame stack in EVM memory over Solidity
  recursive execution. Frame state includes its own method/PC/sp/locals/operand
  stack and initialization state. No cross-frame aliasing of mutable values.
- Caller arguments are popped only after bounds/signature checks. Preserve
  expression-prefix operands on the caller stack and validate return stack/shape.
- Root name ambiguity still fails; unrelated overloaded helpers must not make
  the root ambiguous. Internal overload selection is exact by descriptor.
- Keep class initialization, objects/arrays, references, instance/interface
  calls, synchronized/native/abstract methods and exception tables unsupported.
  Existing methods/flags/class-init rejection remains. No new arithmetic/forms
  beyond the three explicitly required call-related opcodes.
- Previous 201 fixture entries/expected outcomes/gas budgets are protected.
  Don't enlarge them to hide overhead; design bounded metadata/caching sensibly.
  Maintain code/stack/local/CP caps; method metadata cap, if needed, must permit
  existing wide-constant fixtures with >270 methods. Explicitly document limits.

## Frozen call/exception errors
Add Solidity `error CallError(uint256 code, uint256 pc);` for explicit rejections.
For codes 1–4, pc is the invokestatic offset in the caller. For code 5, pc is the
mismatched return offset in the entered method (clarified during independent
integration; tested exactly rather than leaving pc ambiguous):
1. invalid Methodref/Class/NameAndType/Utf8 tag, index or structure;
2. owner is not the same ordinary class (external/interface owners unsupported);
3. no unique method with exact name+descriptor;
4. target not static, forbidden semantic flags/descriptor, or unusable Code;
5. return opcode inconsistent with entered method's I/V descriptor.
Argument/operand stack underflow remains BytecodeError(3, pc); truncated
instructions remain BytecodeError(2, pc). Keep other existing error codes intact.
Malformed unused class structures need not be a full verifier, but should not
panic/crash the host or silently run with wrong semantics.

**Frames limit:** 128 active Java frames including the root. On a push beyond
this limit, emit `JavaException(uint256)` kind **2 = java.lang.StackOverflowError**.
This is an explicit implementation resource cap, not a promise to match OpenJDK's
stack capacity. Other memory/gas caps still apply; low-gas execution must remain
OOG rather than a fabricated StackOverflowError. Both values and known uncaught
Java outcomes keep the same CLI/Run protocol.

M2b kind1 ArithmeticException propagates from a callee as an uncaught root
outcome. There is no catch/unwind/handler support yet. Go may decode only exact
known JavaException payloads (kinds1 and2); unknown kinds and CallError remain
ordinary EVM errors. Update the old decoder's unknown-kind test to another
unknown value (e.g.255), not remove strictness tests.

## Frozen harness/fixture extension
- Add stage `m3a`; selection is cumulative m1 < m2 < m2b < m3a; `all` includes all;
  runner default becomes m3a. Existing schema/outcome formats unchanged.
- Append roughly 50–90 new m3a manifest cases (old201 untouched). Include nested
  calls, multi-argument order, preserved expression prefixes/locals, zero-argument
  and private helpers, internal overloads, void-return and discarded int result,
  bounded direct/mutual recursion, factorial and recursive Fibonacci.
- Include callee divide-zero outcomes (kind1) and an infinite-recursion expected
  StackOverflowError (kind2). OracleMain already supports arbitrary guest Throwable
  class via InvocationTargetException; compare ACTUAL reference class names.
- Keep recursive Fibonacci inputs modest (e.g.<=10); naive exponential work is
  not the goal. Use finite reasonable new-case gas up to50m and timeout<=10s.
- No root overloads/void/non-int parameters; helpers can be overloaded/void.
  No cross-class positive cases until a raw multi-class protocol is implemented.

## Parallel work / ownership
Each worker reads this and AGENTS/program, works in assigned worktree/branch,
commits explicit paths, reports commands/evidence, and returns. No subagents,
main/peer edits, remote pushes or global changes. Parent owns Make/shared docs.

| Worker | Allowed write set | Independent task |
|---|---|---|
| M3a-runtime | jvmevm/runtime/JVMSubsetInterpreter.sol + runtime.hex; jvmevm/jvmevm.go (kind2 output decode only); jvmevm/jvmevm_test.go (artifact hash only); jvmevm/integer_test.go (decoder known/unknown kind tests only); NEW jvmevm/calls_test.go | implementation + inline Java positive/negative/recursion tests, pinned artifact, old regression |
| M3a-fixtures | jvmevm/testdata/differential/** only | append reference fixtures/cases, preserve old201, actual JVM and javap validation |
| M3a-verifier | tools/java_diff.py; tools/test_java_diff.py; tools/JAVA_DIFF.md; NEW jvmevm/calls_validation_test.go | stage protocol + independently authored malformed-call/return/frame-isolation tests |

Verifier does NOT implement runtime or edit other Go tests. Go tests can use
existing test-only compileJava/parseTestClass helpers and own CP-offset helper;
all guest mutation is test-only. Test invalid CP refs (CallError1), external owner
(2), missing signature (3), invalid callee flags/nonstatic (4), return-kind
mismatch (5), stack underflow/truncation and correct caller state on a positive
multi-argument call. Prefer exact custom-error selector/code assertions, not any
revert. Tests expecting new opcodes will initially fail against baseline M2b:
report those expected red results explicitly, compile-check the tests, don't
weaken/skip them or wait/poll runtime peer. Harness tests/stage changes can be
verified with temporary/mocked fixtures and existing real M2b smoke independently.

Runtime/fixtures workers don't depend on peer files: use own inline Java tests or
actual reference JVM runs until integration. Only parent merges the combined
revision and judges full green.

## Acceptance / next continuation
1. Review scoped commits and check source architecture/host boundary.
2. Pinned artifact source matches; full prior201 + new oracle cases, focused Go
   including independent validation tests, Python tests, AOT regression and vet.
3. Parent independently probes caller stack/local isolation, overload argument
   order, recursion/returns, callee exception propagation, frame cap vs OOG and
   exact invalid-reference outcomes. Same runtime across all raw classes.
4. Local last-green commit; update capability/profile/limits. **Continue** to a
   new dependency-ordered stage (raw multi-class loading/linking/static state or
   remaining integer execution forms, then heap), not a routine confirmation stop.

## Status / independent acceptance

**M3a accepted; continue to M3b raw multi-class loading/linking.**

- Runtime `231c169` integrated as `3fe3235`; fixtures `d095e62` as `d297dd7`;
  independent verifier `baf4378` as `46e04aa`. Scoped writes reviewed.
- Pinned artifact matches source: 13,343 bytes, SHA-256
  `e5da633eda34db0ce3a02563fd6276c8016525d441025eb446b578fdef8a390b`.
- Parent inspected iterative Frame[] execution, packed per-class constant/method
  metadata, lazy entered-method validation, exact overload/owner-name lookup,
  cached references, independent frame state and ordered argument/return handling.
  Host change is only exact kind2 outcome decoding; no host Java resolution.
- All prior 201 manifest entries remain exactly unchanged. Combined suite passed
  **268/268** (261 values, 6 ArithmeticExceptions, 1 StackOverflowError), along
  with focused runtime/CLI + independent malformed-call tests, 21 harness tests,
  AOT regression, artifact check and go vet.
- Independent verifier tests pass exact CallError codes1–5, malformed CP chains,
  caller stack/local preservation, internal overloads, duplicate CP owner with
  the same class name, void/pop, argument underflow and truncation. Parent
  resolved the code5 pc ambiguity: it identifies the entered method's return
  offset, and strengthened both return-mismatch tests to assert that exact pc.
- Parent added 40 new actual-JVM differential probes with independent recursive
  source, random int32 seeds/carries, expression prefixes and saved local values;
  all passed. Local evidence: `build/java-diff-parent-m3a/probe-e26u6z5w/results/`.
- Exact cap probe on a directly recursive method: depth argument127 (128 frames
  including root) returns127; argument128 emits StackOverflowError. At gas1000
  the same call remains genuine OOG, not a Java stack exception. The 128-frame
  limit is an explicit resource profile, not OpenJDK-capacity compatibility.
- Representative fixture results: recursiveFactorial(10)=3628800 at537043 gas;
  recursiveFibonacci(10)=55 at3773347; infinite-recursion StackOverflowError at
  1520845. Gas varies with the complete class shape.
- No handlers, reference values/objects/arrays, external class linking, class
  initialization or class-library support is claimed. Those remain queued.
