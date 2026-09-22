# Java 8 `String.indexOf(int)` generated preflight

This generated-only preflight implements `JAVA_EVM_MC_STRING_INDEX_OF_INT_PREPARATION.md` from the exact `classcount68-byte394767-preflight` basis.  It changes only canonical bootstrap `java/lang/String` image slot 26: Java 8 `public int indexOf(int ch)` guest Code over UTF-16 units.  It finds the first BMP unit (including an unpaired surrogate), recognizes a valid supplementary code point only as its high/low surrogate pair, and returns `-1` for negative, out-of-range, or absent values.

The Java 8 rebuilt String image is 1773 bytes, SHA-256 `42b340085b6639cdcad9167a7089da2e1afd81866ee3182ace092796b23258ec`, Keccak-256 `260c4d3836b0b6b5d7ceacb7eed84135b60f2a14a831220ecdb5906accb741d0`.  The independently recomputed ordered 95-bootstrap root is `2741d34b1949eb3cdabe20d0aef3dedca113e311467f90269b7e363b18635a9d`; all 94 other leaves are pinned byte-for-byte.  The rebuilt engine is 377043 / 393216 bytes.  Bootstrap count 95, raw 68 / 394767, diagnostic bound 163, native 16 / String-local 11, Map.Entry slot 94, and Integer slot 70 / `highestOneBit` remain pinned.

`tools/verify_source.py` compiles the Java 8 image, checks that `(I)I` is the sole added String method, proves the Solidity/transport delta is only the image and commitments, and independently rederives the ordered root.  `tools/generate_fixtures.py` creates trusted Java 8 host-oracled code-point cases only.  `tools/gate.py` executes the raw fixtures through ordinary EVM q1/q7/direct chains with terminal new-process reopen and re-encodes canonical receipts.  The two-int overload refusal correctly occurs during execution for q1 and at start for larger quanta; the gate accepts either lifecycle while requiring the same unchanged-root `CallError(1,5)` witness.

The durable generated-only output index is `results/manifest.json`; `SHA256SUMS` covers every tracked input/result in this directory except itself.

## Final reproduction

Run from this worktree root with pinned local Node dependencies and Java 8 installed at `/usr/lib/jvm/java-8-openjdk`:

```sh
python3 evidence/java-evm/minecraft-entry/string-index-of-int-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/string-index-of-int-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/string-index-of-int-preflight/tools/build.py build/java-diff-mc-string-index-of-int-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-index-of-int-preflight/tools/generate_fixtures.py build/java-diff-mc-string-index-of-int-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-index-of-int-preflight/tools/gate.py build/java-diff-mc-string-index-of-int-build-repro-LOCAL build/java-diff-mc-string-index-of-int-fixtures-repro-LOCAL build/java-diff-mc-string-index-of-int-gate-repro-LOCAL
```

No original/JAR/external class/resource/network/provider/world/EULA/Done input is opened or claimed. Parent original replay remains deferred.
