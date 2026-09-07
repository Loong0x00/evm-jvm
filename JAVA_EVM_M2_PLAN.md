# V0 + M2a: staged verification and integer control flow

## Authorization / scope
The user approved staged goals/tests and useful parallel work, explicitly not
starting with Minecraft. This batch stops at V0 + M2a acceptance. Three bounded
`openai-codex/gpt-5.6-sol` / high workers, separate branches/worktrees; parent
owns integration, shared documentation and Make targets. No unbounded agent loop.
M1 baseline: implementation 11e2e88, acceptance 3b427ee; planning base 70e90f0.

**Hard boundary:** unchanged raw classfiles are ABI-packed by host; all Java
class parsing, instruction decoding/validation and execution remain inside EVM.
The reference JVM is exclusively a verification oracle, not execution backend.

## Stage gates
- **V0:** a reproducible differential runner and fixtures verify existing M1;
  pass/fail summaries, ignored replay artifacts, finite subprocess/gas limits.
- **M2a:** constants (iconst, bipush, sipush), local loads/stores (including short
  forms), iadd/isub, iinc (signed 8-bit increment), integer unary and binary
  conditional branches, goto, ireturn. Demonstrate sum and iterative Fibonacci.
- Exactly these added opcodes: 0x02–0x08, 0x10, 0x11, 0x36, 0x3b–0x3e, 0x64,
  0x84, 0x99–0xa4, 0xa7; retain M1 0x15, 0x1a–0x1d, 0x60, 0xac.
- Java int32 wraparound and signed comparisons; branches are signed16 offsets
  relative to the opcode PC, may only target instruction starts. Check local
  initialization/range, stack bounds and truncated operands. Support valid early
  returns/branches with later code (M1's terminal-only ireturn restriction must
  change). Gas bounds nontermination; no fake Java success on OOG.
- ldc/ldc_w, multiplication/division/shifts, wide/goto_w, switch, calls, arrays,
  exceptions, objects, class libraries, Minecraft are deferred. No class
  initializer/monitor/native/exception semantic escape hatches.

## Frozen fixture / runner contract (v1)
Paths, relative to repository root:
- `jvmevm/testdata/differential/cases.json`: manifest.
- Java sources adjacent to manifest; filenames in `sources` are relative to that
  fixture directory. Keep guest classes in the default package, no guest main
  method or dependencies/native calls needed.
- `jvmevm/testdata/differential/OracleMain.java`: HOST TEST ONLY reflection wrapper.
- `tools/java_diff.py`: Python 3 standard-library differential runner.

Manifest shape (additional descriptive keys allowed, required keys fixed):
```json
{
  "schema_version": 1,
  "cases": [
    {
      "id": "m1-add-basic",
      "stage": "m1",
      "sources": ["Arithmetic.java"],
      "class": "Arithmetic",
      "method": "add",
      "args": [20, 22],
      "gas_limit": 2000000,
      "timeout_seconds": 10,
      "smoke": true,
      "expected_kind": "value"
    }
  ]
}
```
- IDs unique and stable; stages `m1` or `m2`; args are signed int32 JSON integers.
- All manifest entries in this batch are expected successful int results on a
  supported interpreter. No skipping/relabeling failures as accepted unsupported.
  Runtime negative tests (revert/OOG/malformed) live in Go tests this batch.
- Oracle invocation: `java -cp <compiled-fixture-dir> OracleMain <class> <method>
  [decimal int args...]`. Wrapper resolves an all-int parameter static method via
  reflection (test side only). Exactly one stdout line: `value=<signed int32>`
  or `exception=<fully-qualified-Java-exception-name>` for invoked guest exception.
  Harness/config errors go to stderr with nonzero exit. No hardcoded oracle
  answers; source guest method is actually run by JVM.
- javac command uses `--release 8 -d <compiled-fixture-dir>` with guest sources
  plus OracleMain.java. A fixture may contain several int methods; entry name
  remains unambiguous. Host fixture tools may use javap for inspection only.
