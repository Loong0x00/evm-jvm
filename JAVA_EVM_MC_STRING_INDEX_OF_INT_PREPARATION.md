# Java-on-EVM Minecraft `String.indexOf(int)` preparation

## Measured blocker
Accepted `parent-c959b6fdf` genuinely loads nf.class and reaches87279J/77I. Canonical q1 raises `StringProfileError(1,17)`. Fresh-domain EVM-only diagnostics identify owner bootstrap String class index94, method `indexOf`, descriptor `(I)I`.

## Required bounded change
Append exactly `public int indexOf(int ch)` to the current canonical bootstrap `java/lang/String`. Implement Java8 code-point semantics over its UTF-16 units: first BMP/raw-surrogate occurrence; valid supplementary code point as a surrogate pair; zero/negative/out-of-range and absent behavior exactly match Java8. Use existing bounded `length()`/`charAt()` surfaces; add no overloads or other String API.

Preserve bootstrap count95 and all non-String images/order byte-for-byte (including Map$Entry and Integer/highestOneBit), raw68/394767, diagnostic163, native16/String-local11 and every other limit/semantic. Rebuild only the String image and independently verify the changed ordered root. Runtime<=393216 (prior376562).

## Gate
Generated Java8 host-oracle cases: empty, ASCII first/repeated/absent, NUL, BMP, raw surrogate, valid supplementary pair, negative and >0x10ffff. Prove exact metadata, q1/q7/direct/reopen, omitted overload and raw String replacement refusals, prior String APIs retained, independent image/root verification, plus retained direct/reopen regression. Whole gate<=1200s; durable results/SHA256SUMS/clean commit. No originals/JAR/classes/resources/network; parent replay deferred. No provider/world/Done claim.
