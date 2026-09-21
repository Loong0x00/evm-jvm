# Generated bounded `System.out` stage

This generated-only stage implements `JAVA_EVM_MC_SYSTEM_OUT_PREPARATION.md` from the accepted generated parent evidence `parent-1004177d2`. It changes exactly bootstrap image44, `java/lang/System`, from the parent artifact. The Java-8-produced image adds only:

```java
public static final PrintStream out;
```

Its genuine guest `<clinit>` constructs the retained `err` first and then a fresh non-null `out`. Both are ordinary distinct guest `PrintStream` objects. `out` is only the existing guest `println(String)` / `print(char)` sink state: this stage has no host stdout/stderr, console, file, provider, stream setter, input stream, or broader System API.

The generated `SystemOutProbe` reads both static final fields repeatedly, checks non-null/stable identity and `out != err`, carries `out` through a typed constructor handoff, and invokes the retained bounded print/println members on both streams. The read-only checkpoint diagnostic verifies separate stream handles and separate line/char sink cells. Its focused q1/q7/direct paths each reopen a durable terminal checkpoint. The host never runs this probe (`java8HostOracle: false`).

All retained generated controls use direct/reopen. They include System no-use and failed-initialization controls, raw System/PrintStream replacement refusals, raw51/raw52 and exact-byte boundaries, existing print/println controls, and retained bounded-library controls. The complete final gate took 120.950734 seconds, ran 480 commands, and independently canonicalized 468 public receipts, below the fixed 1200-second bound.

The engine is 373634 bytes, below the unchanged 393216-byte cap. Raw limits remain 51/328000; diagnostic bound145, 94 bootstrap positions, native14, String-local11, exception kinds14, frames128, checkpoint1MiB, reserve25M, external LOCAL1B budget, and all other limits/toolchain rules are unchanged.

`root-commitment.json` records the sole image44 leaf change and recomputes the ordered root from the runtime source bytes. Unchanged leaves remain runtime-derived in `_bootstrapRoot()`. It also retains the parent-reported root separately from the root physically derived from the parent source, so no historical pin is treated as a substitute for the source-derived commitment.

## Reproduction

From repository root, using fresh ignored `build/` paths and only local pinned dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/system-out-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/system-out-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/system-out-preflight/tools/build.py build/java-diff-mc-system-out-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-out-preflight/tools/generate_fixtures.py build/java-diff-mc-system-out-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-substring-int-preflight/tools/generate_fixtures.py build/java-diff-mc-string-substring-int-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-out-preflight/tools/gate.py build/java-diff-mc-system-out-build-repro-LOCAL build/java-diff-mc-system-out-fixtures-repro-LOCAL build/java-diff-mc-string-substring-int-fixtures-repro-LOCAL build/java-diff-mc-system-out-gate-repro-LOCAL
```

Tracked `results/` contains final hashes, fixture pins, canonical receipt summary, and timing. `SHA256SUMS` covers every tracked stage file except itself.

No original artifact/JAR/class/resource, unchanged-original replay, `ni`, provider/factory execution, world, EULA, or Done input is read or claimed. Parent alone owns unchanged-original replay.
