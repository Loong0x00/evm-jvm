# Toward broader Java execution inside EVM

Status: **V0 + M2a is now accepted**, tracked in `JAVA_EVM_M2_PLAN.md`.
Three bounded workers delivered fixtures/runtime/runner, followed by independent
integration tests. Later phases below remain proposals; this document does not
claim full Java support or authorize an unbounded agent run.

## Inspiration and source attribution

Nicholas Carlini, Anthropic, **Building a C compiler with a team of parallel
Claudes**, February 5, 2026:
https://www.anthropic.com/engineering/building-c-compiler

The article reports 16 agents, almost 2,000 sessions, approximately two weeks
and $20,000, producing a roughly 100,000-line Rust C compiler. More important
than those scale figures are its verification harness, GCC oracle, independent
failure isolation, Git-backed task claims, fresh-session progress documents,
and concise/reproducible fast tests. The reported compiler still had substantive
correctness, integration and performance limitations.

The article's setup used separate clones and a shared bare repository, not Git
worktrees, and an outer restart loop rather than a central orchestration agent.
The coordinator/worktree/merge-gate design below is **our proposed adaptation**,
not a claim about their exact implementation. Test success is bounded evidence,
not proof of complete Java conformance.

## Define "full Java" before claiming it

1. **JVM execution semantics:** instructions, stack frames, values, heap, arrays,
   object/class model, linking, initialization, exceptions, dispatch and monitors.
2. **Java platform:** Java class libraries plus required native/runtime services.
3. **Applications:** Minecraft version-specific JDK, library, native and OS needs.

Completing an opcode checklist does not complete layers 1–3. We propose a first
bounded platform target of Java 8 classfiles / deterministic single-threaded
pure-Java programs, then explicitly version and broaden that target. This is
not a promise of full Java SE 8 conformance; threading/native services are
separate workstreams. Minecraft's exact version must be selected before its
JDK/class-library requirements become acceptance criteria.

The invariant stays: raw classfiles enter an ordinary EVM interpreter. Parsing,
linking, bytecode execution and Java semantics stay in EVM. The host may compile
fixtures/build interpreter artifacts, package raw inputs, drive EVM and display
outputs. It must not compute Java results or parse/decode guest classes on the
execution path. Reference JVM execution is permitted only in the test oracle.

## Milestones with observable exits

| Stage | Work | Exit evidence |
|---|---|---|
| V0 | Reproducible JVM differential harness, fixtures, task/result formats | Existing M1 passes the new harness; mismatch/error artifacts replay with one command |
| M2 | int constants, local stores, arithmetic, comparisons, branches, iinc | Actual javac classes for loop summation, iterative Fibonacci and signed/overflow edge cases agree with reference JVM |
| M3 | method frames, static calls, return, raw multi-class input/linking | Recursive factorial and cross-class calls; all resolution stays in EVM |
| M4 | remaining primitive values, arrays, exceptions, switch/wide forms | Primitive semantic and array-bounds suites; exception type/control-flow comparison, not just generic EVM revert |
| M5 | heap/objects/fields, constructors, virtual/interface calls, class init | Small object graphs, inheritance/interfaces and initialization-order regressions |
| M6 | selected class-library bootstrap and newer classfile/runtime features | A named pure-Java application and a published supported-library/version matrix |
| M7 | version-pinned Minecraft dependency inventory and headless slice | Small deterministic game-logic workload before any service startup claim |

Stages may be revised after measurements. Floats require JVM-compatible IEEE
semantics, not host/EVM integer approximations; invokedynamic, reflection,
class loading and native services each require explicit designs. EVM code-size,
memory, gas and execution-continuation limits may require modular EVM contracts
or explicitly documented local-fork changes—not native Java escape hatches.
No live networking/filesystem/thread emulation or full game commitment yet.

## Verification-first workflow

### Common case protocol (design before parallel coding)

Each manifest entry records: stable case ID, Java source, entry class/method and
descriptor, typed arguments, required features, reference-JDK identity, javac
flags, resource limits and seed. Java source/class hashes and interpreter source,
artifact/compiler hashes accompany results. The execution runner accepts raw
class bytes; any fixture inspection/disassembly belongs only to verification.

