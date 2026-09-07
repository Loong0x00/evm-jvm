# M3b: raw class bundles and direct cross-class static linking

Continuous authority: `JAVA_EVM_PROGRAM.md`. Last-green M3a checkpoint:
**699e367**, 268 oracle cases, 21 harness tests. Parent integrates this batch and
continues to M3c static state/initialization. No Minecraft tasks.

## Scope / hard boundary
Accept a collection of unchanged raw classfiles; identify their declared binary
names and resolve direct static calls entirely INSIDE the EVM. Retain integer
values/frames/outcomes. No new guest opcodes in M3b: class-aware invokestatic is
the capability increment. No host class parsing, dependency scanning/prelinking,
method extraction/evaluation, native/classpath fallback or class-specific EVM
code generation. Host names/path lists are explicit input metadata, not guesses
from classfile contents. Same generic runtime artifact handles old and bundle APIs.

Defer fields/getstatic/putstatic, <clinit> execution, superclass method lookup,
interfaces, object/reference values, instance calls, libraries and new types/forms
to later stages. Bundle execution is direct-owner resolution between ordinary
classes with Object as superclass (Object itself may have no superclass). No
claim of a full JVM loader/linker or complete access-control verification.

## Frozen EVM / Go / CLI API
Keep existing Solidity entry:
`interpret(bytes rawClass, string entry, int32[] args) returns (int32)`.
Keep existing Go `Run` and single-file CLI behavior, including legacy
CallError2 for external-owner references. Preserve prior268 tests and outcomes.

Add Solidity entry:
`interpretClasses(bytes[] rawClasses, string entryClass, string entry, int32[] args) returns (int32)`.
`entryClass` is an explicit JVM **internal name**, e.g. `pkg/Root` (not a filename).
All names are validated/resolved from guest CP/Class metadata inside EVM, not
from host filenames or supplied order. Empty/duplicate/missing bundles are EVM
validation errors. Maximum 64 raw classes per bundle. Each invocation starts with
fresh in-memory execution state; no static/heap persistence in this stage.

Add Go API:
`RunClasses(classfiles [][]byte, entryClass, method string, args []int32, gasLimit uint64) (Result, error)`.
It ONLY ABI-packs unchanged bytes + supplied metadata and calls runtime.Execute,
then decodes the same int/known-Java-exception output. No new JavaException kinds.
ABI loading may include both entry points; shared host execution/output helper is
fine if it never inspects guest data. Existing `Run` remains backward compatible.

CLI:
- `-class` becomes a repeatable raw-file path flag (preserve old one occurrence).
- New `-entry-class` passes a JVM internal name unchanged.
- One `-class` and no `-entry-class`: legacy single-class Run path.
- Multiple `-class`: require explicit `-entry-class` (missing CLI metadata is a
  usage error, not permission to read class headers on host).
- One or more `-class` plus explicit `-entry-class`: RunClasses, even with one
  file, for testing bundle selection/missing-dependency behavior.
- Same success/error output keys, hashes, gas and exit conventions as M3a.
  File extension/name does not determine its declared class identity.

## Resolution / runtime rules
- Parse per-class CP/method metadata in EVM, use declared internal class names.
  Reject duplicate class declarations regardless of filenames/raw-byte equality.
  Class order is arbitrary; cross-class call cycles/recursion are legal.
- Frames carry class identity plus method identity. CP constants, Methodref caches,
  selected-method metadata and instruction boundaries must be scoped per class.
  Resolve exact owner-name + method-name + descriptor; never mix equal CP indices
  or equal method signatures belonging to different classes.
- Preserve same-class private/overloaded helper behavior. Across different classes,
  permit public classes/methods; permit nonprivate package/protected methods in
  the same package; reject external private access and nonpublic classes outside
  their package. Public methods in different packages must work. Package identity
  comes from internal names inside EVM. Subclass/protected cross-package rules
  requiring hierarchy are deferred with unsupported-superclass profile.
- Do not eagerly reject unused methods with unsupported bytecode/descriptors.
  Supplied unused classes may be parsed without being entered. A class with
  <clinit>, interface flag or unsupported superclass is rejected when entered,
  not silently initialized/ignored; do not execute any initializers yet.
- java/lang/Object need not be supplied merely as an ordinary class's implicit
  superclass; no Object methods are provided or evaluated by host. An explicit
  call to an absent owner still fails. No superclass method search in this stage.
- Legacy single-class mode keeps original error behavior/profile. Sharing a
  machine core is preferred over copying the whole dispatcher. Preserve gas
  discipline and current metadata/resource caps (CP4096, Code65535, stack/locals
  1024, active frames128). Method caches should remain invocation-local.
- Do not edit old268 fixture budgets/outcomes to hide regressions. Aim to keep
  them green unchanged; report measured performance blockers to parent if a
  substantive architecture change cannot meet a historical gas budget.

