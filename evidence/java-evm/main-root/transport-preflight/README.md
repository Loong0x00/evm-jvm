# MR0 normal transport/execution preflight

Status: **COPY-only measured preflight, not accepted.** `driver.go.txt` is copied to a
fresh ignored `build/java-diff-mc-main-root-transport-*` directory and uses a normal
LevelDB-backed `StateDB`/trie plus public `core/vm/runtime` calls. It does not use a
CB0 private session, reflection, raw-class API, host ZIP parser/inflater/catalogue,
StateDB page injection, or trace recovery.

The driver reads the generated ZIP once as opaque transport input, ordinarily CREATEs
AS0, ZI0, DI0 and the exact MR0 coordinator, and lets coordinator `_loadAll` make the
actual <=4096-byte DI0 `read` calls. The only LOCAL installation is the requested
engine address `0x4d52304d41494e454e47494e4500000000000001`, whose runtime is
checked as 295568 bytes, SHA-256
`5210271ce941ab322293ada29a551c30c1ac587eb5ab77538d8849025eb850d2`, Keccak
`463dd2419b296aa39f766bdae06d11b49b9cffa935d052a38fe82921757e29de`.
The owner is deliberately distinct from that address. Coordinator runtime pin is
`b4785137ec9ccde676a5892b602a303e29356c14c7d6ca19db561d9526dfb67c`.

## Actual results

* `positive-overload-start-refusal.json` is a real positive-fixture transport call:
  both `MainPositive.class` (566 bytes) and `MainHelper.class` (286 bytes) were read
  by DI0, then `startMain` reverted `MethodError(2)` (`0x166ac6c3`, full word 2),
  558386 gas, with unchanged published root. This confirms the source finding:
  `_prepare` selects only `wantedMethod` and does not filter the descriptor. No
  compiler/engine expectation was changed.
* Exception-only fixture reached ordinary EVM checkpoints and terminal Java-exception
  lifecycle (`outcome=3`, `lifecycle=3`): q1 took 19 slices / 18 JVM steps; q7 took
  3 slices / 18 JVM steps. Both terminal worlds were reopened in fresh processes and
  checked against engine `head`, opaque checkpoint hash, coordinator package root and
  fixed engine pin. q1's final checkpoint root is
  `0x840fd7887c88f374b8c1a5b8c4e320c9d604be97409ca0404c185b3ede85384a`; q7's is
  `0x7a7043d72e63acbe940a2a21c209904e714fd091f786f1ff5ff519946342cbe4`.
* Legal `MainRebind` saves the supplied `String[]`, writes `args=null`, and returns.
  q1 reaches epoch 3 then `resumeMain` reverts `LC0StateError(7,0)`
  (`0x71540d20`), 5146253 gas, after its single 267-byte DI0 read, preserving the
  prior root. q7 reaches ordinary VOID terminal (`lifecycle=2`, epoch 1). This is a
  measured quantum divergence from `_validateMainRootLocal`; it is not masked.

The engine ABI names the retained int field `result`, not `legacyIntResult` as older
notes said. This harness records the actual `outcome` tag explicitly: 1 RUNNING,
2 VOID terminal, 3 Java exception; `result` remains zero in every main receipt and
is never treated as a Java int return.

## Limits and remaining work

The overload blocker means the intended positive main and its warm-cache, memory/disk
root-equivalence, CAS, binding/tamper, publication-failure/retry, capacity, and
wrong-descriptor gates cannot honestly be promoted from this run. The exception route
shows ordinary transport/persistence only; it does not prove a successful normal
main, rebind-safe checkpointing, or any Minecraft/official-JAR behavior.

`verify.py` is receipt-only and validates the copied JSON evidence. `SHA256SUMS`
covers the tracked driver, fixture/oracle sources, receipts, and verifier.
