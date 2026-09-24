# Generated-only `Integer.rotateLeft(II)I` preflight

This isolated P15 candidate implements only the measured Java 8 call
`java/lang/Integer.rotateLeft(II)I` at bootstrap image index 70. Its ordinary
`Code` body is compiled from:

```java
public static int rotateLeft(int i, int distance) {
  return (i << distance) | (i >>> -distance);
}
```

The EVM executes the Java `ishl`, `ineg`, `iushr`, and `ior` bytecodes; JVM int
shift semantics mask both distances to the low five bits. No host arithmetic,
lookup table, native binding, special dispatch, or hardcoded output is used.

## Exact basis and scope

- The semantic source is based on the accepted Java 8 `Integer.java` in
  `../integer-highest-one-bit-preflight/bootstrap/java/lang/Integer.java`.
  Before adding the method, the pinned Java 8 compiler rebuilt that source
  (`-source 8 -target 8 -g:none`). Removing only the compiler's existing
  61-byte Code-local `StackMapTable` metadata made the compiled 2,039-byte
  image byte-for-byte equal to accepted P14 image 70. Raw/stripped hashes and
  the equality check are in `prechange-image-verification.json`.
- The candidate stripped image is 2,087 bytes (SHA-256
  `8c166273089342e5bd5fba6a6c79b861d2a823a8941307a71695374b510def22`,
  Keccak-256 `a650a3f15565b8248e97233b6fe628abff4418eb54574c75fef46fad2680864f`).
  Javac confirms the `(II)I` body contains the expected ordinary shift/negate/
  unsigned-shift/OR/return opcodes.
- `tools/verify_source.py` byte-compares normalized Solidity to the accepted
  independent P14 engine. The only changes are the isolated P15 profile-domain
  labels and bootstrap Integer image 70. Exactly that one of 97 materialized
  image leaves changes; accepted `Object.hashCode` image 0 and the other 95
  images are unchanged. Global bindings 1–21, String-local 12, Math bindings
  18–21, packed-float and sparse codecs, authentication/COPY/transport, raw
  limits 71 / 471,911, and the 393,216-byte runtime cap remain pinned.
- The actual 97-leaf P15 root is recomputed from the candidate Solidity source,
  not copied from P14: `b64cac716a7a15e83cf5c66a19b7dece2af9b15feb7f46d43b65b1b94468a55d`.
  Ordered hashes and the domain hash are recorded in `root-commitment.json`.
- Engine runtime is 389,579 / 393,216 bytes. Full compiler/runtime pins are in
  `build-pins.json`; coordinator and canonical generated-only driver change
  only the isolated P15 domain and the exact runtime/address pins.

## Generated differential and retained gate

`fixtures/rotate-left-cases.json` is the deterministic signed-int input set;
`fixtures/IntegerRotateLeftOracle.java` invokes the host Java 8 implementation
only on those generated pairs. The oracle class is not bundled into the guest
ZIP. The generated guest fixture makes 97 ordinary static calls and saves each
result; the gate checks every 32-bit result against the independently produced
Java 8 raw value.

Coverage includes zero and nonzero signed operands, positive and negative
values, high-bit and alternating patterns, deterministic random pairs, negative
and large distances, ±32 / ±33, `Integer.MIN_VALUE`, and `Integer.MAX_VALUE`.
q1, q7, direct (q4096), and a new-process durable reopen agree at 1,265 Java / 3
internal steps. All three terminal machine roots are
`0x263fe1993afd496f916f3b95af91d7c7bfa2574ce71f65d0b21a03d68f37abb6`; the
opaque payload SHA-256 is
`4e83628b46027720d5c2a243ae58830a4b71f304ca2919310c71944cffc5fe6a`.

The full generated-only gate completed in **1,039.624441 seconds** (under the
1,200-second bound) and independently re-encoded **10,107 successful canonical
receipts** across 76 terminal receipt worlds. All generated ordinary calls use
the fixed LOCAL 1-billion-gas budget. It retains P14 Object identity/hash,
Integer, Math.sqrt/sin/asin/cos, sparse-array, packed `float[1024]` q1/q7/direct/
reopen, packed-array q1 continuation, malformed packed/sparse and old dense
wire controls, raw71 and 471,911/471,912-byte boundaries. Receipt hashes and
checkpoint/root/counter records are archived under `results/`.

The 471,911-byte probe remains a documented non-acceptance: under ordinary 1B
LOCAL gas it exhausts gas after reading the generated payload and before a
checkpoint is published. It is not evidence that a 471,911-byte checkpoint fits.

The first disposable gate attempt exposed a test-only mistake: its checkpoint
rehash helper still used the P12 machine-root domain, so a malformed sparse
case failed outer root validation (code 3) before reaching the intended codec
check. The helper was corrected to P15 and the entire gate was rerun with fresh
worlds. The failed attempt was not continued; its short diagnostic and cause are
preserved in `results/initial-gate-domain-correction.json`.

## Reproduction

Use fresh names for all ignored build output. `build.py` installs pinned npm
packages with `--offline` only; it does not contact a registry. The host Java
runs generated fixtures only.

```sh
STAGE=evidence/java-evm/minecraft-entry/integer-rotate-left-preflight
BUILD=build/java-diff-mc-integer-rotate-left-build-REPRO1
FIX=build/java-diff-mc-integer-rotate-left-fixtures-REPRO1
GATE=build/java-diff-mc-integer-rotate-left-gate-REPRO1
python3 "$STAGE/tools/build.py" "$BUILD"
NODE_PATH="$BUILD/npm/node_modules" python3 "$STAGE/tools/verify_source.py" --check
python3 "$STAGE/tools/generate_fixtures.py" "$FIX"
NODE_PATH="$BUILD/npm/node_modules" python3 "$STAGE/tools/gate.py" "$BUILD" "$FIX" "$GATE"
python3 "$STAGE/tools/archive_results.py" "$BUILD" "$FIX" "$GATE"
```

`results/gate-final/archive-index.json` and `SHA256SUMS` index the archived pins,
source verification, complete compressed gate summary, generated fixture
manifest, canonical receipt/checkpoint hashes, and q1/q7/direct equivalence
records. `archive_results.py` writes a fresh gate-specific subdirectory and
refuses to overwrite an existing run.

This is generated-only bootstrap-method evidence. It is **not** a replay of the
original Minecraft JAR, a logger/world/EULA test, a Minecraft `Done` result, or
standard-chain compatibility evidence. No original JAR, class, resource, world, network input, or failed original state is used or continued.
