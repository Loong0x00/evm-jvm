# Deterministic `System.currentTimeMillis` generated-only gate

This LOCAL, generated-only stage starts from `parent-033e6ff8f`. It replaces
only bootstrap image44 (`java/lang/System`) in the existing 91-image order.
`System.currentTimeMillis()J` is ordinary Java 8 bytecode (`lconst_0; lreturn`)
and deterministically returns `long` zero. It is not native: global native
binding count remains 13. It has no host, block, wall-clock, or monotonicity
claim.

The existing `System` fields, initialization, `arraycopy`, security getter,
property API, `err`, and all other image APIs are unchanged. The exact source
rebuilds to 967 bytes, SHA-256
`d10707987a9b7935e1c87a6a5fc5f574ffbc42f3cd82a629d20291dffa0487bf`.
The strict verifier reconstructs the engine from the parent by replacing only
its domain commitments and this image; it also recomputes the 91-leaf
runtime-derived root. It permits no other interpreter source delta.

The reproducible build is 393123 bytes, below the unchanged 393216-byte cap
(baseline 393157). The source change contains no size cleanup; the 34-byte
reduction is the pinned compiler's literal-layout result. Raw38/285489,
diagnostic129, native13, selected resource 1/4096, CP/Code/frame/checkpoint/
Head limits, compiler, and gas/reserve limits remain pinned.

The focused fixture invokes the clock twice, requires both guest long values to
be zero and equal, then terminates normally. It has no host Java oracle because
host time is expressly outside the contract. q1/q7/direct/reopen produce the
same machine root and opaque checkpoint payload. The retained generated-only
controls and canonical receipt verifier also pass in 522.248 seconds, within
the fixed 1200-second gate limit.

No original artifact, JAR, input class, resource, StatusData, formatted status,
provider factory, world, or Done claim is used here. Parent-owned accelerated
unchanged-original replay is deliberately outside this stage.

Reproduce from repository root:

```sh
python3 evidence/java-evm/minecraft-entry/system-current-time-millis-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/system-current-time-millis-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/system-current-time-millis-preflight/tools/build.py build/java-diff-mc-system-current-time-millis-build-LOCAL
python3 evidence/java-evm/minecraft-entry/system-current-time-millis-preflight/tools/generate_fixtures.py build/java-diff-mc-system-current-time-millis-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/system-current-time-millis-preflight/tools/gate.py build/java-diff-mc-system-current-time-millis-build-LOCAL build/java-diff-mc-system-current-time-millis-fixtures-LOCAL build/java-diff-mc-system-current-time-millis-gate-LOCAL
```

`results/` preserves concise generated-only build/gate/canonical evidence; all
large build worlds are disposable under ignored `build/`.
