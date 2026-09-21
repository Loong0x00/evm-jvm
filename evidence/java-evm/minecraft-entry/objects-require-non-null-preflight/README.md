# Generated `Objects.requireNonNull(Object,String)` image93

This generated-only stage implements
`JAVA_EVM_MC_OBJECTS_REQUIRE_NON_NULL_PREPARATION.md`. It appends exactly
bootstrap image93, Java-8 `java/util/Objects`, after the fixed 92-image tail.
The 385-byte image has a private constructor and only generic
`requireNonNull(T,String)`: it returns the exact non-null reference and null
throws the retained guest `NullPointerException()` image. It does not claim
message retention because that NPE image exposes only `()V`; no other
`Objects` API is present.

The bootstrap root is dynamically calculated inside the engine from all 93
ordered image leaves (`keccak256(abi.encode(DBOOT,h))`), not embedded as a
root literal. The source verifier recomputes the fresh-domain root
`415b737bc5780358c7bb1d8a8e1c9e27cff1a72ec9c2d177e76f5da831a515f3`.
No additional commitment was needed; Object and every pre-existing leaf are
byte-for-byte inherited.

Only bootstrap count `92→93` and read-only checkpoint diagnostic bound
`140→141` change. Raw limits stay `48/314425`; native13, all remaining
limits, compiler/toolchain, and coordinator capacity arrays remain pinned.
The rebuilt runtime is `390985 / 393216` bytes; the 391172-byte baseline is
recorded unchanged as required by the preparation.

The generated gate checks q1/q7/direct/reopen exact-reference and caught-NPE
paths, dormant image93, raw replacement refusal, and omitted one-argument
overload refusal, alongside retained generated controls. It uses only trusted
generated Java-8 sources. It does not read or execute original artifacts,
worlds, provider construction, factory construction, or Done behavior.

## Reproduction

From repository root with fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/objects-require-non-null-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/objects-require-non-null-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/objects-require-non-null-preflight/tools/build.py build/java-diff-mc-objects-require-non-null-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/objects-require-non-null-preflight/tools/generate_fixtures.py build/java-diff-mc-objects-require-non-null-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/objects-require-non-null-preflight/tools/gate.py build/java-diff-mc-objects-require-non-null-build-repro-LOCAL build/java-diff-mc-objects-require-non-null-fixtures-repro-LOCAL build/java-diff-mc-objects-require-non-null-gate-repro-LOCAL
```
