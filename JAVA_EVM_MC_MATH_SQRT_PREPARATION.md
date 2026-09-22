# Java-on-EVM Minecraft `Math.sqrt(double)` preparation

## Measured blocker
Accepted `parent-195ced67d` genuinely loads rk.class and reaches87533J/80I. Atomic q1 refuses `CallError(3,2)`. Fresh-domain EVM-only diagnostics identify exact static symbol `java/lang/Math|sqrt|(D)D` (static-resolution code3013/site4125). No host class/JAR parsing or host math established this dependency.

## Required one bounded semantic change
Add public static native `double Math.sqrt(double)` and global native binding18; String-local remains12. Implement deterministic correctly-rounded binary64 square root using only EVM integer/bit operations on guest IEEE bits (no host floating/math/precompile/oracle): finite positive normals and subnormals round to nearest representable result; exact squares stay exact; +0 and -0 are preserved; +infinity preserved; negative finite/-infinity and NaNs return a Java-valid quiet NaN. Binding validation must enforce exact `(D)D` shape and wide-value invariants. No other Math/StrictMath API.

A suitable bounded construction normalizes the input significand/exponent, forms the <=106-bit radicand, computes integer floor sqrt plus remainder with a fixed/bounded restoring/Newton algorithm in uint256, rounds by the exact midpoint comparison, and renormalizes carry. Source verification must rule out external/host math and unbounded guest-controlled loops.

Preserve raw71/471911, bootstrap96, diagnostic167. Preserve every prior image except measured Math, especially System identityHash SHA-256 `6e29f00abed753017741ad667314982061178298cb3fca5baa0d92f2f9d57564`, String, Locale, Map$Entry, Integer; derive changed ordered root independently. Preserve global bindings1..17 semantics and add only18. Runtime<=393216 (prior380017).

## Gate
Generated Java8 oracle fixtures cover exact squares, irrational neighbors/ties around powers, normal/subnormal inputs (including min/max finite), rounding-boundary vectors, +/-0, infinities, negatives and NaNs using guest comparisons/bit-safe witnesses; q1/q7/direct/reopen equivalence. Retain identityHash/System setters/properties, lower-case/Locale/String/Map/Integer, raw71 and capacity refusals; omitted cbrt/StrictMath.sqrt and raw Math replacement refuse. Verify only Math leaf changes, independent root, global18/String-local12, canonical receipts/DI0 reads, atomic refusals, <=1200s, durable results/SHA256SUMS clean commit. No original/JAR/resource/network/provider/world/EULA/Done input/claim, other worktrees, push/review/delegation/Fast; parent replay deferred.
