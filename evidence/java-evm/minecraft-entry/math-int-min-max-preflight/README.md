# Bounded Java 8 `Math` int min/max source stage

This generated-only stage derives from accepted ThreadLocal parent
`parent-396d5b062`. It appends one Java 8 image at bootstrap index 89:
`java/lang/Math`, a 253-byte SHA-256
`e51d3e61920e9f33267ac3cb4dc2c70289d1c5fd43eb0bf6efdbbb1721c21356` final direct
`Object` subclass. Its only members are private `<init>()V`, static
`max(II)I`, and static `min(II)I`.

Only this append, its reservation, bootstrap vector/allocation count `89→90`,
and read-only checkpoint diagnostic bound `124→125` change from the accepted
parent. Raw35/268379, all prior 89 image positions and bytes, native13,
String-local10, exception kinds14, resource pipeline, frames128,
checkpoint1MiB, Head32768, compiler, and all other fixed limits remain pinned.
Raw `java/lang/Math` substitution is refused before guest execution.

The initially natural layout exceeded LOCAL384. The accepted layout commits the
exact Math image through one fixed `DBOOT_MATH` hash and materializes it after
pinned loader metadata in the outlined tail. It builds at 393208 / 393216
bytes (8-byte headroom); `layout-recovery.json` records both measurements.

The trusted generated Math probe covers equal operands, sign crossings, and
both int32 extremes under q1/q7/direct/reopen. Those executions agree at 63
Java/2 internal steps and epochs 63/9/1, with identical machine root and opaque
payload. A no-use root leaves Math uninitialized. Raw replacement and supported
int-operand `abs` / `addExact` calls are atomic EVM refusals, so no omitted API
result is fabricated.

Focused plus retained direct/reopen gate: 109 rows, 380 commands, 4613 canonical
receipts, 318.462 seconds (cap1200). It uses only trusted generated Java 8
fixtures. No original artifact/JAR/class/resource, Provider/factory/world, or
Done input is opened or claimed; parent alone reruns original35.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/math-int-min-max-preflight/tools/build.py build/java-diff-mc-math-int-min-max-build-LOCAL
python3 evidence/java-evm/minecraft-entry/math-int-min-max-preflight/tools/generate_fixtures.py build/java-diff-mc-math-int-min-max-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/math-int-min-max-preflight/tools/gate.py build/java-diff-mc-math-int-min-max-build-LOCAL build/java-diff-mc-math-int-min-max-fixtures-LOCAL build/java-diff-mc-math-int-min-max-gate-LOCAL
```
