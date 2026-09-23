# Bounded `Math.asin(double)` Q120 candidate

This generated-only implementation adds the measured exact `java/lang/Math|asin|(D)D` surface. It changes Math bootstrap image 89 only (from 289 to 304 bytes) and adds global native binding 20. Binding 18 (`sqrt`), bounded integer binding 19 (`sin`), the other 96 bootstrap images, String-local binding 12, raw-class/byte ceilings (71 / 471,911), packed-float handling, sparse checkpoint format, and authenticated package/engine-codehash/transport boundaries remain unchanged.

The 387,706-byte engine is under the unchanged 393,216-byte LOCAL cap. Source-derived ordered bootstrap root: `e4e36043b03626d5766b849f9504f6520fafbd462fc19238a0e9a580f480ef42`; only leaf/index 89 changed. The Math image SHA-256 is `678f8cef035281f8db9c55ca436048c4494ace649b82c54eb859f4ecb4ea99ad`.

## Kernel and bounds

The EVM consumes only the guest's raw binary64 bits. It preserves both zero encodings and returns the input bits through `|x| <= 2^-27`, where

```
0 <= asin(x)-x <= x^3 / (6(1-x^2)) < 0.5 ulp(x)
```

including subnormals. Finite `|x| > 1` and all NaN/infinity encodings atomically revert with `MathAsinProfileError(1, pc)`; they do not produce a guest result or commit a partial root/Head.

For other inputs, the binary64 significand/exponent is converted exactly to Q120. On `0 < |x| <= 1/2`, the kernel evaluates the positive arcsine series for `n=0..128` with ties-to-even integer divisions. Its omitted tail is bounded by `(1/2)^259/(1-1/4) < 2^-258`. With each rounded Q multiply and coefficient step, term error obeys `E_n <= E_(n-1)/4 + 5/4`, so each term error is `<2` Q units and the accumulated error is `<258` Q units.

For `1/2 < |x| < 1`, it computes `pi/2 - 2*asin(sqrt((1-|x|)/2))`. Q120 half-delta quantization contributes `<2^-93` in the result (the closest binary64 input below 1 has `y > 2^-55`); flooring the Q120 square root contributes `<3/Q`. The root is calculated exactly by 120 fixed restoring rounds over a `<2^238` integer radicand. At `|x|=1`, the nearest Q120 scalar for `pi/2` produces the Java binary64 endpoint. The final signed Q120 result is packed to binary64 using integer nearest-even rounding.

All Q-series products are `<2^240`, the sqrt radicand is `<2^238`, and result/sum magnitudes are `<2^121`, all strictly below signed `2^255`; the source has no guest-controlled loop, floating operation, host math, precompile, lookup/output table, or result injection. The detailed implementation and source-normalization assertions are in `engine/MCEntryInterpreter.sol` and `tools/verify_source.py`.

## Verification

Reproduce with unique, initially absent names under the repository's ignored `build/` directory:

```sh
python3 evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/tools/verify_q120.py
python3 evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/tools/generate_fixtures.py build/java-diff-mc-math-asin-fixtures-<unique>
python3 evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/tools/build.py build/java-diff-mc-math-asin-build-<unique>
python3 evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/tools/gate.py build/java-diff-mc-math-asin-build-<unique> build/java-diff-mc-math-asin-fixtures-<unique> build/java-diff-mc-math-asin-gate-<unique>
python3 evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/tools/archive_results.py build/java-diff-mc-math-asin-build-<unique> build/java-diff-mc-math-asin-fixtures-<unique> build/java-diff-mc-math-asin-gate-<unique>
python3 evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/tools/verify_results.py
```

The completed generated-only gate took 568.123 seconds and verified 4,314 canonical receipts. The 43 EVM inputs cover ±0, tiny/subnormal/normal boundaries, both sides of 1/2, selected positive/negative `k/256`, and ±1. q1, q7, direct and durable reopen agree; every EVM raw double is within 1 ULP of the separately run Java 8 host witness and all selected float-cast bits match. The TEST-ONLY independent integer model checks all 17,066 supported oracle rows: maximum 1 ULP, 472 one-ULP differences from OpenJDK 8, zero float mismatches, and zero sampled monotonicity violations. Its oracle rows are not execution inputs or output tables.

The retained gate also exercises prior sine and sqrt, packed float conversion, float/int/double sparse-array q1/reopen, malformed sparse refusals, exact raw71, and the 471,911/471,912 byte boundaries plus prior library/capacity controls. The 471,911-byte package is coordinator-admitted and all bytes are read, but the ordinary 1B-gas engine call runs out of gas before the checkpoint-cap selector; this remains explicitly **not** a checkpoint-cap acceptance. The 471,912-byte package is rejected by the unchanged coordinator boundary. Hashes, root proof, exact Math image, fixtures, q1/q7/direct checkpoints, receipts, and refusals are archived in `results/generated-gate-v1/` and authenticated by the nested and top-level `SHA256SUMS`.

For an independent TEST-ONLY Java `BigInteger` replay of the supplied oracle model, compile `math-asin-independent-oracle/src/Q120AsinProbe.java` into a unique `build/java-diff-mc-math-asin-q120-java-check-<unique>/classes`, run it against the pinned `samples.tsv` with distinct summary/mismatch output paths, then call `tools/archive_java_q120.py <that-build-dir>`. This rerun does not overwrite the original oracle directory. The archived Java checks include 4,096 exact sqrt-floor tests and 4,110 independent Q120-to-binary64 nearest-even checks; the exact summary and mismatch files reproduce the separately tracked oracle evidence byte-for-byte.

This is only the worker's generated EVM candidate. The parent must independently rebuild/gate in a fresh domain and perform the separately authorized unchanged-original replay. This work did not open or execute the original JAR/classes/resources/world, did not accept an EULA, and makes no Minecraft world/`Done` or readiness claim.
