# Continuous JVM-in-EVM program

## Latest authorization
LATEST user target: run **Minecraft Java server (mcserver) inside original,
unmodified EVM**. This supersedes the earlier general-JVM-not-Minecraft endpoint;
a general interpreter remains the implementation strategy, not a requirement to
finish all Java SE before targeting the server. Latest acceptance refinement:
FIRST milestone is seeing the real server's startup-complete indication after run;
client connectivity is NOT required, and is an optional later stretch goal. Treat
this as the selected version's actual ready/completion marker (typically a Done
line), not merely an early banner. Pin version/artifact and exact marker from
trusted reference evidence before freezing that workload. The parent controls
and delegates implementation continuously without routine stage confirmations.
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
Do NOT modify EVM opcodes, gas accounting, consensus, precompiles, or standard
execution/deployment limits to make Minecraft work. Audit the existing fork against
its pinned upstream before claiming original-EVM compatibility. Current local
runtime.Execute directly installs oversized runtime code: useful execution evidence,
NOT proof of standard CREATE/deployment compatibility. Solve deployment/code size
with ordinary EVM architecture rather than relaxing EIP-170 or other limits.
EVM has no direct OS sockets/files/clock: any proposed input/output transport,
virtual filesystem, scheduling/time source must be explicit. Host transport must
not execute Java/server/world logic. Do not imply a standalone listening server
without a defined, verified external-I/O boundary.

## What completion means / what it does NOT mean
The first concrete endpoint is an unchanged, version-pinned Minecraft Java server
executing its real startup path in original EVM through its genuine startup-complete
marker. A connectable/playable server is optional later work, NOT first acceptance.
Output must originate from guest execution reaching the actual logging path; host
may display decoded guest output, never synthesize the banner, patch out startup,
or substitute a toy program. Record executed artifact hashes, EVM output and enough
startup/state evidence to distinguish completion from an early startup banner.
Any virtual filesystem/network-bind/time/scheduling model needed for headless startup
must be explicit and reviewed; no-client scope is not permission to fake success or
run initialization on the host. Passing a subset test suite, counting
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
| M5c-d | IEEE arrays | accepted;2091 cases plus192 parent probes |
| M5d-a | implicit exceptions/handler/unwind foundation | accepted;2231 cases plus179 parent probes/8 init regressions/field boundary, prior192 retained |
| M5d-b+ | fresh user Throwable construction/APIs and remaining JVM/library features | queued; freeze separately |
| Stock-EVM architecture | ordinary deployment/modules/persistent continuation | proposal/prototype preflight active; not frozen |
| M6 | minimal class-library/bootstrap/native service inventory and implementation | queued; MC1.12.2 candidate inventory available |
| M7 | broader classfile versions, reflection/dynamic features, monitors/threads, conformance/workloads | queued |

This is a capability queue, not a promise all stages fit one session or a claim
that native/OS semantics have already been solved. Keep a concrete missing-feature
matrix in current docs and update the queue on measured evidence. Minecraft-specific
compatibility inventory is now authorized and should guide priorities after the
current atomic exception slice, without weakening general execution semantics.

## Current handoff
M5d-a accepted per JAVA_EVM_M5DA_PLAN.md:2231 JVM/EVM cases,179 independent parent
Java8/21/EVM probes,8 committed Java8 init regressions and field-arena boundary;
prior192 IEEE probes all retained.36 Python/1040smoke/1060fast/GoCLI/24bootstraps/
artifact/demos/AOT/vet green on final runtime154839bytes SHA256
`dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
Parent fixes4ceb539/fc9061c: already-erroneous default prerequisites no longer skip,
immutable exception layout/validation cache reaches field quota within250M. Old2091
manifest entries/outcomes/budgets unchanged. Still no new Throwable/APIs/String main,
standard deployment, or Minecraft startup claim.

MC static-only proposal2b2708d: recommend explicitly scoped1.12.2 candidate, optional
modern1.21.5 comparison. Genuine Done logger follows level preparation. Artifacts
only inspected, never executed; no EULA acceptance/listener. No differences in
core/vm,core/state,core/types,consensus,params vs pinned upstream95665d5.
Next two Sol/high NO Fast proposal-only workers basedfc9061c:
- stock-evm-architecture: JAVA_EVM_STOCK_EXECUTION_PROPOSAL.md + ignored bounded
  standard-deployment/resume prototypes; no privileged SetCode deployment claim.
- java-bootstrap-next: JAVA_EVM_M5DB_BOOTSTRAP_PROPOSAL.md + trusted Java oracle
  probes for construction/Throwable ABI/String/main dependencies.
Parent reviews/freezes next bounded implementation, no routine confirmation. These
proposals are NOT current implementation claims. Keep one production Solidity writer.
