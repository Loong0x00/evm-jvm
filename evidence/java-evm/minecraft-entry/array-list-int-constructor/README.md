# ArrayList(int) bootstrap size preflight — blocked

This is an isolated, append-only candidate against the parent `P28 raw75` engine. It is **not accepted**, has no deployable paired coordinator, and was not run in the EVM. No Minecraft/original-JAR replay, fixture execution, quota test, checkpoint inspection, or acceptance gate was attempted.

## Exact blocker

The pinned LOCAL384 build (`solc 0.8.30+commit.73712a01`, optimizer 200, viaIR, Cancun, metadata disabled) reports a deployed runtime of **394,435 bytes**. The unchanged fixed limit is **393,216 bytes**, so this minimal candidate exceeds the limit by **1,219 bytes**. The P28 raw75 parent runtime is 392,091 bytes; this append increases it by 2,344 bytes. No cap, old image, raw75 limit, or other profile limit was changed.

The candidate appends exactly two Java 8 bootstrap images after the 97-image tail: `AbstractList` (171 bytes, SHA-256 `8d1561a7648fa2da2150621be2b74b4a599efc57c039563502167770f1a76607`) and `ArrayList` (559 bytes, SHA-256 `76a02ffc33cd5749965629183f3f75b0ee9fb4adeb1d972fd6a444e56d39664d`). Its source grows the root to 99 leaves, reserves both binary names, and materializes them at the append-only tail slots. The source verifier reconstructs the candidate from the exact parent engine and verifies the two classfiles using the local Java 8 compiler.

`ArrayList(int)` eagerly creates `Object[initialCapacity]`, leaves `size` at zero, and checks negative capacity before allocation by constructing `IllegalArgumentException`. `add` and `iterator` are native declarations only to close the class's `Collection` method set; their intended behavior is refusal through the existing unbound-native path, but that and all constructor behavior remain **unexecuted/unverified** because the engine does not fit.

## Reproduction

From the repository root, with the pinned local/offline tooling:

```sh
python3 evidence/java-evm/minecraft-entry/array-list-int-constructor/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/array-list-int-constructor/tools/build_candidate.py build/java-diff-mc-array-list-int-constructor-repro
```

The first command must pass. The second intentionally exits nonzero after the pinned Solidity compilation and reports the exact fixed-cap refusal; it does not emit candidate artifacts or compile a coordinator. It uses only this stage, the tracked P28 parent engine source, the installed Java 8 compiler/runtime, and this checkout's pinned local `solc`/`js-sha3` modules. No network access is used.

No optimization was accepted as a substitute for fitting the measured candidate; the next step requires a smaller measured implementation within the existing limit or a parent-directed decision. No broader capability, original replay, or acceptance claim is made.