- EVM invocation is existing `build/bin/jvmevm -class <raw .class> -method <name>
  -args=<comma-separated signed ints> -gas <gas_limit>`; existing key=value output
  and exit behavior are unchanged. Assert generic runtime_sha256 remains the
  same across all cases in a run; never preparse guest classfiles for EVM input.
- Runner args: `--stage m1|m2|all` (`m2` includes m1; `all` includes all),
  `--tier smoke|fast|full`, `--seed <int>`, `--case <exact-id>` for single-case
  replay, `--artifacts <directory>`, `--evm-bin <path>`. Defaults: stage m2,
  tier smoke, seed 56, artifacts build/java-diff, bin build/bin/jvmevm.
- smoke includes smoke-marked cases; fast includes smoke plus a deterministic
  sample of other selected-stage cases, recording IDs and seed; full executes all
  selected-stage cases. Explicit --case bypasses sampling but honors stage.
- Concise summaries; nonzero exit on ANY mismatch, unexpected exception, EVM
  revert/OOG, timeout, build/oracle/CLI/harness failure. Report categories separately.
  At least one selected case required; empty selection is not success.
- Artifacts record exact replay commands, manifest/source/class hashes, runtime
  hash, actual java/javac versions, commands/stdout/stderr, gas, per-case status,
  seed and git commit if available. Save a machine-readable JSON report (including
  case IDs) and concise text failure details. Don't promise full minimization yet.
- Bounded compile and per-case timeouts; build the CLI via external documented
  `go build` before invocation. No automatic unbounded retries or global installs.

## Worker ownership / tasks
| ID | Owner | Write set | Acceptance | State |
|---|---|---|---|---|
| V0-fixtures | fixtures worker | jvmevm/testdata/differential/** only | javac + JVM runs; inspect emitted opcode subset; manifest validation | assigned |
| M2-runtime | interpreter worker | jvmevm/runtime/JVMSubsetInterpreter.sol, corresponding .runtime.hex, jvmevm/jvmevm_test.go, jvmevm/controlflow_test.go (new) only | reproducible runtime build, M1 + new Go tests, sum/fib, malformed branch/stack/local, OOG | assigned |
| V0-runner | harness worker | tools/java_diff.py, tools/test_java_diff.py, tools/JAVA_DIFF.md only | own Python tests; mock protocol/error tests; current M1 real EVM smoke using temporary fixtures | assigned |

Workers MUST NOT modify Makefile, AGENTS.md, shared plans/docs or another write
set. Parent integrates those after cherry-picking scoped commits. No worker may
launch subagents, edit main worktree, push remotely or change global settings.
Workers read the plan from their worktree and write commits on their own branch.
Fixtures worker may add fixture-local README/generator if useful; generated cases
must be fixed/reproducible and counts stay modest (roughly 40–100 total), not a
large benchmark. Runner worker uses temporary self-contained fixtures for its
real M1 self-test; does not wait/poll or edit the fixtures worktree. Runtime worker
creates its own Go test fixtures inline and does not require the other workers.

## Integration / acceptance
1. Review each commit/write-set. Verify V0 fixtures+runner first against unchanged
   M1 using stage m1; preserve this intermediate evidence before runtime changes.
2. Integrate runtime commit; update Make targets and current docs/hashes/scope.
3. Focused runtime tests + artifact rebuild check + Python runner tests +
   differential smoke/full + prior AOT tests all pass on the combined revision.
4. Independent parent probes signed comparisons, wraparound, generic iload/store,
   branch boundary rejection, nonterminating-loop OOG and mismatch reporting.
5. Commit a clean local checkpoint; report measured results/limitations. Do not
   continue to M3 or Minecraft without another bounded task.

## Status
Planning and protocol frozen. Worktrees/worker dispatch follow in this batch.
