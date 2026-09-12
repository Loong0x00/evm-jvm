# MR0 direct-main normal transport preflight

Status: **COPY-only actual EVM execution evidence; not accepted or production.**
Base `b24d5ff40`; exact compiled candidates remain unchanged. This work only adds the
normal transport driver and durable receipt evidence under
`evidence/java-evm/main-root/transport-preflight/`.

## Scope and transport

The copied driver uses normal owned LevelDB/trie/StateDB persistence and public EVM
runtime calls. It uses the requested isolated LOCAL engine address
`0x4d52304d41494e454e47494e4500000000000001` only for the exact precompiled engine
runtime. Its distinct owner ordinarily CREATEs AS0, ZI0, DI0 and the coordinator.
The opaque generated ZIP is transported into AS0; EVM ZI0/DI0 resolves and inflates
all class bytes, and coordinator makes EVM paged DI0 `read` calls (each measured <=
4096). No raw-class execution input, host ZIP/class parser/inflater/catalogue,
Java evaluator, reflection, private Session, page injection, failed-trace recovery,
or engine/artifact change is used.

Pins checked before execution:

* engine: 295568 runtime bytes; SHA-256
  `5210271ce941ab322293ada29a551c30c1ac587eb5ab77538d8849025eb850d2`; Keccak
  `463dd2419b296aa39f766bdae06d11b49b9cffa935d052a38fe82921757e29de`;
* coordinator: runtime 3547, init 7381; runtime Keccak
  `b4785137ec9ccde676a5892b602a303e29356c14c7d6ca19db561d9526dfb67c`.

All actual calls use ordinary 100M gas. Existing bootstrap, heap/VFS/checkpoint,
1..4/65536, 1MiB and other profile limits are neither changed nor claimed enlarged.

## Actual results

1. The minimal `MainPositive` contains legal `main()` and
   `main(String[])`. EVM transported both generated classes (actual DI0 reads 566 and
   286), but `startMain` reverted `MethodError(2)`, selector `0x166ac6c3`, gas
   558386, no published-root change. This confirms the parent source finding:
   `_prepare` currently matches only method name, not descriptor. The exact raw
   receipt is `results/positive-overload-start-refusal.json`; no Solidity retarget
   was made.
2. `MainException` (one exact `main(String[])`) ran through the full EVM route.
   q1 and q7 both terminally produced lifecycle 3/`outcome=3` (Java exception),
   with equal 18 JVM and 5 internal steps. q1 took 19 epochs; q7 took 3. Both were
   resumed and terminally reopened in fresh processes, with engine-head,
   checkpoint-root/hash, coordinator-package and pin checks recorded in the two
   `exception-*-world-report.json` files.
3. Legal `MainRebind` saves the real root String[] then assigns `args=null`.
   q1 reached checkpoint epoch 3, then real `resumeMain` reverted
   `LC0StateError(7,0)` (`0x71540d20`; 5146253 gas) without root change. q7 instead
   reached normal VOID lifecycle 2 at epoch 1. This is the required actual quantum
   divergence from root-local validation, not a host/harness classification.

The actual engine ABI calls its retained integer member `result`, rather than the
legacy documentation name `legacyIntResult`. All driver reports render the explicit
main `outcome`: 1 RUNNING, 2 VOID, 3 Java exception. The `result` field is reserved
zero in these main receipts and is not a Java return.

## Limitation/blocker

Because the exact-name/descriptor source bug blocks the intended positive fixture,
there is no valid claim yet for normal successful positive main, root array identity
across all target slices, warm VM-domain cache, memory/disk equivalence, CAS/binding
or publication failure/retry, capacity, or descriptor/access negative suites. The
exception result proves only this bounded generated transport/persistence path.
It is not an accepted JVM/VFS profile, normal deployment, official-jar class handling,
or Minecraft/EULA/listener/world/Done result.

Reproduce with the tracked driver and fixture sources in a fresh ignored build
folder; run `python3 evidence/java-evm/main-root/transport-preflight/verify.py` to
check retained raw receipt relations and hashes. See its README for exact inputs and
process evidence.
