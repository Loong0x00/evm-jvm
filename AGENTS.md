# Java-inside-EVM agent guide

Current accepted stage: **M3c integer statics/class initialization**, recorded in
`JAVA_EVM_M3C_PLAN.md`. Next: **M3d superclass/member resolution and super-init**,
with draft contract `JAVA_EVM_M3D_PLAN.md`. Heap/references and handlers follow.
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
make java-demo       # actual EVM add, sum(100), fibonacci(20)
make java-smoke      # 128 fixed oracle comparisons
make java-fast       # 148 cases; JAVA_DIFF_SEED=57 changes repeatable sample
make java-full       # 426 cases (341 through M3b + 85 M3c)
make java-test       # artifact + focused Go + 26 runner tests + full differential
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
