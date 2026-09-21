# Result: guest frame snapshots are generated-gate verified

Run `run1` built a 372134-byte LOCAL engine (under the 393216-byte stage cap)
and a 5394-byte coordinator. The exact Java-8 images are:

| leaf | slot | bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `Throwable` | 5 | 716 | `4454ff55c663c08bd8e17f8087193ef72e11f7154e3761f96f5a6cafd4507fa6` |
| `StackTraceElement` | 90 | 448 | `25ce147f4adc080d71bdf752e245cfebc4191c56b7d0feaa714ad963197a18de` |

The runtime-derived 94-leaf bootstrap root is
`9f660cdd0bc878c66d6c1b0075e1e1843b9f2086f6757162dbb1514799c00742`.
The prebuild verifier recomputed the Java images and all ordered leaf hashes,
then established that only slots 5 and 90 differ from the pinned parent source.

The generated EVM gate completed in 18.072 seconds. `guest-stack` (three frames)
and `guest-stack-two` (two frames) completed with their guest assertions over
actual dotted class/method names, top-first order, fresh arrays/elements, and
`isNativeMethod == false`; q1/q7/direct terminal roots and opaque payloads were
equal. `thread-empty` retained zero-length fresh arrays with its leaf dormant.
Raw Throwable and StackTraceElement substitutions were atomically rejected.
`results/gate-summary.json` records exact roots, receipts, commands, and bounds.

This is generated-only evidence. It is not an original/JAR/Minecraft/world/EULA
replay or an acceptance claim.
