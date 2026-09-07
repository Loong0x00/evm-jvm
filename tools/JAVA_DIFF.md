# Java/EVM differential runner

`tools/java_diff.py` compiles staged Java fixtures, invokes their methods on a
reference JVM through the fixture-local `OracleMain`, and compares those values
with the existing `jvmevm` CLI. The JVM is a test oracle only. The EVM CLI is
always given the unchanged `.class` bytes emitted by `javac`; this tool does not
parse, translate, or specialize class files.

Build the CLI separately, then run from the repository root:

```sh
go build -o build/bin/jvmevm ./cmd/jvmevm
python3 tools/java_diff.py
python3 tools/java_diff.py --stage m1 --tier full
python3 tools/java_diff.py --stage m1 --case m1-add-basic
```

Defaults are `--stage m2 --tier smoke --seed 56`, fixtures at
`jvmevm/testdata/differential`, artifacts at `build/java-diff`, and CLI at
`build/bin/jvmevm`. `--stage m2` is cumulative and includes M1; `all` currently
includes both known stages. `smoke` runs smoke-marked cases, `fast` adds a
seeded deterministic sample of at most 20 other cases, and `full` runs every
case selected by the stage. `--case` selects one exact ID without sampling but
still honors `--stage`. An empty selection is an error.

For an alternate, self-contained fixture tree (primarily tests), use
`--fixtures DIR`. It must contain `cases.json`, adjacent guest sources, and
`OracleMain.java` with the protocol frozen in `JAVA_EVM_M2_PLAN.md`.

## Limits and failures

The runner validates schema version, required fields, unique IDs, stages,
signed-int32 arguments (JSON booleans are rejected), fixture-confined existing
source paths, positive gas limits up to 100,000,000, and per-case timeouts up to
300 seconds. `javac --release 8` has a 60-second timeout; Java/Javac version
queries and all oracle/EVM invocations are also bounded.

Any selected-case failure gives a nonzero exit. Reports distinguish value
mismatches, oracle exceptions, oracle protocol/process failures, EVM revert,
out-of-gas, timeout, malformed EVM output, compile failures, and harness errors.
Expected cases are never silently skipped. Successful EVM output is parsed
strictly, and one run must report an identical generic `runtime_sha256` for all
successful EVM executions.

## Artifacts and replay

`report.json` stores the selected IDs, stage/tier/seed, Git commit when
available, fixture source/manifest/class hashes, runtime hash, queried JDK
versions, exact command argv/stdout/stderr/exit or timeout status, gas limit and
gas used, per-case classification, and an exact single-case replay command.
`failures.txt` is a concise human-readable failure list. Compiled fixture
classes are retained under `compiled/`. The default artifact location is under
the repository's ignored `build/` tree.

Replay is not a hermetic snapshot: the command recompiles fixtures and uses the
specified CLI. It therefore depends on the current fixture source,
Java/Javac, CLI binary, and embedded runtime. Compare the recorded hashes and
version output when reproducing an old report.

## Tests

Mock compiler/JVM/CLI protocol and error-path coverage:

```sh
python3 -m unittest discover -s tools -p 'test_java_diff.py'
```

The real M1 test creates a temporary manifest, guest source, and `OracleMain`,
then uses actual `javac`, `java`, and a prebuilt M1 CLI:

```sh
go build -o build/bin/jvmevm ./cmd/jvmevm
JAVA_DIFF_REAL_EVM_BIN="$PWD/build/bin/jvmevm" \
  python3 -m unittest tools.test_java_diff.JavaDiffTests.test_real_m1_temporary_fixture_smoke
```
