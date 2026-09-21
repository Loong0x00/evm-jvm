# Generated `StringBuilder.append(int)` preflight

This generated-only preflight implements `JAVA_EVM_MC_STRING_BUILDER_APPEND_INT_PREPARATION.md` from `parent-6d49b4e57`. It changes only bootstrap slot 84 (the 85th image), `java/lang/StringBuilder`. The public guest `append(int)` emits exact signed decimal text for every Java `int`, including `-2147483648`, and returns the same builder. It uses only retained guest `append(char)` and `String` paths: non-negative input is moved into the negative range, then a recursive negative-domain helper emits digits. This avoids `Integer`, native formatting, host formatting, and `MIN_VALUE` negation overflow.

The Java 8, `-g:none` image is 1097 bytes after removal of parser-ignored `StackMapTable` metadata:

- SHA-256: `a3d2543ce4401a36011be7bdd8e24ef9ee475f5361c615ab8964456c94728020`
- Keccak-256: `e1bef25751c230c7a77ec819c98879e7bab61414b0448348955383e118ae691a`

There are no `append(long)` or `append(Object)` methods. Their generated controls atomically retain ordinary missing-member refusals `CallError(3,8)` and `CallError(3,9)`, respectively. The existing capacity/growth model is not expanded.

## Root and bounds

The strict verifier recompiles the guest source, checks the exact image/hash, independently recomputes the ordered 94-leaf root, and compares the candidate interpreter source byte-for-byte with the immediate parent except for the new domain and the one StringBuilder literal. Only leaf 84 changes; `Object`, every other leaf, and the aggregate root remain runtime-derived. No whole-root or Object folding is present.

- domain: `MC-SB-APPEND-INT-0001`
- ordered bootstrap root: `876bf37291d10bc755d30f52c07f2a2fcf122f331a2e2c3302f2cea03bb4ec9d`
- engine: 367072 / 393216 bytes (26144-byte LOCAL headroom)
- coordinator: 5394 bytes
- retained: 94 bootstraps, diagnostic bound 144, raw 50 / 324338, 13 global native bindings, String-local binding 10, 14 exception kinds, 128 frames, 1 MiB checkpoint/32768-byte Head, 25M reserve, compiler/toolchain settings, and LOCAL 1B call envelope.

The private fixed-length guard in `_bootstrapStringBuilder` is unreachable (`bytes.length` cannot be `uint256.max`) and exists solely to prevent a `viaIR` literal duplication; it does not alter guest behavior.

## Parent replay

`results/` is one immutable clean parent replay. It rebuilt artifacts, regenerated only trusted Java fixture sources, and ran the entire generated gate in fresh ignored directories:

- full gate: 865.708077 seconds, below the 1200-second limit
- gate commands: 443
- canonical receipts: 14349
- focused q1/q7/direct/reopen witnesses: MIN, `-1`, `0`, `123456789`, MAX, and existing-prefix `-42`

For each focused value, q1, q7, and direct finish with equal Java/internal counters, machine root, and opaque checkpoint digest; the six direct terminal Java-step counts are 3431, 983, 782, 2826, 3131, and 1211. The retained controls—including raw50/raw51, exact 324338/324339 byte boundaries, old bootstraps, no-init, raw replacement, and omission controls—also passed and are covered by the canonical receipt record. The q1/q7 sweep is deliberately concentrated on the new six signed witnesses; retained controls use direct/reopen checks within the finite 1200-second gate.

The tracked replay record contains build pins, source-verification output, fixture and gate summaries, canonical receipt verification, root commitment, summary, and a manifest with hashes and disposable build paths. `tools/parent_replay.py` refuses to overwrite a nonempty `results/` directory.

## Reproduction

From the repository root, use fresh ignored build paths:

```sh
python3 evidence/java-evm/minecraft-entry/string-builder-append-int-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/string-builder-append-int-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/string-builder-append-int-preflight/tools/build.py build/java-diff-mc-string-builder-append-int-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-append-int-preflight/tools/generate_fixtures.py build/java-diff-mc-string-builder-append-int-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-append-int-preflight/tools/gate.py build/java-diff-mc-string-builder-append-int-build-repro-LOCAL build/java-diff-mc-string-builder-append-int-fixtures-repro-LOCAL build/java-diff-mc-string-builder-append-int-gate-repro-LOCAL
```

No original artifact/JAR/class/resource, network input, provider/factory execution, Minecraft world, or Done behavior was read, executed, or claimed. This is preflight evidence only, not a Minecraft startup or general-JVM acceptance claim.
