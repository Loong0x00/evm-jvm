# Result: Java 8 `String.indexOf(int)`

- Added only `String.indexOf(int):int` guest Code to canonical bootstrap slot 26. The Java 8 rebuilt image is 1773 bytes: SHA-256 `42b340085b6639cdcad9167a7089da2e1afd81866ee3182ace092796b23258ec`, Keccak-256 `260c4d3836b0b6b5d7ceacb7eed84135b60f2a14a831220ecdb5906accb741d0`.
- `verify_source.py` independently rebuilt the image, verified `(I)I` is the sole method addition, verified all 94 other bootstrap leaves unchanged, and recomputed 95-image root `2741d34b1949eb3cdabe20d0aef3dedca113e311467f90269b7e363b18635a9d`.
- Rebuilt engine is 377043 / 393216 bytes. Bootstrap count 95; raw 68 / 394767; diagnostic 163; global native 16; String-local native 11; Integer slot 70/highestOneBit and Map.Entry slot 94 are unchanged.
- Final generated Java 8 gate completed in 188.96514479501639 seconds (limit 1200): 169 commands and 2649 independently verified canonical receipts. Empty, ASCII first/repeated/absent, NUL, BMP, raw-surrogate, supplementary-pair, negative, and >`0x10ffff` cases agree across q1/q7/direct/reopen. Retained String, Map, Integer, raw68, and boundary controls also pass.
- `indexOf(int,int)` remains omitted with unchanged-root `CallError(1,5)` (`0x32e310eb`) at all quanta; raw String replacement remains rejected before guest execution. Raw69 and 394768 frontiers remain refusal witnesses.

Durable checksums and detailed generated-only summaries are in `SHA256SUMS` and `results/`. No original/JAR/external class/resource/network/provider/world/EULA/Done input or claim; parent original replay remains deferred.
