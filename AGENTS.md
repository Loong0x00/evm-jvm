# Java-inside-EVM agent guide

LATEST endpoint: unchanged Minecraft Java server executing in EVM.
LATEST priority/resource refinement: LOCAL artistic experiment first. User now
permits relaxed local gas budgets and work split across transactions/blocks.
See JAVA_EVM_PROGRAM.md: preserve opcode semantics/gas accounting/precompiles/
consensus and no host Java/server-logic fallback. Use explicit large finite local
budgets with watchdog/resource bounds; do not silently change any accepted stock
budget or claim infinite resources. Standard deployment is a SEPARATE target, no
longer a prerequisite for MC work. Leverage the richer monolith for local library/
startup dependencies rather than first migrating every feature into stock modules.
Currently dispatched S2b-L workers finish their frozen unchanged gates/write sets.
Current oversized local runtime.Execute is NOT standard deployment proof. Pin
server version and explicit I/O boundary before workload claims.
First MC milestone: genuine guest startup-complete marker (exact version/marker to
pin), NOT client connectivity. No fake/hardcoded banner or skipped initialization;
connectable server is an optional later goal. 1.12.2 is the proposed first target;
see JAVA_EVM_MC_STARTUP_PROPOSAL.md. No MC execution/EULA acceptance performed.

Current accepted stage: **M5d-a implicit exceptions/handlers/unwind**, recorded in
`JAVA_EVM_M5DA_PLAN.md`:2231 cases,179 parent cross-JVM/EVM probes plus8 initialization
regressions and a field-arena boundary case; prior192 IEEE-array probes retained.
Parent fixed already-failed default-interface prerequisites and bounded arena cost.
Runtime154839bytes;24 bootstraps. New Throwable/APIs remain deferred, four raw-bit
bindings only. Separate **S0 stock deployment/continuation is accepted** under
JAVA_EVM_STOCK_S0_PLAN.md:8 trusted fixtures x3 signed/replay budgets,80 parent
JVM probes,42 gas thresholds and reviewed CP512/Code256 boundary. Module11132bytes,
coordinator3724-byte template, ordinary CREATE and bounded resumes. Tiny S0 is NOT
modularized M5d-a and counts stay separate. **S1 is accepted** per
JAVA_EVM_STOCK_S1_PLAN.md: all82 unchanged M1/M2 rows, EVM-derived reusable metadata,
named entries/int args, branch/loop-safe schema2 and finite step-limit outcome.
Parser15271/step8408/coordinator6328-byte templates;48parent loop+52threshold probes,
reviewed aggregate boundary fixed without raising8M. Preserve S0/S1/monolith/old
fixtures. **S2a accepted** per JAVA_EVM_STOCK_S2A_PLAN.md:201 M1/M2/M2b rows,
199values+2Arithmetic faults, one frame;312parent probes andindependentreview pass.
Parser15659/step9470/coordinator7694-byte templates, no runtime defect demonstrated.
Next **S2b-L registration/link slice is frozen** in JAVA_EVM_STOCK_S2BL_PLAN.md:
new stock/s2b analyzer/linker/schema4 metadata and EVM S2a reparse adapter. NO frame
store/resume/268-row execution claim in L. Fix prototype worklist and method-order
risks, preserve8M registration. Frame5-word/4-touched design remains proposal-only.
M5d-b0 retained; still no full-profile deployment, libraries or MC startup claim.
New workers keep Sol/high but MUST NOT request Fast/priority (latest user
instruction overrides historical stage plans). Do not pass --fast or re-enable
the disabled preference. Existing running workers need not be restarted.
Runtime is over EIP170 deployment size: local runtime.Execute only, not mainnet
CREATE compatibility; no consensus-core or host-Java fallback changes.
Continuous parent orchestration is authorized by `JAVA_EVM_PROGRAM.md`,
superseding earlier stop-after-each-batch instructions. Worker scope comes from
the current frozen batch plan; wider stages are not conformance claims.

## Git / ownership

Canonical integration repository: `/home/user/evm-jvm/geth`, branch
`java-on-evm`. `upstream` is geth v1.16.9 at
`95665d5703e1023995a0ff93e4ce9eb77e8a59bd`. First confirm
`git rev-parse --show-toplevel`; the home directory has an unrelated Git repo.
Use `git status --short --branch`, stage explicit paths, make small verified
local commits, do not push or change global configuration.

