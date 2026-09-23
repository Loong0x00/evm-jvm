# Measured Math.sin signed-zero candidate

This isolated generated-only profile implements exactly the requested first measured `java/lang/Math.sin(D)D` use. Global native binding 19 accepts binary64 `+0.0` and `-0.0` only, returning the same raw bits. Every finite nonzero value, NaN, and infinity reverts atomically with the distinct `MathSinProfileError(1, pc)`; it does not approximate sine. The prior exact `Math.sqrt(D)D` binding 18 remains in place.

The genuine Java-8 `java/lang/Math` image is built from `bootstrap/java/lang/Math.java`; all 97 ordered bootstrap images are compared to the checked-in sparse-checkpoint baseline and only image 89 is permitted to differ. `verify_source.py` independently compiles the image with the pinned Java-8 `javac`, checks its bytes/SHA/Keccak, normalizes the interpreter back to the exact sparse baseline outside the Math image and binding19 delta, and derives the ordered bootstrap root from the actual image bytes and the Solidity `DBOOT` expression. The sparse primitive-array checkpoint codec is unchanged.

## Reproduction

Run from the repository root. All outputs use unique, ignored `build/` directories; the fixture generator runs host Java only on its generated test classes. No original JAR/classes/resources/world/EULA, network, sibling worktree, push, or Fast setting is involved.

```sh
python3 evidence/java-evm/minecraft-entry/math-sin-signed-zero-preparation/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/math-sin-signed-zero-preparation/tools/generate_fixtures.py build/java-diff-mc-math-sin-fixtures-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-signed-zero-preparation/tools/build.py build/java-diff-mc-math-sin-build-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-signed-zero-preparation/tools/gate.py build/java-diff-mc-math-sin-build-<unique> build/java-diff-mc-math-sin-fixtures-<unique> build/java-diff-mc-math-sin-gate-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-signed-zero-preparation/tools/archive_results.py build/java-diff-mc-math-sin-build-<unique> build/java-diff-mc-math-sin-fixtures-<unique> build/java-diff-mc-math-sin-gate-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-signed-zero-preparation/tools/verify_results.py
```

The durable generated run is `results/generated-gate-v1/`; `results/SHA256SUMS` authenticates the durable results subtree. The gate covers Java-8 host raw-bit witnesses, q1/q7/direct/reopen for signed zero and prior sqrt, q1 sparse 65536-cell checkpoint/resume/reopen plus malformed/noncanonical and threshold controls, previous library regressions, raw71/471911 and capacity controls, and independent atomic root/Head/no-continuation checks for finite positive/negative, NaN, and positive/negative infinity.

## Source-derived root caveat

The inherited sparse-stage `baseline-pins.json` declares bootstrap root `7e17be...`. Recomputing the baseline's checked-in P2 `_bootstrapRoot` from its exact 97 images and `keccak256("JVMEVM:MC-RANDOM-CLASS-P2:BOOTSTRAP:1")` yields `7d5bb2...`, not that inherited declaration. This candidate does not perpetuate the stale value: it records the source-derived prior root and computes the candidate root `e8d268...` from the actual changed image-89 leaf. Both values and the discrepancy are explicit in `root-commitment.json`, source-invariants, and the archived proof for parent review.

This is a worker candidate, not profile acceptance. Parent must independently rebuild/gate it and alone replay the original program to measure the next exact input. No general `Math.sin`, full Minecraft startup, readiness, or `Done` claim is made.
