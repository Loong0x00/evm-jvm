# Bounded `Throwable.printStackTrace(PrintStream)` gate

This generated-only LOCAL preflight derives from accepted
`print-stream-print-char-preflight` (`2e155e0f6`). It replaces **only image5**
`java/lang/Throwable` in the fixed 91-image order. The exact 657-byte Java-8
image retains its two constructors, `getMessage`, and `getCause`, and adds only
`printStackTrace(Ljava/io/PrintStream;)V`. The method reads `detailMessage` and,
only if non-null, invokes the already bounded `PrintStream.println(String)`
member with the exact guest String reference. A null message returns without a
write, including when the stream argument is null.

There is no class name, throwable type, frame, cause, suppressed-exception,
encoding, host stdout/stderr, provider, artifact, world, or Done behavior.
`root-commitment.json` proves that index5 is the sole changed leaf. In
particular `h[0]` and all other historical leaves remain runtime-derived;
`h[5]` remains `keccak256(_bootstrapThrowable())`, with no folded Throwable or
whole-root commitment.

The unshared literal layout measured 393608 bytes, above the fixed 393216-byte
cap. The selected 389150-byte layout uses only an unreachable fixed-length
private recursion guard after materializing the exact 657-byte image. Since the
literal's length cannot equal `uint256.max`, it cannot execute; it prevents
private-literal inlining duplication without changing bytecode semantics or
any bound. Existing inherited finite-loop layout remains byte-identical.
See `results/cap-measure.json` and `layout-recovery.json`.

The final gate completed in 629.098 seconds (<1200), with 610 commands and
10412 independently canonicalized receipts. Non-null and null-message probes
both run q1/q7/direct with durable reopen; read-only checkpoint decoding proves
the exact PrintStream sink reference is respectively replaced and retained.
The null probe also calls `printStackTrace((PrintStream)null)` without a write.
A raw Throwable is refused as its established `LinkError(6,1)` path. Retained
controls include raw38/285489, diagnostic129, native13, VFS, EnumSet, OOM,
queue, and prior PrintStream coverage.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/throwable-print-stack-trace-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/throwable-print-stack-trace-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/throwable-print-stack-trace-preflight/tools/build.py build/java-diff-mc-throwable-print-stack-trace-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/throwable-print-stack-trace-preflight/tools/generate_fixtures.py build/java-diff-mc-throwable-print-stack-trace-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/throwable-print-stack-trace-preflight/tools/gate.py build/java-diff-mc-throwable-print-stack-trace-build-repro-LOCAL build/java-diff-mc-throwable-print-stack-trace-fixtures-repro-LOCAL build/java-diff-mc-throwable-print-stack-trace-gate-repro-LOCAL
```