The completed `m2-fixtures`, `m2-runtime`, `m2-harness` branches/worktrees retain
worker delivery history. For new delegated work, use the explicitly assigned
worktree based on the latest integration revision, not an old worker tree.
Worktrees separate edits, not security permissions. Respect frozen task write
sets; only one worker edits the monolithic Solidity dispatcher at a time.
Disjoint Go files still share a package namespace: give new test helpers a
stage/role prefix (e.g. runtimeM5da* vs verifyM5da*) to avoid integration collisions.
The differential oracle executes Java on the host: use only trusted generated
fixtures here; untrusted external programs/corpora require isolation first.

## Relevant map / execution boundary

- Generic EVM interpreter source/artifact/build: `jvmevm/runtime/`
- Raw-byte ABI runner and focused/negative tests: `jvmevm/`
- CLI: `cmd/jvmevm/`
- Staged Java inputs + HOST-TEST-ONLY oracle: `jvmevm/testdata/differential/`
- Differential runner/error tests: `tools/java_diff.py`, `tools/test_java_diff.py`
- Quickstart/limits: `JAVA_EVM.md`; runner details: `tools/JAVA_DIFF.md`

At runtime, host only ABI-packs unchanged raw classfiles, method name and int
arguments. EVM performs class/method/Code/constant-pool resolution, instruction
predecode, int32 arithmetic/bitwise/conversion/locals, signed conditions, loops
and returns. `RunClasses`/repeatable CLI `-class` plus explicit `-entry-class`
accept unchanged raw bundles (max64); EVM resolves declared names/direct owners,
keeps per-class CP/caches and checks the supported access profile. No host
classpath fallback. Calls use independent Java frames (128 cap). ArithmeticException and
StackOverflowError outcomes are determined inside EVM; host only decodes exact
recognized payloads (never any arbitrary revert). Integer statics and lazy/reentrant
<clinit> execute in EVM; initializer ArithmeticException wraps as known EIIE kind3,
but Error/OOG are not mislabeled. Statics reset per VM invocation. No host Java parsing/extraction/translation/evaluation,
native Java precompile, or class-specific runtime generation. Host javac and
JVM reflection/oracle runs belong ONLY to building/testing guest inputs.

M0 host-AOT remains in `javaevm/` and `cmd/javaevm/`, only under `java-aot-*`
commands; never present it as the in-EVM interpreter. Keep consensus core intact.

## Commands / gates

Go 1.24+, JDK with `javac --release 8`, make; Python 3 for differential tests;
Node/npm for pinned artifact build/check. Run from your assigned repo root:

```sh
make java-demo       # EVM arithmetic, bundle call and int-array examples
make java-smoke      # 1040 fixed oracle comparisons
make java-fast       # 1060 cases; JAVA_DIFF_SEED=57 changes repeatable sample
make java-full       # 2231 cases through M5d-a
make java-test       # artifact + focused Go + 36 runner tests + full differential
make java-aot-test   # separate old-path regression
```

`make java-build` creates ignored `build/bin/jvmevm`. `make java-diff-m1`
checks M1 cases on the current runtime; `make java-harness-test` includes a real
JVM/EVM smoke (not just mocks). Runtime rebuild/check:
`make java-runtime-build` / `make java-runtime-check`. After interpreter edits,
review generated artifact and update expected runtime hash only from that
pinned reproducible build. Do not weaken expected outcomes to get green tests.

Single-case replay after building: `python3 tools/java_diff.py --case
m2-fibonacci-20` (one shell line). Reports under ignored `build/java-diff*/`
include exact replay commands, sources/runtime hashes, JDK versions and logs.
Each run preserves its own classes/report. Replay depends on the current
sources/tools/CLI; it is not a frozen snapshot. Keep output concise and inspect
saved failures rather than dumping all logs into agent context.

## Continuous orchestration / worker boundary

The user authorized the parent to keep planning/delegating/integrating stages
toward a general JVM, without routine re-confirmation. Parent follows
`JAVA_EVM_PROGRAM.md`; each worker implements ONLY its frozen stage/write set,
commits and returns for review (no self-spawning or scope expansion). After a
verified milestone the parent starts the next dependency-ordered batch.
Stop/escalate genuine blockers, budget/safety constraints or platform-boundary
decisions—not merely because a small stage ended. Do not claim a full JVM or
arbitrary Java support from subset counts. Preserve finite timeouts/gas and
separate EVM/unsupported/harness failures from structured Java outcomes.
