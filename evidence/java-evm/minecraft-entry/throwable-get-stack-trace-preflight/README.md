# Generated image5 `Throwable.getStackTrace()` stage

This generated-only stage implements `JAVA_EVM_MC_THROWABLE_GET_STACK_TRACE_PREPARATION.md` from `parent-66b1622a2`.  It changes only the existing bootstrap image5, `java/lang/Throwable`: its new public `getStackTrace()` method allocates and returns a fresh non-null zero-length `StackTraceElement[]` on each invocation.  The Java-8 image is 772 bytes (`SHA-256 6ea5d86706a5ac3aabc7a7452f746bd9c3209483ee16f1c83948dbe7bd2a0d79`).

The retained constructors, `detailMessage`, `cause`, `getMessage`, `getCause`, and `printStackTrace` behavior stay in this image.  The bounded method does **not** expose captured frames, element class/method/file/line details, causes beyond the existing API, or suppressed exceptions.  `StackTraceElement` is the existing bootstrap leaf and is resolved without initialization.

The strict source verifier recompiles the image with Java 8, verifies its exact source/hex/hash, recomputes the ordered 94-leaf root, and compares the source against the parent engine.  Its candidate root is `43a87c0dfe115b957cac7c16049b2b54f15420dd57252957c100173f4a350525`; only leaf5 changes, while all other leaves remain runtime-derived.  No folded whole-root value or `DBOOT_THROWABLE` was introduced.

The clean parent replay stored in `results/` rebuilt everything in fresh ignored directories and passed the whole generated gate in 699.559 seconds (736 commands, 11,703 canonical receipts).  The focused q1/q7/direct/reopen executions agree at 39 Java and 2 internal steps, with epochs 39/6/1, identical machine root `0x6c2da6444f2245a177995dfee32f9b225d6510330253dd4ac653aa288d3c48c4`, and identical opaque checkpoint digest `c08a3b2bbfd273456d0709e8849f61a5955d8429c23fe2b868a985764350aca7`.  The dormant control leaves image5 uninitialized; a raw `Throwable` replacement atomically preserves the canonical `0x427cfac5` / `[6,1]` refusal.

All 94 bootstraps, diagnostic bound 144, raw limits 50/324338, 13 global native bindings, existing String-local binding10, exception kinds14, frame/checkpoint/Head limits, compiler settings, and the 393216-byte LOCAL runtime cap remain pinned.  The rebuilt runtime is 393145 bytes (71-byte headroom from the cap; baseline was 393007 bytes).  The raw50 and exact 324338/324339 boundary controls remain in the full gate.

No original artifact/JAR/class/resource, network input, provider/factory construction, Minecraft world, or Done behavior was read, run, or claimed.

## Reproduction

The stored parent replay is immutable: `tools/parent_replay.py` refuses to overwrite nonempty `results/`.  To make a new disposable reproduction from the repository root, choose fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/throwable-get-stack-trace-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/throwable-get-stack-trace-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/throwable-get-stack-trace-preflight/tools/build.py build/java-diff-mc-throwable-get-stack-trace-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/throwable-get-stack-trace-preflight/tools/generate_fixtures.py build/java-diff-mc-throwable-get-stack-trace-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/throwable-get-stack-trace-preflight/tools/gate.py build/java-diff-mc-throwable-get-stack-trace-build-repro-LOCAL build/java-diff-mc-throwable-get-stack-trace-fixtures-repro-LOCAL build/java-diff-mc-throwable-get-stack-trace-gate-repro-LOCAL
```
