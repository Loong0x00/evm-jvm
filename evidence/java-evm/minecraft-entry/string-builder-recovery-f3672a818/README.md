# StringBuilder source-layout recovery (incomplete gate)

## Scope and basis

This records the local recovery attempt after the committed 395319-byte / 393216-byte failure at `9c101f757`. The fixed parent basis is `parent-89928ece8`; the stage remains the bounded Java-8 image85 StringBuilder profile. No original JAR/class/resource/world, sibling worktree, network, or host execution path was used.

The engine source repair is commit `f3672a818`; it outlines the existing post-VFS bootstrap assignment tail from `_prepare` into `_appendTailBootstraps` and calls a one-purpose StringBuilder materialization helper for slot 84. The strict source verifier derives this exact layout from the parent rather than accepting a broad replacement. It still checks all 84 parent image bytes, their order, the 542-byte image85 bytecode, raw replacement reservation, every fixed limit, and dynamic `keccak256(_bootstrapStringBuilder())` inside the runtime-derived full bootstrap root.

Commit `e71a98afe` fixes two gate-only staging paths (`root` and the renamed checkpoint diagnostic). Those fixes were required before the gate could reach EVM execution; they do not affect any contract source, artifact, or pin.

## Build result

The one full product build command was:

```sh
python3 evidence/java-evm/minecraft-entry/string-builder-preflight/tools/build.py \
  build/java-diff-mc-string-builder-build-f3672a818
```

It passed the strict source verifier and used solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer enabled/runs200, viaIR, Cancun, and metadata-off. `build-pins.json` records the resulting 386100-byte runtime, SHA-256 `a63dc6b0539158fc02ad8ec177e0a09745a34605a2ebb31b14cd899254e06066`, and Keccak `0c20ed49fe75dc3705c3849a3454cf795e079d695290d051493f5e76a7261d72`.

This is 9219 bytes smaller than the failed 395319-byte candidate and 7116 bytes below the unchanged 393216-byte cap. The coordinator remains 4146 bytes. No bootstrap root or limit commitment was precomputed or weakened.

## Generated-only gate outcome

Generated fixtures were made locally, then one substantive gate invocation began after the runtime fit. Its q1/q7/direct/reopen non-null StringBuilder control, bounded-null control, and no-use/uninitialized control all completed. Their command records and terminal heads are summarized in `gate-observed.json`.

The next `stringbuilder-oom` fixture failed during `startMain` with `LC0StateError(1,0)`. In the direct `startMain` path that selector/arguments can come only from the unchanged 1MiB checkpoint guards in `_encodeMachine` or `_commit`; the fixture has retained enough arrays to cross that cap. `gate-oom-start-refusal.json` and `gate-oom-finish.log` preserve the exact result. The resume attempt then correctly rejected the manifest because no initial checkpoint was published.

This gate is incomplete and was not retried. The candidate is **not accepted**. Any follow-up must redesign the OOM witness (or otherwise resolve the fixed-cap contradiction) before it can claim the complete generated gate; it must not relax the checkpoint cap or use this partial result as an acceptance substitute.

## Files

- `source-verification.log`, `engine-build.log`, `coordinator-build.log`, `build-console.log`: full product build evidence.
- `build-pins.json`: runtime/coordinator hashes and all preserved commitments.
- `fixture-summary.json`, `fixture-console.log`: generated-only fixture provenance.
- `gate-logs/`: exact command/exit records through the stopping assertion.
- `gate-observed.json`: normalized successful terminal heads and the failed start receipt.
- `source-pins.json`: source hashes and the source/harness commits.
- `SHA256SUMS`: integrity manifest for this archive.