## Frozen error protocol
New Solidity `error LinkError(uint256 code, uint256 detail);` in bundle mode:
1. zero or >64 raw classes; detail = supplied count;
2. duplicate declared class; detail = index of the later duplicate input;
3. requested entry class absent; detail = 0;
4. referenced owner absent; detail = invokestatic offset in the caller;
5. entered class has unsupported class semantics (interface, <clinit>, or
   non-Object superclass except Object's zero superclass); detail = class index
   in input bundle.

Malformed raw files retain ClassError. Existing MethodError/root and CallError
payloads otherwise retain their meanings: CallError1 malformed ref/tag structure,
3 missing exact method signature, 4 invalid callee or illegal cross-class access,
5 entered-method return mismatch. CallError2 remains the legacy single-class
external-owner rejection. Underflow/truncation remain BytecodeError. All LinkError
failures remain EVM errors, NOT invented Java linkage exceptions. Known uncaught
ArithmeticException and StackOverflowError propagate across classes unchanged;
OOG remains a distinct EVM failure. Error precedence on multiply malformed input
is not a full JVM verification contract.

## Frozen manifest / runner extension
- Add cumulative stage `m3b`, default m3b; `all` includes every stage. Schema1
  remains additive. Preserve existing268 entries exactly.
- `class` may now be a dotted binary Java name (ASCII identifier segments with
  optional `$`, e.g. `bundle.Root`, `bundle.Outer$Inner`). Default-package old
  names remain valid. Method remains a simple identifier. OracleMain receives
  this dotted class name. Root .class path is metadata-derived by replacing dots
  with '/' (no classfile parsing). Unicode/MUTF8 completeness is not this stage.
- Optional `class_files` is a nonempty list of distinct relative `.class` paths
  under this run's javac output, e.g. `["bundle/Root.class","bundle/Helper.class"]`.
  Lexical traversal/absolute paths and resolved symlink escape are errors. Check
  existence/confinement after compilation. Do not auto-enumerate dependencies or
  automatically add files omitted by manifest.
- Without class_files, invoke legacy CLI exactly as before (one raw root file).
  With class_files, pass repeated `-class` in listed order plus
  `-entry-class <manifest class with dots replaced by slash>`; this conversion is
  explicit metadata serialization, not guest resolution. A bundle may omit the
  entry owner to test EVM rejection outside positive oracle cases.
- Existing `sources` lists confined relative Java sources; compile supplied
  sources + OracleMain via javac --release8. Package source subdirectories work.
- Preserve root class_sha256 compatibility and additionally record each supplied
  class path/hash, exact ordered CLI argv/bundle paths/internal entry name in
  report. Same runtime hash across legacy and bundled values/exceptions.
- Expected-kind/outcome/replay/timeouts semantics unchanged. Validation tests
  should make omission/path mistakes fail clearly rather than silently fallback
  to host classpath. Oracle executes trusted fixtures on host; not a sandbox for
  arbitrary untrusted Java. Keep external/untrusted corpora out of this batch.

## Parallel ownership
Only assigned worktree/branch; no main/peer edits, subagents, remote pushes,
global config changes or arbitrary external source execution. Parent owns shared
plans/docs/AGENTS/Makefile; workers commit scoped code + evidence and return.

| Worker | Allowed write set | Task |
|---|---|---|
| M3b-runtime | Solidity source/runtime hex; jvmevm/jvmevm.go; cmd/jvmevm/main.go + main_test.go; jvmevm/jvmevm_test.go (hash only); NEW jvmevm/bundles_test.go | bundle loader/linker/core frame class identity, raw Go/CLI adapter, inline positive/negative bundle tests, old regression |
| M3b-fixtures | jvmevm/testdata/differential/** only | append ~50–80 m3b raw-bundle cases/sources, packages/order/CP+cache isolation, cross-recursion/exception outcomes, actual JVM reference and javap |
| M3b-verifier | tools/java_diff.py; tools/test_java_diff.py; tools/JAVA_DIFF.md; NEW jvmevm/bundles_validation_test.go | ordered raw bundle protocol/path safety; independent exact loader/access errors, API boundary and filename/order independence |

Runtime/fixtures workers use their own inline tests/reference sources; do not
wait/poll peers. Verifier's new Go tests may fail to compile on the baseline
because RunClasses does not exist yet: report that test-first dependency clearly,
do not add a fake API/stub, weaken assertions or skip final tests. Production
`go build ./jvmevm ./cmd/jvmevm` and Python old/mock/real legacy checks can pass
independently. Parent integrates runtime before verifier. No production edits
outside owned paths. For test-only multi-source Java compilation, create temp
directories and run javac on trusted inline sources.

## Acceptance / continuation
- Prior268 remain green unchanged, plus new cross-class/reference/call-state cases.
- Same runtime executes alternate bundle order, correctly declared classes under
  misleading host filenames, per-class same-named helpers and CP indices, private
  same-class calls and legitimate package/public cross-class calls.
- Exact LinkError1–5 and CallError4 access checks, missing signature/owner,
  duplicate classes and malformed raw input; no host preprocessing/fallback.
- Reproducible artifact, focused Go incl independently authored validation,
  Python protocol/path tests with real JVM/EVM smoke, full oracle suite, AOT/vet.
- Parent review/probes, last-green commit and capability update, then automatically
  proceed to **M3c static fields and class initialization** (new bounded contract).

## Status
M3b contract frozen; next action is worker dispatch. No M3b implementation claim.
