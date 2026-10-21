# LOCAL Java 8 `Math.min/max(double,double)` stage

This append-only stage starts from the P32 `identity-hash-map-int-constructor`
engine source (`039abb41…`) and changes only the materialized Java 8
`java.lang.Math` image and its actual root-leaf commitment. The image adds
ordinary guest-code `min(DD)D` and `max(DD)D`; it adds no native binding or
platform class. Existing Math `(II)I` min/max bytecode and native `sqrt`, `sin`,
`asin`, and `cos` declarations/bindings remain byte-identical. The root has 100
images in the original order; only Math at its existing slot changes.

The new methods preserve Java 8 IEEE-754 behavior: first-NaN payload/order,
NaNs in either operand, signed-zero min/max, infinities, subnormals, ties, and
finite binary64 boundaries. Negative zero selection uses ordinary guest
`1.0 / operand` and comparisons; all comparisons, division, branching, and
returns execute as Java bytecode in the interpreter. The Math class is rebuilt
with pinned local JDK 8 (`javac -g:none -source 8 -target 8`), and the engine
source verifier checks its exact bytes, actual Keccak root, prior method byte
identity, the exact two-method append, and all other materialized bootstrap
images.

Generated-only fixtures store actual EVM `long[]` raw result bits in the guest
checkpoint. The harness compares each bit against a read-only local Java 8
oracle; oracle outputs are not included in any EVM bundle. The 24-pair special
edge witness runs at q1/q7/q65536/q4096 and is reopened in a distinct process.
A deterministic 256-pair raw-bit matrix runs at q65536/q4096. The positive
checks cover signed zeros, quiet/signaling and signed NaN payloads/order,
positive/negative infinities, normal/subnormal transitions, extrema, ties, and
seeded arbitrary binary64 patterns. Existing ArrayList/IdentityHashMap,
Math-int, sqrt/sin/asin/cos, Object, Integer, packed/sparse, exact raw150 and
coordinator controls remain in the gate. Unsupported `Math.abs(double)` and raw
`java.lang.Math` replacement remain atomic refusals.

Pinned profile: LOCAL runtime ceiling 1,048,576 bytes; independent checkpoint
ceiling 1,048,576 bytes; raw150 / 1,063,930-byte limits; 100 bootstraps; 21
global native bindings; String-local binding 12. No budget was increased by
this stage. The test gate starts at 1,000,000,000 gas per EVM call and 1,200
seconds; any measured test-only shortage is preserved and expanded coherently,
and an expanded run is explicitly not labeled ordinary1B. No EVM opcode gas,
consensus, state schema, packed/sparse layout, or accepted profile was changed.

Run from the repository root:

```sh
python3 evidence/java-evm/minecraft-entry/math-double-min-max/tools/run_gate.py RUN_ID
```

Latest generated-only run: `runs/p33-final3-ordinary/` (pinned in `pins.json`),
starting at ordinary1B per-call gas / 1,200-second test wall budget. Its run
report, fixture/oracle manifest, direct q schedules, separate-process reopen,
coordinator route, opaque q1 checkpoint, source hashes, and build logs are
archived together. Earlier failed/harness-packaging attempts are retained in
separate run directories; none is overwritten.

This generated-fixture stage is not an untouched Minecraft replay or a general
Java claim. The delegated worker did not access original Minecraft JARs,
classes, resources, worlds, receipts, parent evidence directories, sibling
worktrees, or network inputs, and did not host-execute original code.
