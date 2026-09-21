# Generated bounded `System.setErr(PrintStream)` stage

This generated-only stage implements `JAVA_EVM_MC_SYSTEM_SET_ERR_PREPARATION.md` from accepted `parent-88245dfff`. It changes only canonical bootstrap image44, `java/lang/System`, and ordered-root leaf44. The new 1045-byte Java-8 image retains `err` and `out` as public static final `PrintStream` fields and adds exactly public static native `setErr(PrintStream)`.

Global binding15 is recognized only for that exact native `System.setErr(Ljava/io/PrintStream;)V` declaration. Normal `invokestatic` resolution, initialization, descriptor parsing, and `PrintStream` assignability run first. Binding15 consumes the supplied guest reference (including null) and writes only the canonical initialized `System.err` static cell. It neither writes `System.out` nor exposes any generic static mutation. Raw `java/lang/System` replacement is rejected during owned-bootstrap validation before it can acquire the binding.

The generated focused guest witness performs direct replacement, a `PrintStream` subclass replacement, null replacement, and reset to the original `err`; every transition asserts that `System.out` remains its original identity. q1/q7/direct terminal durable reopen agree at 209 Java / 7 internal steps, with machine root `0x9e01e48c396489c3f968b6a299ff7fd9c746192c3bae3fba50455a7b478831e7` and opaque payload SHA-256 `717b594fb4d1689b68827527afeba99b2b3d7e1516c69210988c529f0e29e9fd`. The exact raw-System-native replacement rejects atomically with `BootstrapProfileError(1,1)` selector `0x6a23ad80`; its root is unchanged.

The full focused q1/q7/direct/reopen plus retained direct/reopen gate completed 511 commands and 865 independently canonicalized receipts in 159.293139 seconds, below the fixed 1200-second bound. Runtime is 375425 bytes, below the unchanged 393216-byte cap. Raw52/329162, diagnostic146, 94 bootstraps, String-local11, exception kinds14, frames128, checkpoint1MiB, reserve25M, and LOCAL1B external budget remain pinned. `root-commitment.json` records the runtime-derived 94-leaf ordered root `82843b2d85f2c1ecc06b2a7c520682379eaf00eeba2ac3c557f6c618ddce56a7`; only leaf44 differs from the accepted image set.

No SecurityManager permission, host stderr/stdout, forwarding, console, file, provider behavior, original artifact/JAR/resource, world, EULA, or Done work is present or claimed. Parent original52 replay remains deferred.

## Reproduction

From repository root, using only local pinned tools and fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/system-set-err-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/system-set-err-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/system-set-err-preflight/tools/build.py build/java-diff-mc-system-set-err-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-set-err-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-system-set-err-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-set-err-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-system-set-err-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-set-err-preflight/tools/gate.py build/java-diff-mc-system-set-err-build-repro-LOCAL build/java-diff-mc-system-set-err-retained-fixtures-repro-LOCAL build/java-diff-mc-system-set-err-fixtures-repro-LOCAL build/java-diff-mc-system-set-err-gate-repro-LOCAL
```

Tracked `results/` contains build pins, source verification, generated fixture manifests, raw refusal receipt, full gate summary, canonical receipt summary, and timing. `SHA256SUMS` covers every tracked stage file except itself.