Results distinguish Java value/exception, unsupported capability, invalid input,
EVM revert, out-of-gas, reference timeout and harness failure. Never equate OOG or
timeout with successful Java exception behavior. Later float comparison follows
JVM requirements, including signed zero/infinities and allowed NaN behavior,
not a blanket numeric tolerance. Initially compare exact int32 results.

Use generated Java wrappers with reference OpenJDK as oracle; pin/report the
actual JDK build as well as `--release 8`. Compare result values, and later Java
exception types/observable state. Keep wall time/gas out of semantic equality.
Add hand-written edge cases and seeded generation; save minimized reproducers
for mismatches. A shared mistake in a generator/oracle remains possible, so
cross-check selected cases against JVMS rather than trusting counts alone.

### Test tiers and evidence

- `smoke`: fixed edge cases, every change, concise output.
- `fast`: repeatable sample plus changed-feature cases; record seed and IDs.
- `full`: every accepted supported case and all regressions; merge gate.
- Unsupported/planned cases are reported separately, not counted as successes.
- Run with finite wall-time/gas limits. Summarize PASS/FAIL/UNSUPPORTED/OOG counts
  on stdout; write full logs and exact replay commands under ignored artifacts.
- Preserve same generic interpreter hash across input classes/argument values.
- Rebuild source/artifact before acceptance and keep M0 tests as separate checks.
- Full conformance claims need an appropriate full suite and independent review;
  passing generated cases or a demo cannot establish them.

### Bounded agent organization (proposal, not running)

Start with at most **3 workers** using `gpt-5.6-sol` / `high`, not 16 agents or an
infinite restart loop. First freeze the case/result interface, then split:

1. **Oracle/fixtures worker:** reference JVM wrapper, manifests, edge cases and
   deterministic generation. No interpreter edits.
2. **Interpreter worker:** one M2 opcode/control-flow slice and runtime artifact
   generation. Sole owner of the Solidity interpreter until modular boundaries
   are genuinely useful; no competing edits to its monolithic dispatcher.
3. **Harness/integration worker:** bounded process runner, summaries, replay and
   regression gates. No independent changes to expected semantic outputs.

The parent coordinates and independently reviews/merges. Use one branch/worktree
per worker (proposed alternative to the article's clones). Worktrees isolate Git
edits, **not process permissions or credentials**; compiler/build tests need
separate resource controls and should not receive production secrets. No remote
pushes or global tool/config changes. Keep everything local by default.

Task records include owner, base revision, write-set, dependencies, acceptance
commands and state (`ready/claimed/blocked/review/done`). Claim via the coordinator
before implementation; release only after review. If moving to autonomous
claiming, add atomic claims/leases/heartbeat recovery rather than stale lockfiles.
Workers return a commit and concise evidence; progress documents allow restart
without a giant accumulated conversation. Never continuously poll/waste loops
while another worker owns a prerequisite.

Merge one candidate at a time onto an integration branch. Test the **combined
revision**, not just isolated branches. Do not weaken tests, change oracle
outputs, or silently reclassify failing supported cases to improve pass counts.
Interpreter artifact/hash updates must be explainable by reviewed source and
pinned compiler settings. Retain last-green commits and minimize/reproduce a
failure before assigning multiple agents the same bug.

### Stop and budget rules

- First batch stops after V0 + a specifically agreed M2 slice and a reviewed
  demo/test commit; do not autonomously continue through the whole roadmap.
- Cap concurrency and individual command duration/gas. Exact agent time/token
  or monetary limits must be agreed before an unattended long run; the historical
  article cost is not an estimate for this project.
- Stop/report blockers on ambiguous semantics, native/host-boundary changes,
  repeated non-progress, verifier disagreement or resource-budget exhaustion.
- Further phases require explicit bounded scopes. No claim that current tools
  already provide the proposed task scheduler, worktrees or replay harness.

## Current checkpoint / next decision

V0 and M2a closed loops are complete: real EVM sum/Fibonacci, 82 fixed JVM
comparisons, bounded gas/error tests and replay tooling. See `JAVA_EVM_M2_PLAN.md`
for accepted scope and evidence. M2's broader integer instruction set is not
complete (ldc, negation, multiplication/division, shifts/bitwise are still absent).

Stop here for this batch. A next small task can cover another integer opcode
slice with dedicated semantic/error tests, then method frames/calls. Do not jump
from control-flow demos to objects, Java SE completeness or Minecraft.
