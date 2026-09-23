# Independent Java-8 large-array controls (generated only)

This directory is an isolated fixture/evidence contribution for the sparse-array
checkpoint work. It contains no engine, Solidity, coordinator, bootstrap, or
checkpoint-writer changes. Nothing here opens or depends on an original class,
JAR, resource, sibling worktree, or network input. Generated classfiles are test
inputs only, not evidence that any EVM execution succeeded.

## Guest controls

`src/SparseFloatMain.java` allocates an actual `float[65536]`, reads and checks
every default-zero element, writes three distant nonzero values, and reads them
back with Java bytecode (`faload`/`fcmpl`). Its `main` executes only the
three-nonzero case. `src/SparseOneFloatMain.java` is a separate guest entry for
the single far-end nonzero case, so each EVM invocation retains at most one large
array. Other independent entry controls cover a dense `float[65536]`, small
primitive arrays, and an `Object[]` with null defaults and distant references.
Each entry throws `RuntimeException` if a guest-side check fails.

`src/ArrayHostOracle.java` is host-test-only. The builder compiles with an
explicit Java 8 `javac`, runs each guest main under Java 8, then runs this
independent Java 8 oracle and checks its deterministic result. This proves only
that the generated fixtures behave as expected on that host JVM; it is not an
EVM, checkpoint, Minecraft, or guest-result claim.

## Optional 71-image raw binding set

`generated/bindings/` contains five main/control classfiles and 66 generated
`PadNN` classes (71 bindings total). Each padding class contains one inert,
never-called method with a large constant string; it adds no static fields and
is not referenced by the controls. Their sources are synthesized by
`build_controls.py` in a disposable build directory; no classfile rewriting or
classfile parsing is used. The builder selects the largest uniform string size
fitting the frozen bounds:

- bindings: **71**
- aggregate raw class bytes: **471849** (limit **471911**)
- constant-string bytes per `PadNN`: **6890**
- next uniform size (6891 bytes) would total **471915**, 4 bytes over the cap
- largest classfile: **7105** bytes; per-class limit: **262144** bytes
- toolchain: **OpenJDK 1.8.0_504 / javac 1.8.0_504**
- Java 8 host-oracle output: `generated/oracle-results.txt`

Exact per-image sizes and SHA-256 digests, exact Java host-oracle source hash,
and toolchain versions are in `generated/manifest.json`.
The repository-level `SHA256SUMS` covers the sources, scripts, manifest, oracle
output, and all generated raw classfiles. This raw set is optional as a parent
input; it does not imply interpreter acceptance of these images.

Reproduce into a new, disposable output directory (the builder refuses to
overwrite existing output):

```sh
python3 build_controls.py --output /path/to/fresh-output \
  --java8-home /usr/lib/jvm/java-8-openjdk
```

A Java 8 JDK is required. `JAVA8_HOME` may be used instead of the explicit flag.
The only output class bundle is the generated `bindings/` directory; the host
oracle class is kept out of that bundle. Parent replay under a selected semantic
engine, across quanta, transport reopen, or checkpoint equivalence is explicitly
deferred to the parent.

## Read-only checkpoint analyzer

`checkpoint_arrays.py CHECKPOINT` summarizes array handle, rank/leaf metadata,
length, count of nonzero cells, and bounded nonzero positions from the existing
dense `MR01` checkpoint transport prefix. For rank-1 primitive `float[]`, the
leaf is marked `float`; raw cell bits are reported as hex. It validates bounds
needed for safe parsing through heap records but deliberately does not validate
the remaining VFS/checkpoint suffix or establish canonicality. The analyzer is
not an execution authority and its output must never be used to construct,
modify, or resume a checkpoint. It understands only the current dense MR01
record layout; an incompatible/sparse transport version is refused rather than
interpreted. No real checkpoint was available or fabricated for this isolated
control task.

```sh
python3 checkpoint_arrays.py --help
```
