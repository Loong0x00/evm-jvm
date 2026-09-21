# Generated `Integer.toString(int)` preflight

This generated-only preflight implements `JAVA_EVM_MC_INTEGER_TO_STRING_PREPARATION.md` from accepted `parent-12bfded16`. It changes only existing bootstrap slot 70, `java/lang/Integer`: public static `toString(int)` delegates exactly to retained guest `new StringBuilder().append(value).toString()`.

The Java 8 `-g:none` image is 1959 bytes after removing 61 bytes of parser-ignored `StackMapTable` metadata:

- SHA-256: `56b891f66fbab31669688a128b8a888291183461adb3aaf667aba394cd1455a8`
- Keccak-256: `d850fbfd897244a29a754d0c512a52689db64ecccab14e29e5debb4a09c14225`

No radix or unsigned overload is present. The strict verifier recompiles only this local guest source, verifies the 94 ordered bootstrap leaves from runtime functions, and proves only leaf 70 changes. The new domain is `MC-INTEGER-TO-STRING-P1`; runtime-derived bootstrap root is `acc183127fc38ae8594433310d91c91617814f764dc6d5407ffd4a3741a9f2c6`.

## Bounds and generated gate

The rebuilt engine is 367235 bytes, below the fixed 393216-byte local cap (parent baseline 367072); coordinator remains 5394 bytes. All 94 bootstraps, diagnostic 144, raw 50/324338, global native 13, String-local 10, exception kinds 14, 128 frames, 1 MiB checkpoint/32768-byte Head, 25M reserve, compiler settings, and LOCAL 1B call envelope remain pinned.

`results/` records one fresh generated-only gate: 457 commands, 12237 canonical receipts, and 798.433708 seconds, below the fixed 1200-second whole-gate limit. Each of MIN, `-1`, `0`, `123456789`, and MAX passes q1/q7/direct plus reopen with equal Java/internal counters, machine root, and opaque payload. Fixtures check exact text and two fresh non-interned guest strings. An unreferenced root leaves Integer uninitialized; valid Java-8 radix and unsigned call sites retain atomic `CallError(3,4)` and `CallError(3,1)` refusals.

## Reproduction

From repository root, with fresh ignored build paths:

```sh
python3 evidence/java-evm/minecraft-entry/integer-to-string-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/integer-to-string-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/integer-to-string-preflight/tools/build.py build/java-diff-mc-integer-to-string-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-to-string-preflight/tools/generate_fixtures.py build/java-diff-mc-integer-to-string-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-to-string-preflight/tools/gate.py build/java-diff-mc-integer-to-string-build-repro-LOCAL build/java-diff-mc-integer-to-string-fixtures-repro-LOCAL build/java-diff-mc-integer-to-string-gate-repro-LOCAL
```

No original artifact, JAR, class, resource, Minecraft world, or Done behavior is read, executed, or claimed. This is generated-only preflight evidence; parent alone owns genuine replay.
