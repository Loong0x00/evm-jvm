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
python3 tools/java_diff.py --stage m4fa --tier full
python3 tools/java_diff.py --stage m1 --case m1-add-basic
```

Defaults are `--stage m4fa --tier smoke --seed 56`, fixtures at
`jvmevm/testdata/differential`, artifacts at `build/java-diff`, and CLI at
`build/bin/jvmevm`. Stage selection is cumulative: `m1` selects M1, `m2` adds
M2, `m2b` adds M2b, `m3a` adds M3a, `m3b` adds M3b, `m3c` adds M3c, `m3d` adds
M3d, `m4a` adds M4a, `m4b` adds M4b, `m4c` adds M4c, `m4d` adds M4d,
`m4e` adds M4e, and `m4fa` or `all` adds M4f-a. A manifest without entries
in the newest stage continues to run its older cases under the new default. `smoke` runs smoke-marked cases,
`fast` adds a seeded deterministic sample of at most 20 other cases, and `full` runs every
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

## M3d hierarchy cases

M3d cases use the unchanged M3b bundle protocol: the manifest explicitly lists
every supplied class and the runner neither discovers nor loads superclass
files. Superclass/member resolution and initialization order are EVM work, not
runner work. M3d remains limited to ordinary classes and supported static
integer members; interface, instance, and other staged-negative fixtures are
validation tests, not differential-oracle passes.

The manifest outcome schema is unchanged. In particular, hierarchy/link/access
reverts are not accepted reference-Java outcomes and cannot pass by matching an
arbitrary EVM failure. Only the exact value or named Java exception protocol
below is comparable by the differential oracle.

## M4a integer-array cases

M4a retains the schema-1 root protocol: entry methods still accept only signed
`int` arguments and return `int`. Array references are created and manipulated
inside guest bytecode and are never serialized as host arguments, results, or
heap identifiers. Single-class and ordered raw-bundle handling, source/class
hashes, runtime identity checks, and replay commands are unchanged.

The reference JVM is used for ordinary array values and for real
`NegativeArraySizeException`, `ArrayIndexOutOfBoundsException`, and
`NullPointerException` comparisons. EVM logical-cap `OutOfMemoryError` probes
are focused mock/Go tests only: the runner must not attempt to exhaust the host
JVM heap, whose policy is not the interpreter's fixed resource profile.

## M4b ordinary-object cases

M4b keeps schema 1 and the raw ordered-bundle protocol unchanged. Roots remain
static methods with only signed `int` arguments and an `int` result; object,
array, and uninitialized-reference values are never serialized by this runner.
Construction, bootstrap `java/lang/Object`, layouts, fields, reference
assignability, direct private/super calls, and constructor lifecycle are all
interpreted inside the EVM from the supplied raw classfiles.

The reference JVM runs only trusted, finite ordinary-object fixtures. Fixed EVM
object-count and instance-slot exhaustion probes are mock/Go tests, not host JVM
OOM oracles. M4b adds no Java exception kinds: arithmetic, stack overflow,
initializer error, negative array size, array bounds, null receiver, and logical
OOM remain exact kinds 1 through 7. In particular, an EVM out-of-gas execution
or arbitrary revert never passes as `OutOfMemoryError` or another Java outcome.
Virtual/interface dispatch, casts/type tests, handlers, and general class-library
APIs remain outside this runner stage.

## M4c virtual dispatch and type-test cases

M4c remains schema 1 and cumulative over M4b. It adds trusted, finite fixtures
for `invokevirtual`, `checkcast`, and `instanceof`; ordered raw class bundles,
static `(I...)I` roots, hashes, budgets, and the value-or-exception output
protocol do not change. References are still guest-only values and are never
serialized by the host runner. Interface calls, reference-array allocation and
storage, exception handlers, and broader class-library APIs remain deferred.

A failed `checkcast` may produce the one newly recognized outcome
`java.lang.ClassCastException`. As with arithmetic, null, and bounds failures,
a cast failure escaping an active class initializer is compared as
`java.lang.ExceptionInInitializerError`. Target type resolution and class
initialization behavior are interpreter work; the runner does not inspect class
hierarchies or discover omitted targets. EVM out of gas remains an engine
failure and can never match either exception.

## M4d reference-array cases

M4d keeps schema 1, cumulative selection, static `(I...)I` roots, and the
ordered unchanged-classfile bundle protocol. Reference arrays, their elements,
and identities stay entirely inside guest execution. Trusted finite fixtures
cover `anewarray`, `aaload`, `aastore`, recursive array covariance, and array
casts/type tests; `multianewarray`, interfaces, and other primitive array types
remain deferred.

An incompatible non-null `aastore` may produce the newly recognized exact
`java.lang.ArrayStoreException` outcome. If it escapes class initialization the
observable outcome remains `java.lang.ExceptionInInitializerError`. Logical EVM
heap-cap probes remain focused Go/mock tests only; the host JVM is never driven
toward OOM. Out of gas and arbitrary reverts are still engine failures, not Java
exceptions.

## M4e multidimensional-array cases

M4e keeps schema 1, static `(I...)I` roots, cumulative selection, and the raw
ordered class-bundle protocol unchanged. Trusted finite fixtures may use
`multianewarray` for supported `int` and ordinary-class/Object array leaves,
including partial dimensions. Every count and all resulting references remain
inside guest execution; the runner neither parses array descriptors nor plans or
allocates guest arrays.

Negative multidimensional counts use the existing exact
`java.lang.NegativeArraySizeException` outcome, including initializer wrapping
as `java.lang.ExceptionInInitializerError`. Logical aggregate/per-array quota
`java.lang.OutOfMemoryError` cases remain focused Go/mock tests: they must not
induce host JVM OOM. The recognized exception set and schema remain unchanged,
and EVM out of gas is still an engine failure rather than Java OOM.

## M4f-a interface graph and abstract-call cases

M4f-a remains additive schema 1 and cumulative over M4e. Trusted finite fixtures
may supply ordinary classes and public abstract interfaces in an explicit ordered
bundle, and may exercise `invokeinterface`, abstract-interface fallback for
`invokevirtual`, interface reference types, interface-leaf arrays, and the
`Cloneable`/`Serializable` array marker relations. The runner still performs no
classfile parsing, graph discovery, method resolution, type checking, dispatch,
or initialization; all listed javac outputs are passed unchanged and those rules
are enforced by EVM bytecode.

M4f-a adds no Java exception kind. Interface cast and array-store failures use the
existing exact `ClassCastException` and `ArrayStoreException` outcomes. Interface
graph/link/profile errors and deferred interface features remain focused Go-test
reverts and are never accepted as oracle outcomes. Fixtures must not rely on
interface defaults, private interface bodies, interface static invocation/fields,
array-receiver method dispatch, or unbounded host resource exhaustion. Abstract
interface metadata (including unentered static initialization metadata) does not
by itself initialize an interface.

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
adds `java.lang.ExceptionInInitializerError`; M3d preserves that outcome when
arithmetic escapes a superclass initializer. `java.lang.StackOverflowError`
remains unwrapped. M2b's `java.lang.ArithmeticException` outside initialization
remains unchanged. M4a and M4b additionally recognize exact
`java.lang.NegativeArraySizeException`,
`java.lang.ArrayIndexOutOfBoundsException`, `java.lang.NullPointerException`,
and `java.lang.OutOfMemoryError` outcomes. M4c additionally recognizes exact
`java.lang.ClassCastException`; M4d adds exact
`java.lang.ArrayStoreException`. Unknown exception names, even syntactically
valid Java names, are rejected rather than extending the frozen outcome
protocol. The first three, class-cast, and array-store failures, like
arithmetic, become `java.lang.ExceptionInInitializerError` when they escape active class
initialization; `OutOfMemoryError` and `StackOverflowError` remain unwrapped.
The fixture oracle may report the two initializer-time Error outcomes from
`Class.forName`, before reflective invocation. Oracle process,
configuration, or malformed-output errors still fail and are never converted
into expected outcomes. Value/exception disagreements, wrong wrapping, and
wrong exception classes fail. Nonzero CLI exits, generic reverts, and out-of-gas
executions remain EVM failures; out of gas is never reclassified as a Java
exception or an `OutOfMemoryError`.

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
