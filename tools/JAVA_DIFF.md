# Java/EVM differential runner

`tools/java_diff.py` compiles staged Java fixtures, invokes their methods on a
reference JVM through the fixture-local `OracleMain`, and compares those
outcomes with the `jvmevm` CLI. The JVM is a test oracle only. The EVM CLI is
always given the unchanged `.class` bytes emitted by `javac`; this tool does not
parse, translate, evaluate, or specialize class files.

Build the CLI separately, then run from the repository root:

```sh
make java-smoke  # all smoke-marked cases in the current cumulative stage
make java-fast   # smoke + 20 seeded cases; JAVA_DIFF_SEED=57 changes the seed
make java-full   # every case in the current cumulative stage
# Or invoke directly after `make java-build`:
python3 tools/java_diff.py
python3 tools/java_diff.py --stage m3a --tier full
python3 tools/java_diff.py --stage m1 --case m1-add-basic
```

Defaults are `--stage m3a --tier smoke --seed 56`, fixtures at
`jvmevm/testdata/differential`, artifacts at `build/java-diff`, and CLI at
`build/bin/jvmevm`. Stage selection is cumulative: `m1` selects M1, `m2`
selects M1+M2, `m2b` selects M1+M2+M2b, and `m3a` or `all` adds M3a. A
manifest without M3a entries therefore continues to run its older cases under
the new default.
`smoke` runs smoke-marked cases, `fast` adds a seeded deterministic sample of at
most 20 other cases, and `full` runs every case selected by the stage. `--case`
selects one exact ID without sampling but still honors `--stage`. An empty
selection is an error.

For an alternate, self-contained fixture tree (primarily tests), use
`--fixtures DIR`. It must contain `cases.json`, adjacent guest sources, and
`OracleMain.java` with the additive schema/version-1 protocol frozen in
`JAVA_EVM_M2B_PLAN.md`.

## Outcome protocol

Existing value cases retain `expected_kind: "value"`. An explicitly expected
uncaught Java outcome uses both:

```json
{
  "expected_kind": "java_exception",
  "expected_exception": "java.lang.ArithmeticException"
}
```

`expected_exception` is required for exception cases, must be a syntactically
valid fully-qualified Java class name, and is rejected on value cases. The
reference oracle prints exactly one `value=<signed-int32>` or
`exception=<fqcn>` line based on the actual invocation; expected answers are not
hardcoded into the runner or oracle.

A successful EVM CLI invocation prints the four common keys `engine`,
`runtime_bytes`, `runtime_sha256`, and `gas_used`, plus exactly one outcome key:

```text
result=<signed-int32>
```

or

```text
exception=<fqcn>
```

The runner accepts an exception as a passing Java outcome only when the
manifest explicitly expects `java_exception` and the expected, JVM, and EVM
classes all match. M3a uses the same protocol for
`java.lang.StackOverflowError`; M2b's `java.lang.ArithmeticException` remains
unchanged. Value/exception disagreements and wrong exception classes fail.
Nonzero CLI exits, generic reverts, and out-of-gas executions remain EVM
failures; in particular, out of gas is never reclassified as a stack overflow.

## Limits and failures

The runner validates schema version, required fields, unique IDs, stages,
expected outcome fields, signed-int32 arguments (JSON booleans are rejected),
fixture-confined existing source paths, positive gas limits up to 100,000,000,
and per-case timeouts up to 300 seconds. `javac --release 8` has a 60-second
timeout; Java/Javac version queries and all oracle/EVM invocations are also
bounded. Existing smoke/fast sampling and case budgets are unchanged.

Any selected-case failure gives a nonzero exit. Reports distinguish value or
outcome mismatches, unexpected oracle exceptions, oracle protocol/process
failures, EVM revert, out-of-gas, timeout, malformed EVM output, compile
failures, and harness errors. Expected cases are never silently skipped.
Successful value and Java-exception EVM outputs are parsed strictly, must report
positive gas within the case limit, and must carry one identical generic
`runtime_sha256` throughout the run.

## Artifacts and replay

`report.json` stores the selected IDs, stage/tier/seed, Git commit when
available, fixture source/manifest/class hashes, runtime hash, queried JDK
versions, exact command argv/stdout/stderr/exit or timeout status, gas limit and
gas used, per-case classification, and an exact single-case replay command.
Outcome metadata uses `oracle_value`/`evm_value` or
`oracle_exception`/`evm_exception` as applicable. `failures.txt` is a concise
human-readable failure list.

Compiled fixture classes are retained under a new `run-*/compiled/` directory
for every run. Each run also keeps its own report and failure summary; top-level
`report.json` and `failures.txt` describe the latest run. Existing compiled or
run directories are never deleted or reused. The default `build/java-diff/`
and named `build/java-diff-*/` artifact directories are explicitly Git-ignored.

Replay is not a hermetic snapshot: the command recompiles fixtures and uses the
specified CLI. It therefore depends on the current fixture source, Java/Javac,
CLI binary, and embedded runtime. Compare the recorded hashes and version
output when reproducing an old report.

## Tests

`make java-harness-test` runs all runner tests including real JVM/EVM smoke.
Mock compiler/JVM/CLI protocol and error-path coverage alone:

```sh
python3 -m unittest discover -s tools -p 'test_java_diff.py'
```

The real M1 test creates a temporary manifest, guest source, and `OracleMain`,
then uses actual `javac`, `java`, and a prebuilt CLI supporting M1 (including
later cumulative stages):

```sh
go build -o build/bin/jvmevm ./cmd/jvmevm
JAVA_DIFF_REAL_EVM_BIN="$PWD/build/bin/jvmevm" \
  python3 -m unittest tools.test_java_diff.JavaDiffTests.test_real_m1_temporary_fixture_smoke
```
