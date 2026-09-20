# Bounded `StringBuilder.append(char)` generated-only stage

This LOCAL generated-only stage starts from accepted `parent-868c7d1b8` monitor
support, represented durably by `monitor-enter-exit-preflight`. It changes only
bootstrap image84 (`java/lang/StringBuilder`) in the unchanged 91-image order.
The ordinary Java 8 `append(char)` method returns the same builder and delegates
to the retained `append(String)` copy path with a one-element `char[]`; it thus
preserves the existing logical prefix and appends exactly one UTF-16 code unit.

`bootstrap/java/lang/StringBuilder.java` is compiled with the pinned Java 8
flags. The bounded EVM class parser never consumes Code-local `StackMapTable`
attributes, so `tools/strip_stackmap.py` removes only those four attributes
(64 bytes) from the generated 990-byte class. It retains every constant-pool
entry, field, method header, Code byte, exception table, and all non-StackMap
attributes. The resulting 926-byte image has SHA-256
`7f2e95a40c6ec353b603368e0a2609a2e0baa7cf84f7d65b7d4865daf6792270`.
`tools/verify_source.py` recompiles and proves that derivation, proves the
engine differs from its parent only in the fresh domain strings and image84,
and recalculates the 91-leaf runtime-derived bootstrap root.

The focused trusted fixture starts with the retained `"pre"` prefix and then
appends NUL, ASCII `A`, high surrogate `U+D83D`, and low surrogate `U+DE00`.
It checks same-builder identity, each output code unit, and pre-append
`toString` independence. Its q1/q7/direct/reopen chains each terminate at
1044 Java / 2 internal steps with machine root
`0x51fbf1223732ae7fd08e992d70aed0c06cbea61e0d8bb1b6e75dd2ead6ba896d`
and opaque payload SHA-256
`bfade40e1f5e4743562d63e1aa37370d33b75ef4cb9b783cacdcc8a10f68cfbd`.
The retained gate also reruns monitor support and all inherited controls.

The reproducible runtime is 393208 bytes, 8 bytes below the unchanged 393216
cap (baseline 393191). Raw38/285489, diagnostic129, native13, every image
except84, all quotas, compiler/toolchain, and semantics remain pinned. The
focused-plus-retained generated gate completed in 591.456 seconds (limit 1200)
and independently canonicalized 9711 receipts. Durable pins and concise
outputs are in `build-pins.json` and `results/`; large generated worlds remain
disposable under ignored `build/`.

No original artifact, JAR, class, resource, StatusData, provider factory,
world, or Done input/claim is included. Parent-owned accelerated original
replay is outside this stage. No other append overload is claimed.

Reproduce from repository root:

```sh
python3 evidence/java-evm/minecraft-entry/string-builder-append-char-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/string-builder-append-char-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/string-builder-append-char-preflight/tools/build.py build/java-diff-mc-string-builder-append-char-build-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-append-char-preflight/tools/generate_fixtures.py build/java-diff-mc-string-builder-append-char-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-append-char-preflight/tools/gate.py build/java-diff-mc-string-builder-append-char-build-LOCAL build/java-diff-mc-string-builder-append-char-fixtures-LOCAL build/java-diff-mc-string-builder-append-char-gate-LOCAL
```
