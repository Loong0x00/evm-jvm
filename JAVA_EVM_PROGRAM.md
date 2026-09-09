# Continuous JVM-in-EVM program

## Latest authorization
SELECTED MC VERSION (explicit user choice): Minecraft Java server **1.12.2**,
unchanged official vanilla server, Java8 compatibility target. It is no longer
merely a candidate. Pinned official server size30,222,121bytes,
SHA1 886945bfb2b978778c3a0288fd7fab09d315b25f,
SHA256 fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e;
official URL and static ready-path evidence in JAVA_EVM_MC_STARTUP_PROPOSAL.md.
Target actual rendered message body:
`Done (<digits>.<exactly three digits>s)! For help, type "help" or "?"`,
from guest nz.j() after world preparation, not an early banner. Java8/21 remain
TEST oracle versions, not a claim of complete Java21/MC compatibility. This pins
version/artifact intent only: no server execution/EULA acceptance performed and no
full platform/config/workload acceptance inferred. Keep historical proposals intact.

LATEST platform-scope refinement: user explicitly prioritizes the artistic
VM-inside-VM-running-a-game result, not complete Java/platform conformance.
Implement the EVM-backed virtual filesystem and only the Java/runtime/scheduling
subset actually needed by the unchanged selected MC startup path. Full Java SE,
OS-thread equivalence, parallel execution and a general-purpose scheduler are NOT
prerequisites. A deterministic single-EVM cooperative guest scheduler is a candidate,
not an implemented capability: required guest tasks must really execute, and used
start/join/wait/notify/lock/sleep behavior must be modeled sufficiently to avoid
fake progress/deadlock or omitted startup work. No blanket Thread.start/locking/I/O
no-ops or host-executed background/world logic to manufacture readiness. Freeze the
actual subset from dependency evidence; report unsupported paths explicitly.
First success remains genuine server startup-complete, not a graphical client or
full playability. Continue bounded work without routine confirmation.

LATEST resource/priority refinement (after S2b-L freeze): user explicitly permits
relaxed LOCAL gas budgets (colloquially "unlimited gas") for an artistic experiment,
and splitting work across blocks/transactions. Prioritize genuine LOCAL MC startup;
standard-chain deployment/small stock budgets are NO LONGER its prerequisite.
Use a separately labeled experimental profile with explicit large FINITE gas,
wall-time/memory bounds and recorded configuration. Preserve EVM instruction
semantics/gas accounting; do not disable charging or patch consensus/core merely
to avoid choosing an adequate local budget. No actual infinite-resource guarantee.
The existing oversized runtime.Execute harness is usable local execution evidence,
not standard CREATE proof. Standard S0/S1/S2a and frozen S2b-L gates remain unchanged
and separate; never silently raise historical budgets or relabel local evidence.
Let currently dispatched bounded S2b-L work finish, but do not require migrating
all monolith semantics to stock deployment before working on MC library/platform
prerequisites. Prefer leveraging the richer monolith for the local startup path.
Cross-transaction continuation still requires an explicit EVM-owned checkpoint of
Java state; host may transport opaque data, not compute Java or recover a reverted
OOG transaction as if its intermediate state had committed. Capability/EULA/I/O
and genuine-ready-marker requirements below are unchanged.

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
Do NOT modify EVM opcodes, gas accounting, consensus or precompiles to make
Minecraft work. Local experimental gas limits may now be explicitly increased,
per latest authorization above; use distinct configuration/results, not silent
changes to accepted stock profiles. Audit the existing fork against its pinned
upstream before compatibility claims. Current local runtime.Execute directly
installs oversized runtime code: useful LOCAL execution evidence, NOT proof of
standard CREATE/deployment compatibility. The standard-deployment track continues
to respect EIP-170 and all other original limits; it is not a prerequisite for the
newly prioritized local MC experiment.
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
| Stock-EVM S0 | ordinary deployment/signed replay/bounded persistent integer stepping | accepted JAVA_EVM_STOCK_S0_PLAN.md; separate subset, NOT M5da migration |
| Stock-EVM S1 | actual legacy integer workloads/arguments/control flow and reusable parsing/state | accepted JAVA_EVM_STOCK_S1_PLAN.md;82rows/39roots, schema2 |
| Stock-EVM S2a | integer completion and terminal arithmetic faults | accepted JAVA_EVM_STOCK_S2A_PLAN.md;201rows/60roots, one frame |
| Stock-EVM S2b-L | schema4 callmetadata and S2a reparse adapter, registration ONLY | accepted JAVA_EVM_STOCK_S2BL_REVIEW.md;14classes/51callrecords, NO268stock execution |
| Local MC-LB0 | richer-monolith MUTF8/String literals/intern identity | ACCEPTED;64newcases/198parentEVM/17reviewprobes/alllegacygates PASS; JAVA_EVM_MC_LB0_REVIEW.md |
| Local MC-LC0 | EVM-owned single-stack checkpoints/start/resume/CAS/durable restart | ACCEPTED; actual15/36/10 q1/q7/internal1 chains, new-process reopen and1MiBboundary; JAVA_EVM_MC_LC0_REVIEW.md |
| Local platform later | VFS/minimal scheduler/main/JAR and further libraries | VFS proposal prepared; bridge/String/Throwable dependencies remain unfrozen; no MC execution |
| M6 | minimal class-library/bootstrap/native service inventory and implementation | local MC dependency priority; selected1.12.2 static inventory available |
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
Stock S0 accepted: JAVA_EVM_STOCK_S0_PLAN.md. Runtime/harness/verifier integrated,
parent numeric-zero fix1f45125, real gasguard bugfix861c8c2, independentreviewdb1d169
and CP-reuse fixc62cec4. New stock gates green with8JVMfixtures x3 signed/replay
budgets,80 parentJava8/21probes,42gasthresholds and successful CP512/Code256 review
boundary. Module11132bytes SHA3f36c84abdb4701faa36fa5ce1490ce179fc5c395a17f7e6fe45de861acdbfd4,
coordinator3724-byte template. Canonical6positiveTx/3resumes/4234189gas->12.
Old2231suite/GoCLI/36Python/bootstrap/artifact/smoke/fast/demos/AOT/vet remain green;
no original-EVM/core/params/consensus modification. This is NOT full M5da deployment
or Minecraft execution. Keep S0/legacy case counts separate.

