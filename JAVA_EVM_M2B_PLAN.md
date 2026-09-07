# M2b: integer expressions and explicit uncaught Java outcomes

Current program authority: `JAVA_EVM_PROGRAM.md`. The user authorized continuing
through stages without asking after each gate. This batch starts from accepted
M2a at 3216753. Three Sol/high workers; parent integrates and then proceeds to
M3a static calls/frames. No Minecraft work.

## Scope / runtime contract
Retain all M2a behavior and the raw-classfile EVM-only execution invariant.
Add only this instruction slice:
- ldc (0x12), ldc_w (0x13), **CONSTANT_Integer only**
- imul (0x68), idiv (0x6c), irem (0x70), ineg (0x74)
- ishl (0x78), ishr (0x7a), iushr (0x7c)
- iand (0x7e), ior (0x80), ixor (0x82)
- i2b (0x91), i2c (0x92), i2s (0x93)

No calls, object/reference values, arrays, wide, switch, stack permutation forms,
other numeric types, exception handlers, native bridges or additional features
in this worker batch. Those remain queued program tasks. Existing error code
semantics in negative tests must not be changed accidentally.

Semantics: Java int32 wraparound; division truncates toward zero; remainder has
Java sign behavior; INT_MIN/-1 returns INT_MIN and its remainder is zero without
Solidity overflow panic. Shift counts are masked with 31; distinguish signed
ishr from unsigned iushr. Conversions sign-extend byte/short and zero-extend char.
Constant-pool integer tag/index/value resolution occurs INSIDE EVM. Reject non-int
ldc/ldc_w references and invalid indices explicitly. Keep instruction predecode
and branch boundary validation entirely inside EVM.

## Frozen Java exception outcome protocol
Uncaught idiv/irem by zero is an actual Java `ArithmeticException`, **not a generic
unsupported-bytecode/EVM failure**. Exception handlers and unwinding are NOT in
this batch. Provide a precise temporary top-level uncaught outcome that later
frame/handler implementation can preserve externally.

- Solidity declaration: `error JavaException(uint256 kind);`
- kind 1 = `java.lang.ArithmeticException`. The EVM interpreter checks divisor
  and emits this only for actual guest arithmetic exceptions. It must not rely
  on Solidity Panic as the guest exception representation.
- Go `jvmevm.Result` adds `ExceptionClass string`. `Run` decodes ONLY exact
  JavaException selector + 36-byte payload + known kind 1 into that result and
  returns nil error for a successfully interpreted uncaught Java outcome. This
  is output decoding, not host guest execution. Keep measured gas and raw data.
  Unknown error selectors/kinds/lengths, class/bytecode errors and OOG remain
  Go errors. Never convert all EVM reverts into Java exceptions.
- CLI common stdout keys remain engine, runtime_bytes, runtime_sha256, gas_used.
  Exactly one outcome key: `result=<signed int32>` OR
  `exception=java.lang.ArithmeticException`. Both successful value and known
  Java-exception outcomes exit 0. EVM/harness failures still exit nonzero/stderr.
  This is a method-invocation test CLI convention, not a Java launcher exit-code
  compatibility claim. Preserve existing successful value output exactly.

## Frozen manifest / differential protocol extension
Base schema_version remains 1 (additive extension). Existing 82 entries remain
unchanged; no weakening gas/timeout budgets or expected semantics to get green.
- Add stage `m2b`: m1 selects m1; m2 selects m1+m2; m2b/all select all three.
  New runner default stage becomes `m2b`. Smoke/fast/full/--case behavior unchanged.
- Existing `expected_kind: "value"` unchanged.
- New exception cases: `expected_kind: "java_exception"` and required
  `expected_exception: "java.lang.ArithmeticException"` (require a syntactically
  valid fully-qualified class name; all current new cases use this class).
- Existing OracleMain stdout already supports `exception=<fqcn>` from actual
  guest InvocationTargetException. JVM reference result—not a hardcoded expected
  answer—is compared to EVM result. A matching exception class may count as pass
  ONLY for an explicitly expected java_exception case, with expected class also
  checked against reference. Value vs exception disagreement is failure.
- Report fields include oracle_exception and evm_exception where applicable;
  distinguish expected matched Java outcome from EVM revert/OOG, unexpected
  oracle exception, malformed protocol and harness errors. Record same runtime
  hash across values AND exception outcomes. No silent unsupported skips.
- All previous strict validation, bounded execution, preserved run output,
  replay and metadata requirements remain. Same fixture/runner paths and flags.

## Parallel ownership
Workers operate only in assigned worktree/branch. No shared docs/Makefile edits,
no remote push, global changes, subagents or edits to peers/main tree. Parent
owns program/stage docs, AGENTS, Makefile and integration.

| Task | Write set | Required evidence |
|---|---|---|
| M2b-runtime | jvmevm/runtime/JVMSubsetInterpreter.sol + runtime.hex; jvmevm/jvmevm.go; cmd/jvmevm/main.go; jvmevm/jvmevm_test.go; NEW jvmevm/integer_test.go; optional NEW cmd/jvmevm/main_test.go | pinned artifact build/check; focused previous+new Go tests; signed arithmetic/casts/shift/ldc(_w), typed zero-divisor outcome vs genuine EVM errors; ABI output boundary unchanged except decoded outcomes |
| M2b-fixtures | jvmevm/testdata/differential/** only | append ~80–120 fixed new stage cases/classes; preserve old entries; actual javac/java oracle runs; javap confirms exact opcodes including ldc_w; document exception cases |
| M2b-harness | tools/java_diff.py; tools/test_java_diff.py; tools/JAVA_DIFF.md only | stage/manifest/outcome protocol extension, deliberate value/exception mismatches and malformed exception output tests, runtime hash divergence across outcomes, expected exception matching, retained timeouts/replay safety |

Workers don't wait/poll other branches. Runtime worker creates own inline Java
Go fixtures. Fixtures worker validates old stage against current runtime but
new cases against actual reference JVM only until integration. Harness worker
uses mocks and a temporary M1 real smoke fixture; new real exception tests run
after parent integrates runtime. Scoping old expected unsupported-imul test:
replace it with a genuinely still-unsupported instruction (e.g. newarray),
retain the negative-error purpose and make the reason explicit in the diff.

## Tests / stage acceptance
- Previous 82 cases remain green under their existing finite budgets.
- New int32 add/mul/neg/casts/shift/constant/div/rem edges compare to actual JVM,
  including negative divisors, INT_MIN/-1 and masked negative/large shift counts.
- Both zero-divisor instructions match `java.lang.ArithmeticException` on JVM and
  EVM. They are not catch/unwind support. Generic reverts/OOG remain failed tests.
- Real ldc_w with pool index >255, wrong/noninteger/out-of-range constant indices
  and truncated instruction tests. No host constant-pool preprocessing in Run.
- Same interpreter artifact handles all old/new classes, arguments and outcomes.
- Build pinned source/artifact consistency; focused Go and Python tests, complete
  combined oracle suite and prior AOT/vet. Parent independently reviews and probes.
- Commit local last-green milestone, update profile/queue; **automatically plan
  and dispatch M3a** after acceptance (no routine user re-confirmation).

## Status
Protocol frozen for the next three workers. No claim M2b is implemented yet.
