# Java/EVM differential runner

`tools/java_diff.py` compiles staged Java fixtures, invokes their methods on a
reference JVM through the fixture-local `OracleMain`, and compares those
outcomes with the `jvmevm` CLI. The JVM is a test oracle only. The EVM CLI is
always given unchanged `.class` bytes emitted by `javac`; this tool does not
parse, translate, evaluate, scan dependencies, or specialize class files.
Only trusted repository/test fixtures may be executed by the host oracle.

Build the CLI separately, then run from the repository root:

```sh
make java-smoke  # all smoke-marked cases in the current cumulative stage
make java-fast   # smoke + 20 seeded cases; JAVA_DIFF_SEED=57 changes the seed
make java-full   # every case in the current cumulative stage
# Or invoke directly after `make java-build`:
python3 tools/java_diff.py
python3 tools/java_diff.py --stage m3c --tier full
python3 tools/java_diff.py --stage m1 --case m1-add-basic
```

Defaults are `--stage m3c --tier smoke --seed 56`, fixtures at
`jvmevm/testdata/differential`, artifacts at `build/java-diff`, and CLI at
`build/bin/jvmevm`. Stage selection is cumulative: `m1` selects M1, `m2` adds
M2, `m2b` adds M2b, `m3a` adds M3a, `m3b` adds M3b, and `m3c` or `all` adds
M3c. A manifest without entries in the newest stage continues to run its older
cases under the new default. `smoke` runs smoke-marked cases, `fast` adds a
seeded deterministic sample of at most 20 other cases, and `full` runs every
selected case. `--case`
selects one exact ID without sampling but still honors `--stage`. An empty
selection is an error.

For an alternate, self-contained fixture tree (primarily tests), use
`--fixtures DIR`. It must contain `cases.json`, adjacent guest sources, and
`OracleMain.java` with additive schema version 1.

## M3b class-bundle manifest protocol

The manifest `class` is an ASCII dotted binary Java name, for example
`bundle.Root` or `bundle.Outer$Inner`; default-package names remain valid. It is
passed unchanged to `OracleMain`. Its root output path is derived solely from
this metadata (`bundle.Root` becomes `bundle/Root.class`), never by inspecting a
class header.

A case can opt into the bundle CLI with `class_files`, a nonempty ordered list
of distinct relative `.class` paths beneath that run's `javac -d` directory:

```json
{
  "id": "m3b-package-call",
  "stage": "m3b",
  "sources": ["bundle/Root.java", "bundle/Helper.java"],
  "class": "bundle.Root",
  "class_files": ["bundle/Helper.class", "bundle/Root.class"],
  "method": "run",
  "args": [42],
  "gas_limit": 10000000,
  "timeout_seconds": 10,
  "smoke": true,
  "expected_kind": "value"
}
```

After compilation every listed output must exist, be a regular file, and remain
inside the fresh compile directory after symlink resolution. Absolute paths,
empty or traversal components, duplicates, wrong extensions, missing outputs,
and symlink escapes are hard harness failures. The runner does not enumerate
javac output, infer dependencies, add the root class, or fall back to a
classpath. Thus a deliberately omitted entry or dependency is sent as omitted.

With `class_files`, the EVM command receives one `-class PATH` per list item in
exact listed order, then `-entry-class bundle/Root`; dotted-to-internal slash
conversion is explicit metadata serialization. Even one listed class selects
the bundle API. Without `class_files`, the historical single `-class ROOT`
command is retained exactly, with no `-entry-class`.

Each bundle case report records the compatible root `class_path` and
`class_sha256`, plus ordered `class_files`, resolved `class_paths`, ordered
`class_file_sha256` path/hash records, internal `entry_class`, and exact
`evm_argv`. The command record independently retains the argv actually run.
These fields make class order and every raw input artifact auditable.

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
`exception=<fqcn>` line based on actual invocation; expected answers are not
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

The runner accepts an exception as passing only when the manifest explicitly
expects `java_exception` and the expected, JVM, and EVM classes all match. M3c
adds `java.lang.ExceptionInInitializerError`; arithmetic escaping an active
initializer is wrapped as that class, while `java.lang.StackOverflowError`
remains unwrapped. M2b's `java.lang.ArithmeticException` outside initialization
remains unchanged. The fixture oracle may report the two initializer-time Error
outcomes from `Class.forName`, before reflective invocation. Oracle process,
configuration, or malformed-output errors still fail and are never converted
into expected outcomes. Value/exception disagreements, wrong wrapping, and
wrong exception classes fail. Nonzero CLI exits, generic reverts, and out-of-gas
executions remain EVM failures; out of gas is never reclassified as a Java
exception.

## Limits and failures

The runner validates schema version, required fields, unique IDs, cumulative
stages, expected outcomes, signed-int32 arguments (JSON booleans are rejected),
fixture-confined existing source paths, positive gas limits up to 100,000,000,
and per-case timeouts up to 300 seconds. `javac --release 8` has a 60-second
timeout; Java/Javac version queries and all oracle/EVM invocations are bounded.
Existing smoke/fast sampling and case budgets are unchanged.

Any selected-case failure gives a nonzero exit. Reports distinguish value or
outcome mismatches, unexpected oracle exceptions, oracle protocol/process
failures, EVM revert, out-of-gas, timeout, malformed EVM output, compile
failures, and harness errors. Expected cases are never silently skipped.
Successful value and Java-exception EVM outputs must report positive gas within
the case limit. Legacy and bundle invocations, including exception outcomes,
must all carry one identical generic `runtime_sha256` throughout a run.

## Artifacts and replay

`report.json` stores selected IDs, stage/tier/seed, Git commit when available,
fixture source/manifest/class hashes, runtime hash, queried JDK versions, exact
command argv/stdout/stderr/exit or timeout status, gas limit and gas used,
per-case classification, and an exact single-case replay command. Outcome
metadata uses `oracle_value`/`evm_value` or
`oracle_exception`/`evm_exception`. `failures.txt` is a concise failure list.

Compiled classes are retained under a new `run-*/compiled/` directory for every
run. Each run also keeps its own report and failure summary; top-level
`report.json` and `failures.txt` describe the latest run. Existing compiled or
run directories are never deleted or reused. Default `build/java-diff/` and
named `build/java-diff-*/` artifact directories are Git-ignored.

Replay is not a hermetic snapshot: it recompiles fixtures and uses the specified
CLI. It therefore depends on current fixture sources, Java/Javac, CLI binary,
and embedded runtime. Compare recorded hashes and version output when
reproducing an old report.

## Tests

`make java-harness-test` runs all runner tests including real JVM/EVM smoke.
Mock compiler/JVM/CLI protocol and error-path coverage alone:

```sh
python3 -m unittest discover -s tools -p 'test_java_diff.py'
```

The real legacy test creates a temporary manifest, trusted guest source, and
`OracleMain`, then uses actual `javac`, `java`, and a prebuilt CLI. It remains a
single-class M1 smoke and must pass on later cumulative runtimes:

```sh
go build -o build/bin/jvmevm ./cmd/jvmevm
JAVA_DIFF_REAL_EVM_BIN="$PWD/build/bin/jvmevm" \
  python3 -m unittest tools.test_java_diff.JavaDiffTests.test_real_m1_temporary_fixture_smoke
```
