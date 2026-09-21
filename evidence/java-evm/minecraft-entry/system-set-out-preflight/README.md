# Generated bounded `System.setOut(PrintStream)` stage

This generated-only stage implements `JAVA_EVM_MC_SYSTEM_SET_OUT_PREPARATION.md` from accepted `parent-1b178a6eb`. It changes only canonical bootstrap image44, `java/lang/System`, and the binding16 Solidity path. The 1062-byte Java-8 image retains `err` and `out` as public static final `PrintStream` fields, retains exact binding15 `setErr`, and adds exactly public static native `setOut(PrintStream)`.

Global binding16 is recognized only for exact `System.setOut(Ljava/io/PrintStream;)V`. Normal `invokestatic` resolution, initialization, descriptor parsing, and `PrintStream` assignability run first. Binding16 consumes the supplied guest reference, including null, and writes only the canonical initialized `System.out` static cell. `System.err` and every other static cell remain unchanged. A raw `java/lang/System` replacement is rejected by bootstrap ownership validation before it can acquire either binding. No SecurityManager permission, host stdout/stderr, console, file, forwarding, or provider behavior exists.

The generated focused guest witness performs direct replacement, `PrintStream` subclass replacement, null replacement, and reset to the original `out`; each transition asserts retained `System.err` identity. q1/q7/direct terminal reopen checkpoints agree at 209 Java and 7 internal steps, with machine root `0xf5ca21c95263119a94d20cc9de8bb5ef290b7dd53618136b138b6754bcadbfd1` and opaque payload SHA-256 `4c837ecbfe4dc12865ed60e9abfa9bae46aa58b95a4d866ab8c1e3c5a66eef8c`. The exact raw-System-native replacement rejects atomically with `BootstrapProfileError(1,1)` selector `0x6a23ad80`; its root is unchanged.

The full focused q1/q7/direct/reopen plus retained direct/reopen gate completed 511 commands and 865 independently canonicalized receipts in 153.731347 seconds, below the fixed 1200-second bound. Runtime is 377312 bytes, below the unchanged 393216-byte cap. Raw52/329162, diagnostic146, 94 bootstraps, String-local11, exception kinds14, frames128, checkpoint1MiB, reserve25M, and LOCAL1B external budget remain pinned. `root-commitment.json` records the runtime-derived 94-leaf ordered root `d9b2bc4f1e8799d1df1e981a5ea03016c1d80e5801ba72aef6dd8be8677f0235`; only leaf44 differs from the accepted image set.

No original artifact/JAR/class/resource, world, EULA, or Done work is present or claimed. Parent original52 replay is deferred.

## Reproduction

From repository root, using only local pinned tools and fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/system-set-out-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/system-set-out-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/system-set-out-preflight/tools/build.py build/java-diff-mc-system-set-out-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-set-out-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-system-set-out-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-set-out-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-system-set-out-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-set-out-preflight/tools/gate.py build/java-diff-mc-system-set-out-build-repro-LOCAL build/java-diff-mc-system-set-out-retained-fixtures-repro-LOCAL build/java-diff-mc-system-set-out-fixtures-repro-LOCAL build/java-diff-mc-system-set-out-gate-repro-LOCAL
```

Tracked `results/` contains build pins, source verification, generated fixture manifests, raw refusal receipt, full gate summary, canonical receipt summary, and timing. `SHA256SUMS` covers every tracked stage file except itself.
