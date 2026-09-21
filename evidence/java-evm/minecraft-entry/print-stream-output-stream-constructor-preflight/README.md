# Generated bounded `PrintStream(OutputStream)` stage

This generated-only stage implements `JAVA_EVM_MC_PRINT_STREAM_OUTPUT_STREAM_CONSTRUCTOR_PREPARATION.md` from accepted `parent-3aa2fed0a`. It changes exactly canonical bootstrap image83, `java/io/PrintStream`, and its ordered root leaf.

The 507-byte Java-8 image keeps `PrintStream` a direct `OutputStream` subtype and retains its no-arg constructor, `println(String)` reference sink, `print(char)` code-unit sink, and `write(int)` low-byte sink. It adds only public `<init>(Ljava/io/OutputStream;)V`: it invokes retained `OutputStream.<init>()`, then invokes `Object.getClass()` on the supplied guest stream. That ordinary receiver check catches null as canonical guest NPE. The constructor does not add `FilterOutputStream`, an inherited `out` field, stored forwarding target, forwarding, encoding, auto-flush, file, console, or host output behavior.

The focused non-null witness creates a concrete guest `OutputStream`, constructs both direct `PrintStream` and a subclass which invokes `super(OutputStream)`, and retains distinct private line/char sink values. Checkpoint inspection proves the supplied stream was not forwarded (`forwarded == 0`), while both existing guest-only PrintStream sinks retain their exact values. The null witness catches the canonical NPE and verifies no result is fabricated. An uninitialized root keeps OutputStream and PrintStream dormant. The retained raw `PrintStream` replacement control remains atomic and the retained direct/reopen corpus is unchanged.

Focused constructor and null probes each run q1/q7/direct with terminal durable reopen. The constructor agrees at 103 Java / 3 internal steps (epochs 103/15/1), with identical machine root `0xeccdf4626a2241c772f549902c2a15b9baeeb1ca7b88fdc1fcd79e47eb65a845` and opaque payload SHA-256 `cd54fea2001f2ed89a0b592da886a57e3d3e694803275148cae9e0c790608cbe`. The null-NPE witness agrees at 25 Java / 4 internal steps (epochs 25/4/1). The full focused plus retained direct/reopen gate took 134.909576 seconds, issued 501 commands, and independently re-encoded 625 canonical receipts, below the fixed 1200-second limit.

The runtime is 373860 bytes, below the unchanged 393216-byte cap. Raw52/329162, diagnostic146, 94 images, native14, String-local11, System out/err, exception kinds14, frames128, checkpoint1MiB, reserve25M, LOCAL1B external budget, toolchain, and runtime-derived ordered-root rules remain pinned. `root-commitment.json` records the sole leaf83 change: image SHA-256 `cd053e0847ae7c3a740a54e246fbc3dd3c42635bb44bf6fcdc317004b411a41c`, Keccak-256 `6587de63639fa1c563fc0b4f84dc0e0355cdbffdfd6d355c1f758b83873884b9`, ordered root `cf2aa359b32a5bb4ca0789b053ad4cef4aa3708eaac8ad7d9a17cb9158e9edde`.

## Reproduction

From repository root using fresh ignored `build/` paths and only local pinned dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-constructor-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/print-stream-output-stream-constructor-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-constructor-preflight/tools/build.py build/java-diff-mc-print-stream-output-stream-constructor-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-constructor-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-print-stream-output-stream-constructor-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-constructor-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-print-stream-output-stream-constructor-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-output-stream-constructor-preflight/tools/gate.py build/java-diff-mc-print-stream-output-stream-constructor-build-repro-LOCAL build/java-diff-mc-print-stream-output-stream-constructor-retained-fixtures-repro-LOCAL build/java-diff-mc-print-stream-output-stream-constructor-fixtures-repro-LOCAL build/java-diff-mc-print-stream-output-stream-constructor-gate-repro-LOCAL
```

Tracked `results/` holds the build pins, fixture manifests, source verification, full gate summary, canonical receipt summary, and timing. `SHA256SUMS` covers every tracked stage file except itself.

No original artifact/JAR/class/resource, unchanged-original replay, network, provider/factory execution, world, EULA, or Done input is read or claimed. Parent replay remains deferred.
