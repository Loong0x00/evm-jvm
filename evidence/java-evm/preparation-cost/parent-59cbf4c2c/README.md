# Independent preparation-cost attribution

JAVA_EVM_MC_PREPARATION_COST_PARENT_PREFLIGHT.md is canonical. No optimization or
accepted profile change. Worker raw products remain immutable. Its outer1200s
run lacked sampled RSS; its comparison/reconciliation claims needed actual checks.
Parent fixes the child-call pending-key cleanup, checks both code hashes/source IDs,
and records real EVM memory expansion/free-pointer writes, not guest heap or host RSS.

Fresh full source/debug rebuild+seven calls:419.030s/936648704B completewatchdog.
Fresh-world replay with the same independently rebuilt/hashed executable plus
strict analysis/vet/protected checks:58.513s/522731520B separatecompletewatchdog.
First second-replay failed before EVM: copyfile omitted executable permission;
final-replay.log/watchdog preserved, copy2 fixed only harness, new output path.

run.py reconstructs/compiles only copied code and observer; replay_existing.py
re-executes in fresh worlds using that exact code, not old outcomes. analyze.py
asserts exact parent untraced receipt fields, opcode/PC/source identity, per-address
and total inclusive/exclusive frame accounting, zero-value child forwarding and
memory-expansion reconciliation. Named-source bucket0 is not proof a phase was
never reached. functionDebugData/optimizedIR/free-pointer counts separately identify
736B Selected allocations and emitted region146431..146622. final/ keeps compiler
products, actual trace driver, all raw aggregates, strict report and IR excerpt.
No millions-of-op rows; no failed-trace recovery or fabricated Java state.

Use NEW ignored build/java-diff-mc-capacity-cost-* directories. Old snapshots/logs
must not be overwritten; TMPDIR is scoped to each build. Current accepted CB0 remains
4/65536, and the observed8/256 capacity copy is still not promoted. No original
Minecraft Java/JAR handling/startup/EULA/listener/world/Done or push.
