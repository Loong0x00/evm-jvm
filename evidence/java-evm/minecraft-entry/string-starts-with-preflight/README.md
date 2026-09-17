# Generated `String.startsWith(String)` source stage

This generated-only stage derives exactly from accepted Properties parent
`parent-1fc13ef12`. It replaces only bootstrap `java/lang/String` slot 26 with
a Java-8 (`-source 8 -target 8 -g:none`) image that retains all prior fields,
constructors, natives, `lastIndexOf(String)`, and `split(String)`, and adds
ordinary `startsWith(String)`.

The added method calls `prefix.length()` first, then compares offset-zero UTF-16
code units with existing `length()` and `charAt(int)` primitives. Thus empty,
longer, exact/prefix, absent, BMP, surrogate-pair, and lone-surrogate-prefix
inputs have normal Java-8 offset-zero behavior; null follows the ordinary
catchable guest NPE. No offset overload, substring, native binding, host
comparison, or broader String API is added.

`tools/verify_source.py` rebuilds the String image with pinned Java 8 and proves
that the accepted P2 engine differs only by fresh profile-domain commitments and
slot 26. It also verifies coordinator/driver exact deltas, raw `32/262144`, 86
bootstraps, 13 global natives, diagnostic bound 118, 128 frames, checkpoint 1
MiB, Head 32768, reserve 25M, external LOCAL gas 1B, and runtime cap 393216.

The generated gate runs new startsWith cases q1/q7/direct/reopen with canonical
receipts. Properties and all retained parent controls run direct/reopen so the
whole gate remains bounded to 1200 seconds. Fixture sources and ZIPs are
trusted generated inputs only; no original artifact, JAR, class, resource,
provider, factory, world, Minecraft run, or Done claim is involved.

Reproduce with local pinned tools only:

```sh
python3 evidence/java-evm/minecraft-entry/string-starts-with-preflight/tools/build.py build/java-diff-mc-string-starts-with-build-LOCAL
python3 evidence/java-evm/minecraft-entry/string-starts-with-preflight/tools/generate_fixtures.py build/java-diff-mc-string-starts-with-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/string-starts-with-preflight/tools/gate.py build/java-diff-mc-string-starts-with-build-LOCAL build/java-diff-mc-string-starts-with-fixtures-LOCAL build/java-diff-mc-string-starts-with-gate-LOCAL
```
