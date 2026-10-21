# Equivalence-preserving iteration performance work (user authorized)

Current accepted anchor: P34, unchanged geth EVM/charging/consensus, interpreter398336B under1MiB runtime cap, checkpoint2MiB,100bootstrap images/native21/raw150/1063930. User now explicitly requests performance optimization while preserving equivalence, followed by GitHub sync of current `java-on-evm` branch to `origin` (`Loong0x00/evm-jvm`), not upstream/otherbranches/forcepush. This supersedes the earlier no-push directive only for this requested sync. Worker/network restrictions remain.

## Measured baseline (latest complete original86)

-700.916126s total;1,920,904 counted JVM instructions/93internalsteps/36successful checkpoints.
-60.680454s setup,466.000818s successful Resume process time,174.101553s failed localization,0.063603s reopen.
-17failed localization calls after authenticated missing-class errors. First failure already names exact missing class at q65536/lastsuccessful JVM1,900,544; seven later successful small slices and sixteen further refusals refine the frontier.
-Accounting on this same trace: stopping after the first authenticated missing-class refusal would end at417.020035s. This is a **counterfactual trace accounting, not a new measured benchmark**.
-Current call gas is uint64.max, quantum65536, publicCancel60s. The EVM runs a synchronous interpreter loop; gas is not a wall-clock ticker. Host speed also depends on IPC/cache/memory/tracing/StateDB I/O, not CPUfrequency alone.

## Work A: discovery controller, not relaxed acceptance

Add explicit modes: unchanged precise/q1 acceptance, and discovery that may stop at an authenticated **MCEntryMissingClass** with canonical ABI, preserved root/head, zero returned checkpoint. Do not skip arbitrary errors/OOG/watchdog/Java exceptions. A discovery stop is **not terminal guest success, not exact q1 frontier acceptance, and never permission to resume failed state**. Preserve original precise scripts/evidence/default behavior.

Verify on generated fixtures: success unchanged; discovery+precise continuation from its last authenticated successful checkpoint reaches exactly the legacy precise outcome/counters/MR01/root. Invalid proofs/ABI/refusals fail closed. Later source/behavior/final gates remain precise.

## Work B: EVM-only selected-method dependency preflight

Authenticated view on selected original resource/Code can report near-term type owners for batching **explicit** resource bindings. Parse class metadata in EVM only; host receives ABI metadata, never host-parses original ZIP/class, runs guest Java, creates a host catalogue, or fabricates execution values. Diagnostic results are not execution authority. No eager Java class initialization is skipped or asserted. Full precise fresh replay on the final explicit batch remains the acceptance proof; package changes do not authorize reuse/migration of old checkpoints.

All original-input handling remains parent-owned. Workers use disjoint worktrees/generated fixtures/local dependencies. No JVM/EVM/runtime image/format/gas or COPY/authenticity changes are needed for these optimizations. At most2workers; no blind quantum expansion. Keep every failure and evidence file.
