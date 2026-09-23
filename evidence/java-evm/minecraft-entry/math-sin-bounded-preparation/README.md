# Bounded `Math.sin(double)` Q120 implementation candidate

This generated-only candidate implements existing global native binding 19 for finite binary64 `|x| <= 0x401921fb54442d18`. It preserves both raw signed-zero encodings, atomically refuses larger magnitudes, NaNs, and infinities with `MathSinProfileError(1, pc)`, and leaves native bindings 1–18, String-local binding 12, all 97 bootstrap images, and the sparse checkpoint format unchanged.

## Numerical kernel

The interpreter converts the guest IEEE bits directly to signed Q120 using integer significand/exponent fields. For the non-shortcut branch the input is a normal whose exponent field is 995–1025, so the scale is an exact left shift of 40–70 bits. It range-reduces using nearest-even `piQ = 4175892906503776358826876457663557747`, computes `x2 = roundEven(x*x / 2^120)`, and runs exactly 30 recurrence updates through the `x^61` term. Every signed division is nearest-even. A small input with magnitude at most `2^-28` returns its input bits: `|x - sin(x)| <= |x|^3/6` is below half an ulp there, including subnormals. Final Q120-to-binary64 conversion uses integer highest-bit normalization and nearest-even rounding.

The source documents the bounds: range-reduced `|xQ| < 2^122`, `|x2| < 2^124`, recurrence products `<2^246`, and accumulator `<2^127`, all below signed 2^255. There is no host math, precompile, lookup/table, guest output table, or unbounded guest-controlled loop in the execution path. These numerical claims are implemented by the Solidity helpers in `engine/MCEntryInterpreter.sol`; `verify_source.py` confirms that only the binding-19 dispatch and private kernel differ from the signed-zero baseline.

The source-derived ordered root from all 97 exact Solidity leaves is `e8d2682b12ee29790e98011eb4745d7f41706d085b11c649de02faffd633efac`; no image changed. The inherited `7e17be...` historical P1 root is stale and is retained only as an explicit caveat. Runtime is 386,037 bytes, below the unchanged 393,216-byte LOCAL cap.

## Verification and durable evidence

Reproduce from the repository root using unique `build/` names:

```sh
python3 evidence/java-evm/minecraft-entry/math-sin-bounded-preparation/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/math-sin-bounded-preparation/tools/verify_q120.py
python3 evidence/java-evm/minecraft-entry/math-sin-bounded-preparation/tools/generate_fixtures.py build/java-diff-mc-math-sin-fixtures-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-bounded-preparation/tools/build.py build/java-diff-mc-math-sin-build-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-bounded-preparation/tools/gate.py build/java-diff-mc-math-sin-build-<unique> build/java-diff-mc-math-sin-fixtures-<unique> build/java-diff-mc-math-sin-gate-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-bounded-preparation/tools/archive_results.py build/java-diff-mc-math-sin-build-<unique> build/java-diff-mc-math-sin-fixtures-<unique> build/java-diff-mc-math-sin-gate-<unique>
python3 evidence/java-evm/minecraft-entry/math-sin-bounded-preparation/tools/verify_results.py
```

The gate took 465.513 seconds and independently checked 3,769 canonical receipts. Actual EVM q1/q7/direct/reopen outputs include the genuine first nonzero input `0x3f1921fb54442d18`, its negative, both signed zeros, subnormal/normal and identity-threshold edges, values near pi/2, pi, and both signs of the inclusive two-pi magnitude bound, plus 34 mirrored sampled-grid points. Every sampled EVM double is within 1 ULP of its generated Java 8 `Math.sin` witness and each selected float cast matches exactly. The exact genuine positive output is `0x3f1921fb539ecf31`, with float cast `0x38c90fdb`.

`verify_q120.py` separately checks the test-only exact-integer model against all 65,536 generated Java 8 grid rows: 2,008 double outputs differ by one bit, maximum distance is 1 ULP, and no float casts differ. This is research/test-only evidence, not execution-path code or universal Java/ correctly-rounded equivalence.

The retained gate also covers `Math.sqrt`, sparse float[65536] q1/reopen/resume and malformed/noncanonical refusals, old library controls, native/root commitments, and raw71/471911 capacity probes. The latest durable generated gate is `results/generated-gate-v2/`, with 701 exact sine q1/q7/direct slice receipts and their checkpoints, heads, generated class bundles, runtime hashes, source/root proof, and SHA256 manifests. `generated-gate-v1/` is preserved as the earlier source-comment revision; the final v2 was rebuilt and gated again.

This is a worker implementation candidate only. The parent must independently rebuild and replay the unchanged original program. No original JAR/class/resource/world, EULA, provider, or Minecraft `Done` execution is included or claimed.
