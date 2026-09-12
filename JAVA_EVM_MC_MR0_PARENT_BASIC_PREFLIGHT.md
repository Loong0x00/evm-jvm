# MR0 repaired kernel: parent basic replay

**Independent generated-main kernel/basic replay passed; full MR0 Session/profile
acceptance remains blocked.** Worker a2efa63fa integrated1533b244d. Selected-table
optimization1d56cde9a is separate and NOT merged here. Accepted4/65536/38 bootstraps,
heap/VFS/checkpoint limits and production sources unchanged. No original Java,
Minecraft/EULA/listener/world/Done or push.

Parent inspected the exact two source changes: main name+descriptor selection;
initial-input validation immediately after allocation instead of freezing mutable
local0 at every pending checkpoint. `_prepare` descriptor fields match parsed
method metadata. Resume does not reinstall/recreate arguments. Coordinator delta
is only its engine pin. Original compiled candidate and both failures remain.

Parent copied SOURCE ONLY to a fresh ignored build, independently compiled pinned
solc0.8.30/opt200/viaIR/Cancun/metadataoff, and rebuilt/vetted the exact worker Go
driver. Absolute scoped TMPDIR avoids the worker wrapper's relative TMPDIR becoming
invalid after its `cd`. No archived artifact fallback. Whole monitored final gate:
**197.311341s,882098176B sampled process-group peak, exit0**,20min/4GiB envelope.
Engine294795B SHA256`5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875`,
Keccak`2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f`;
coordinator3547B Keccak`06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c`.
Oversized engine is labeled LOCAL initial-state installation, not CREATE; other
controllers/pages use ordinary CREATE in the normal owned opaque-ZIP EVM pipeline.

12 new worlds, q1/q7/direct4096 for each generated case:

|Guest|q1/q7/direct epochs|Java/internal|Outcome|
|---|---|---|---|
|Overloaded MainPositive+Helper|319/46/1|319/3|VOID|
|args=null|7/1/1|7/2|VOID|
|args=new String[1], retained initial array|24/4/1|24/2|VOID|
|Uncaught RuntimeException|19/3/1|18/5|JAVA_EXCEPTION|

All three quanta have equal terminal machine/VFS roots AND byte-identical opaque
machine payloads after the280-byte envelope. Reserved `result` remains zero, not
an invented Java int return. Both runtime/code pins checked in EVERY world.
Actual driver counters show<=100M and<=30s on all observed calls; this establishes
observed compliance, not that the worker harness enforces a per-call watchdog.
36 actual setup/finish/verify processes have external PID/command/exit receipts.

The first parent gate reached all12 EVM terminal worlds but failed an overly strong
parent assertion that every no-op finish persists its process PID. Direct-terminal
exception finish actually opens/closes without republishing the manifest; verify
therefore persists two IDs, not three. Parent preserves that failure and its state,
records actual external process launches on the fresh final run, and checks the
precise2-vs3 manifest behavior instead of fabricating fsync/PID evidence.

## Remaining acceptance gaps from independent source review

* Current worker harness is a normal self-owned StateDB/trie probe, not yet the
  full strict COPY Session contract. `coordinatorCall` mutates decoded manifest/
  writes checkpoint before publication and panics on publication error; broad
  normal-path atomic failure/poison/CAS/initial-install tests are not proven.
* `applyDecoded` lacks comprehensive per-slice typed outcome/schema/epoch/counter/
  VFS/event validation; manifest drops JavaRef; most resumes have no full receipt.
* DI0 trace records requested sizes on enter, not canonical returned fragment
  bytes/length/offset/success and exact resource identity on exit.
* Worker strict verifier checks some code pins with list membership, not all-world
  equality, and compares outcome counters rather than terminal state/payload. Its
  fresh-directory name guard is not evidence that a file originated in a fresh run.
  Parent improved all-world pins and terminal equality here, not every other gap.
* Missing exact-method/duplicate/access/native/abstract/synchronized/old selector,
  legal local-slot integer reuse, full transport binding/tamper/page/size cases,
  warm/memory equivalence and real publication fault matrix still need completion.
* Worker wrapper's declared4GiB is not measured RSS. Parent canonical watchdog
  does supply actual sampled group RSS for this independent basic gate.

Evidence `evidence/java-evm/main-root/parent-a2efa63fa/`: run_basic.py, whole logs/
watchdogs,12-world summaries, sources/artifacts, process receipts, checkpoints and
retained first failure. Next scope is Go-only strict MR0 transport/persistence
against exactly these immutable engine/coordinator pins; no Solidity optimization,
new argv, capacity promotion or official-JAR execution is authorized by this result.
