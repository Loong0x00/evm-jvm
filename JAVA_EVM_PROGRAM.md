# Continuous JVM-in-EVM program

## Latest authorization
The user now explicitly asks the parent to control the workflow and delegate
implementation continuously toward a general Java virtual machine, **not
Minecraft**, without stopping for confirmation after every small accepted stage.
This supersedes earlier per-batch 'stop and wait' instructions. Stages and tests
remain bounded; acceptance of one stage triggers planning/dispatch of the next.
Default worker model remains `openai-codex/gpt-5.6-sol`, reasoning `high`.
Latest speed request supersedes earlier Fast instructions: NEW agents must NOT
request Codex Fast/priority. Keep the same Sol model and high reasoning. Persisted
Fast state was verified already disabled; do not pass --fast or re-enable it.
Existing running agents are not restarted or reconfigured by this request.
Recheck disabled preference before future dispatch; older frozen plans' Fast
wording records historical launches and does not override this latest directive.

## Execution invariant
Guest classfiles are supplied unchanged. Class parsing/linking, Java bytecode
execution, runtime values/heap/exception semantics happen inside ordinary EVM
bytecode. Host code may compile input/build runtime, package raw inputs, drive
EVM, and serialize/display outputs; it must not evaluate/translate Java or
resolve guest classes/methods on the actual execution path. Host JVMs are test
oracles only. No native-Java precompile or fallback on unsupported code.

## What completion means / what it does NOT mean
The aspiration is general Java execution. Passing a subset test suite, counting
implemented opcodes, or launching a toy Java main is not completion. The first
explicit compatibility target is Java 8 classfile/Java semantics; newer classfile
versions and platform libraries must then be identified/versioned. The project
currently has neither Java SE conformance nor arbitrary-Java capability.

Track separately:
1. JVM instructions, types, operand/local/category rules, stack frames and calls.
2. Class loading/linking/initialization, object/array heap, exceptions/unwinding,
   virtual/interface/dynamic dispatch, monitors and thread semantics.
3. Class-library bootstrap and runtime/native services, reflection and resources.
4. Execution limits: code/memory/heap/stack caps, finite gas, continuation/state.
5. Conformance evidence and named real pure-Java workloads.

'Arbitrary Java' includes programs with OS/JNI/network/file/thread dependencies
and unbounded resource requirements. Pure EVM execution does not automatically
supply those. Do not hide such gaps or claim unrestricted compatibility. Report
unsupported capabilities precisely; when a real platform boundary is reached,
propose explicit emulation/interfaces rather than secretly running Java on the
host. Ask the user only for material compatibility/safety/budget choices, not
routine permission to start the next verified increment.

## Workflow
- Parent owns stage contracts, disjoint write sets, integration and independent
  checks. Workers implement on separate Git branches/worktrees, return commits
  plus evidence, and never spawn more workers themselves.
- At most 3 concurrent Sol/high workers initially. Only one writes the monolithic
  Solidity runtime until a reviewed modular architecture allows real independence.
- Parallelize oracle fixtures and verification tooling against a frozen interface.
  Do not create fake parallelism with conflicting runtime edits.
- Merge fixtures/tooling and runtime in dependency order, test the combined
  revision, retain last-green commits. Failures are reproducers/tasks, not reasons
  to weaken oracle comparisons or silently exclude supported cases.
- Each stage uses finite gas and subprocess limits; no infinite agent restart
  loops. After acceptance, automatically launch the next dependency-ordered stage
  while context/session permits. Persist plans/status so continuation is explicit.
- No remote pushes, global config changes, production credentials or broad
  unrelated edits. Worktrees isolate changes, not permissions.
- Stop/report only on user interruption, an actual unresolved blocker, resource
  constraints, or a material boundary decision. Never claim work is still running
  unless agents/processes have actually been launched.

## Dependency-oriented progression
| Stage | Goal | State |
|---|---|---|
| V0 / M2a | oracle/replay gates + integer control flow | accepted at 3216753 |
| M2b | int constants/arithmetic/bitwise/conversions + explicit uncaught arithmetic exception outcome | accepted; JAVA_EVM_M2B_PLAN.md |
| M3a | same-class static calls, explicit Java frames/returns/recursion | accepted; JAVA_EVM_M3A_PLAN.md |
| M3b | raw multi-class input, direct EVM-side resolution/linking | accepted; JAVA_EVM_M3B_PLAN.md |
| M3c | integer static fields/state and ordinary-class initialization | accepted; JAVA_EVM_M3C_PLAN.md |
| M3d | class hierarchy/member resolution and superclass-init prerequisites | accepted; JAVA_EVM_M3D_PLAN.md |
| M4a | integer-array heap, typed references, array helpers/statics | active; JAVA_EVM_M4A_PLAN.md |
| M4b | ordinary object allocation, constructors, instance fields and direct invokespecial calls | accepted;713 cases plus46 independent probes |
| M4c | invokevirtual dispatch, casts/type tests | accepted;792 cases plus48 independent probes |
| M4d | reference arrays/covariance/ArrayStoreException | accepted;892 cases plus48 independent probes |
| M4e | multianewarray | accepted;960 cases plus48 independent probes |
| M4f-a | interface graph/abstract calls/type compatibility | accepted;1059 cases plus48 independent probes |
| M4f-b | defaults and required default-interface initialization | accepted;1163 cases plus48 independent probes |
| M4f-c | interface static members/initialization | accepted;1263 cases plus48 independent probes |
| M5a | Z/B/C/S int-like types/fields/arrays | accepted;1383 cases plus48 independent probes |
| M5b-a | scalar long/category-2 stack/locals/calls/fields | accepted;1493 cases plus48 independent probes |
| M5b-b | long arrays | accepted;1593 cases plus48 independent probes |
| M5c-a | switch/goto_w/wide variable-width control flow | accepted;1681 cases plus48 independent probes |
| M5c-b | scalar IEEE representation/conversions/comparisons + four EVM raw-bit APIs | accepted;1811 cases plus216 independent probes |
| M5c-c | software scalar IEEE arithmetic | accepted;1971 cases plus960 parent probes |
| M5c-d | IEEE arrays | frozen in `JAVA_EVM_M5CD_PLAN.md`; dispatch3 workers |
| M5d+ | exception/unwind and remaining JVM/library features | queued; freeze separately |
| M6 | minimal class-library/bootstrap/native service inventory and implementation | queued |
| M7 | broader classfile versions, reflection/dynamic features, monitors/threads, conformance/workloads | queued |

This is a capability queue, not a promise all stages fit one session or a claim
that native/OS semantics have already been solved. Keep a concrete missing-feature
matrix in current docs, update the queue on measured evidence, and avoid
Minecraft-specific work unless separately requested.

## Current handoff
M5c-c accepted:1971 JVM/EVM cases plus960 parent probes,36 Python,864 smoke/884fast,
Go/CLI/artifact/5bootstraps/demos/AOT/vet green. Obsolete arithmetic guards updated,
extra IEEE corner/seeded regressions and bounded gas proved; no runtime audit defect.
Runtime136564 bytes, local-runtime only/not full JVM. Prior1811 inputs/budgets same.
M5c-d frozen in JAVA_EVM_M5CD_PLAN.md; dispatch3 workers, then bounded exception/unwind
foundation. Four raw-bit native services ONLY, no host math/JRE fallback. NEW
agents Sol/high WITHOUT Fast; named java-fast is fixture tier. Automatic verified
progression, no routine confirmation.
