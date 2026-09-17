# Bounded `Integer.valueOf(String)` source stage

This generated-only stage derives exactly from accepted WeakReference parent
`parent-cb0c15e54`. It replaces only the existing bootstrap image70
`java/lang/Integer`; all 87 bootstrap positions and every non-Integer image are
otherwise retained. The Java-8-produced Integer image is 1827 bytes, SHA-256
`0fb2a617951eb2228ac6277a85ae44da1c59647904d82c2cb68b613c6e33ba03`.

The retained Integer source keeps both constructors, numeric conversions,
equality/hash/compare, decimal `parseInt`, and accepted `valueOf(int)`. It adds
only:

```java
public static Integer valueOf(String s) { return new Integer(parseInt(s)); }
```

Thus parsing remains the existing ordinary negative-accumulation decimal guest
Code, and a valid result is a new guest `Integer` via the existing public
constructor. It retains guest `NumberFormatException` for null, empty,
sign-only, invalid decimal, and signed-overflow input. There is no radix
overload, cache or identity guarantee, formatting, broad boxing surface, host
primitive, or host parser.

Only this image plus domain/address and generated-artifact hash rebinding differs
from the accepted parent. Raw33/262158, 87 bootstraps, native13, diagnostic120,
selected resource/Properties/String/WeakReference pipeline, frames, checkpoint
and Head limits, compiler, and outlined tail remain pinned. One source build
produced runtime 391802 / 393216 bytes (1414-byte headroom) and a 5394-byte
coordinator.

The focused trusted Java-8 valid/invalid/null/overflow fixtures all complete
q1/q7/direct/reopen with identical terminal machine root and opaque payload per
fixture: valid `1240` Java / `3` internal steps, epochs `1240/178/1`; invalid
`320` / `11`, epochs `320/46/1`; null `38` / `8`, epochs `38/6/1`; overflow
`771` / `9`, epochs `771/111/1`. Valid includes the measured provider-priority
spelling `"10"`; invalid covers empty, sign-only, and non-decimal input; overflow
covers both signed boundaries. The no-init/raw replacement controls and omitted
`valueOf(String,int)` radix control are atomic. The retained direct/reopen gate
completed 89 result rows, 322 commands, 4311 canonical receipts, and 292.809
seconds (cap 1200).

Only trusted generated Java-8 sources are compiled. No original artifact, JAR,
class, resource, Provider construction, factory, world, or Done input is read or
claimed. Parent alone reruns unchanged original33.

Reproduce with local pinned tools only:

```sh
python3 evidence/java-evm/minecraft-entry/integer-value-of-string-preflight/tools/build.py build/java-diff-mc-integer-value-of-string-build-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-value-of-string-preflight/tools/generate_fixtures.py build/java-diff-mc-integer-value-of-string-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-value-of-string-preflight/tools/gate.py build/java-diff-mc-integer-value-of-string-build-LOCAL build/java-diff-mc-integer-value-of-string-fixtures-LOCAL build/java-diff-mc-integer-value-of-string-gate-LOCAL
```
