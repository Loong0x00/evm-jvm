# Bounded `Object.hashCode()I` candidate (generated-only)

This stage adds exactly one bootstrap surface after the accepted P12 `Math.cos` work: ordinary Java 8 `java.lang.Object.hashCode()I`, implemented as:

```java
public int hashCode() { return System.identityHashCode(this); }
```

The native `System.identityHashCode(Object)I` global binding (binding 17) already existed. This adds no binding, heap identity/hash table, host hash, special VM dispatch, bootstrap class, or other `Object` method. Existing constructor, identity `equals`, and native `getClass` remain. Virtual calls use the guest wrapper and guest overrides; `String.hashCode()` keeps its existing implementation.

## Inputs, pins, and scope

- Basis: accepted independent P12 `parent-cd8122975`; its files are retained unchanged under the sibling evidence stage.
- Engine profile/domain: `MC-RANDOM-CLASS-P12`; this directory is a measured candidate, not a claim of wider JVM support.
- Exactly bootstrap image 0 changes; the other 96 materialized images, all 21 global native bindings, String-local binding 12, codecs, gas/checkpoint/head/frame limits, owner, address, and ABI/authentication/transport rules remain byte/pin-equivalent to P12 except for the engine runtime hash/length pin required by this image change.
- All 97 ordered bootstrap root leaves were rematerialized. Candidate root: `c0b02ab719751b297602c23385e7e0831ac1728fb8a9026fc86fafea1ade7970` (accepted P12 root was `a2fe7bacf0077f8dcc48b9da2f0ea2295401ca42e648aadf4e0fdcf6b11aa003`).
- Object image: 401 bytes; SHA-256 `ac898039bbd7f71df4c6553f6156c75465f41c1d1537e99c50a09aeee9eab138`; Keccak-256 `d08322f3721eccab25e9087ee347cd633e0cd3bd618b1ea8dc71c4e099732c37`.
- Engine runtime: 389,524 bytes (3,692 below the unchanged 393,216-byte cap); SHA-256 `4e5c10535f3a264e7215f490348091b3cd6959939848424fdf311801c79e7b53`; Keccak-256 `01c8208e069f173594b8458a5efc984981689e56e736ab70915fb98878eeb758`. Coordinator runtime is 5,394 bytes and changes only its engine code-hash pin. See `build-pins.json` and `results/build-pins.json` for complete compiler/runtime/limit pins.
- Java 8 compiler and differential oracle inputs are used only for locally generated fixtures. No official/original Minecraft JAR, class, resource, original world, or original checkpoint was opened or replayed. Generated fixture EVM worlds/checkpoints were produced/reopened for the retained P12 gates. No network access or host execution of original program code.

## Verification result

Source verification independently normalized the candidate engine against P12 and confirmed the only semantic image delta is bootstrap Object, all 97 root leaves match the recomputed candidate root, `System.identityHashCode` binding 17 is preserved, and the packed-float/sparse codec sources remain byte-identical. Candidate engine and coordinator compile with the pinned Solidity compiler and offline dependency tree.

The complete generated-only gate passed in 936.756920738 seconds, below its 1,200-second guard. It covered 73 generated worlds and 8,660 independently checked successful receipt records, with q1 and q7 resumable chains and q4096 direct controls. Canonical nested ABI/event, CP, receipt-counter, checkpoint, and head data are independently indexed in `results/verified-receipt-index.json.gz`; the compressed full gate summary, canonical receipt counters, generated-fixture manifest, source/build pins, and test-only q120 model report are also retained under `results/`.

Focused Object cases establish, without assuming nonportable OpenJDK identity-hash numbers:

- repeat identity hashes are stable; distinct generated Objects receive distinct observed identity hashes; null identity hash is zero;
- the `Object` wrapper and inherited subclass path return the same identity hash; guest subclass virtual override dispatch remains in force;
- virtual and direct `String.hashCode()` both return the Java 8 `"abc"` value 96354, independently of its identity hash;
- caught and uncaught null-receiver calls produce the expected guest NPE behavior (uncaught Java kind 6); q1/q7/direct machine roots and opaque payloads agree;
- omitted `Object.toString()` still fails as the same typed atomic unresolved-call refusal (`CallError` selector `0xd631c3a4`, first arguments `[3,7]`, unchanged root) for q1, q7, and direct execution.

Retained P12 generated controls pass, including packed-float/sparse-array oracle and malformed-refusal cases, `Math.sqrt`/`sin`/`asin`/bounded `cos`, retained String/Map.Entry/Integer/System/Properties cases, and the raw 71-class limit. The q120 host-Java oracle is test-only; it does not add a guest binding.

Boundary caveat: the 471,911-byte raw class bundle is read by the guest and coordinator acceptance is observed, but the fixed LOCAL 1-billion-gas call ceiling is reached before publishing a checkpoint/head (gas 984,570,381; prior head/root remain unchanged). This is an expected gas-ceiling refusal, **not** evidence that a 471,911-byte checkpoint fits the 1 MiB checkpoint cap. 471,912 bytes is rejected by the unchanged class-size/binding bound, also without head/root mutation.

This stage does not establish an original-program replay, logger initialization, Minecraft startup, EULA/world creation, `Done`, standard-chain deployment, broader Java compatibility, or full Minecraft readiness.

## Reproduction

From this repository root, use fresh names so no previous run is overwritten (the scripts reject existing output directories):

```sh
STAGE=evidence/java-evm/minecraft-entry/object-hash-code-preflight
FIX=build/java-diff-mc-object-hash-code-fixtures-REPLAY1
BUILD=build/java-diff-mc-object-hash-code-build-REPLAY1
GATE=build/java-diff-mc-object-hash-code-gate-REPLAY1
python3 "$STAGE/tools/generate_fixtures.py" "$FIX"
python3 "$STAGE/tools/build.py" "$BUILD" "$FIX"
python3 "$STAGE/tools/gate.py" "$BUILD" "$FIX" "$GATE"
python3 "$STAGE/tools/archive_results.py" "$BUILD" "$FIX" "$GATE"
```

`build.py` performs pre-build and post-build source/pin verification; it requires the already-cached pinned `solc` dependency and does not download dependencies. The scripts use `/usr/lib/jvm/java-8-openjdk` for trusted generated fixtures only. `gate.py` reproduces all retained P12 gates and has its own 1,200-second per-process watchdog. `archive_results.py` hashes/indexes successful generated-only receipt/checkpoint metadata and archives summaries; it does not modify runtime or invoke the EVM.
