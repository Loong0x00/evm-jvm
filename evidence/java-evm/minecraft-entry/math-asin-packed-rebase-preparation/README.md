# P9 Math.asin + accepted P6 packed-float rebase (candidate)

Status: **generated-only candidate; pending independent parent rebuild, replay, and acceptance**. This is deliberately not a completion or Minecraft-readiness claim. No original server/JAR/class/resource/world/EULA input was read or executed, and the failed P8 checkpoint is not used as continuation state.

The candidate is reconstructed from the exact accepted P6 packed-float engine source. `tools/verify_source.py` enforces normalized byte-identity with P6 except for the narrowly transferred global native-20 `Math.asin(D)D` bounded Q120 kernel; the only changed bootstrap image is exact Java 8 `java.lang.Math` image 89. Packed-float and sparse codecs, all other bootstrap images, native bindings 1–19, transport/authentication, and resource limits are intended to remain unchanged. See `results/source-invariants.json` and `root-commitment.json` for computed source/image/root commitments.

## Reproduce generated-only worker gate

From the repository root, with Java 8 at `/usr/lib/jvm/java-8-openjdk` and the pinned EVM build prerequisites installed:

```sh
python3 evidence/java-evm/minecraft-entry/math-asin-packed-rebase-preparation/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/math-asin-packed-rebase-preparation/tools/build.py build/java-diff-mc-math-asin-p9-build-local
python3 evidence/java-evm/minecraft-entry/math-asin-packed-rebase-preparation/tools/generate_fixtures.py build/java-diff-mc-math-asin-p9-fixtures-local
python3 evidence/java-evm/minecraft-entry/math-asin-packed-rebase-preparation/tools/gate.py build/java-diff-mc-math-asin-p9-build-local build/java-diff-mc-math-asin-p9-fixtures-local build/java-diff-mc-math-asin-p9-gate-local
```

The generated gate invokes its canonical receipt verifier at the end. Each output name is intentionally fresh and must not already exist. Archive successful output with `tools/archive_results.py <build-dir> <fixture-dir> <gate-dir>`; `tools/verify_results.py` checks the resulting archive. `results/generated-gate-p9/` retains the worker-generated gate summary, exact fixture bytes, all report/receipt JSON in a compressed archive, canonical receipt verifier output, build artifacts and selected terminal/continuation checkpoints. Recreate disposable build/world directories rather than treating archived checkpoints or this worker run as independent acceptance.

## Scope and limits

Generated Java 8 fixtures exercise asin edges and refusals, genuine packed `float[1024]` values, packed malformed cases, prior sparse arrays and malformed sparse cases, old Math/library controls, and retained raw/boundary controls. The worker gate reports 6,112 canonically checked public receipts in 680.184 seconds. The engine runtime is 388,632 bytes under the unchanged 393,216-byte cap. The Q120 test-only comparison covers 17,066 generated inputs, observes maximum 1 ULP (472 one-ULP differences), and exact float casts for sampled rows; it is not a global Math conformance claim.

The measured P8 LOCAL4.2B OOG is historical diagnostic evidence, not this candidate's input or baseline. This candidate does not alter gas, step, byte, class, memory, or checkpoint quotas. A prior generated attempt failed only at the final canonical-receipt step because worker3 build pins still named the P6 engine address; that nonpassing invocation and error are preserved under `results/nonpassing-attempts/`. The P9 address pins were corrected and the complete worker4 gate rerun from fresh worlds. Parent independent replay is still required before any acceptance or unchanged-original replay. No original-program workload result is implied.