Stock S1 ACCEPTED per JAVA_EVM_STOCK_S1_PLAN.md: exact82rows/39roots/5classes/2213
instructions via signed64/128runs, JVM8/21 andmonolith; EVM-derived immutablemetadata
reused, no hostoffsets. Cataloguef98038bd7cb12d165c0b22dd7feca869803efce86a8194f4a3ddb1973f84764b.
Parser15271/step8408/coordinator6328-byte templates fitstandarddeployment. All old2231
and S0 gates retainedgreen. Sharedsetup12tx/11790544gas; sum100128step7resumes,
value5050,isolated10324488gas; fib30value832040. FiniteSTEP_LIMIT notJavaoutcome.
Parent+review fixedvalidaggregate budget via MCOPY (8449776->6923070,8Munchanged)
andinvalidtestmethods,48eight-local loopprobes+52gasthresholds green. Details/logs/
hashes in plan/review. No originalEVM/core/gas/limit change or MC execution.

Stock S2a ACCEPTED per JAVA_EVM_STOCK_S2A_PLAN.md:201orderedrows/60roots/11classes,
199values+2Arithmetic faults/2642attempts; actualJVM8/21/signedStock/directreplay.
Catalogue1273f2302d2898a2eb0ff391f9cf7ff2c9b64749fd0821df891b921499aa8d0d.
Parser15659/step9470/coordinator7694-byte templates, actualordinarydeployment;
312parent arithmetic/prefix/capprobes andindependentreview085886e pass. Onlyparent
fix was verifiercatalogueformat (faultresult0 +lifecycle3 notJSONnull), no runtime
defect/artifactchange. Old2231/S0/S1/allgates green; no core/EVM/limit/host changes.

Next two Sol/high NOFast proposalworkers based3098849:
- stock-s2b-frame-preflight: compactint frame storage/owner/deltas/root links,
  bounded2/4 dirty-frame alternatives, actualreserve/gas measurements.
- stock-s2b-parser-preflight: actualEVM parser/analyzer/callmetadata/private/void/
  sixarg/overload/CPMethodref prototype, boundednewversion andregistrationgas.
S2b NOT frozen. Old16-childwrites~3.8M and192coldwords>4.2M cannot be guaranteedby
800kreserve; measure/refactor, never modify stocklimits. Reuse old268caseoracle
withoutclaiming S2a alreadyexecutescalls/frames. M5d-b0 remainsqueued. No MCstartup/
EULA execution. One productionSoliditywriter, continuousauthority/no routineconfirmation.
