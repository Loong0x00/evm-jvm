# Generated `Integer.highestOneBit(int)` preflight

This generated-only preflight implements `JAVA_EVM_MC_INTEGER_HIGHEST_ONE_BIT_PREPARATION.md` from `parent-bbecbd532`. It changes only existing bootstrap slot 70, `java/lang/Integer`, by appending public static `highestOneBit(int)` with the Java 8 signed 32-bit bit-smear implementation. Zero returns zero, positive values select their highest set bit, and all negative values return `MIN_VALUE`. No `rotateLeft` or other Integer API is added.

The independently rebuilt Java 8 `-g:none` image is 2039 bytes after removal of the existing 61-byte parser-ignored `StackMapTable` metadata:

- SHA-256: `5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd`
- Keccak-256: `1a698ef9f803879a7f45c3613a679295cd1db22528c2c0e986fc4f9a6b845ba9`

`tools/verify_source.py` recompiles just this generated Java source, proves exactly one ordered bootstrap leaf changes (slot 70), and checks its runtime-derived 94-leaf root `57722a32ab679ecdca73bd05c5cb633aa5984568e531a0dcbf2651bc0dac997c`. Raw62/376794/diagnostic156, native16, String-local11, all other bootstrap leaves and limits remain pinned. The rebuilt engine is 377409 bytes, below the 393216-byte cap; coordinator remains 5394 bytes.

## Generated gate

`results/` records a fresh generated-only gate: 198 seconds wall time, 197.760432 seconds measured whole-gate time, 523 commands, and 1722 canonical receipts, below 1200 seconds. The Java 8 host oracle and guest probe cover `0,1,2,3,4,7,8,0x12345678,MAX_VALUE,MIN_VALUE,-1` plus deterministic values. q1/q7/direct/reopen agree. Retained controls run direct/reopen. Valid raw Integer, malformed raw Integer, and omitted `rotateLeft` each refuse atomically.

## Reproduction

From the repository root with fresh ignored `build/` directories:

```sh
python3 evidence/java-evm/minecraft-entry/integer-highest-one-bit-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/integer-highest-one-bit-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/integer-highest-one-bit-preflight/tools/build.py build/java-diff-mc-integer-highest-one-bit-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-highest-one-bit-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-integer-highest-one-bit-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-highest-one-bit-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-integer-highest-one-bit-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-highest-one-bit-preflight/tools/gate.py build/java-diff-mc-integer-highest-one-bit-build-repro-LOCAL build/java-diff-mc-integer-highest-one-bit-retained-fixtures-repro-LOCAL build/java-diff-mc-integer-highest-one-bit-focused-fixtures-repro-LOCAL build/java-diff-mc-integer-highest-one-bit-gate-repro-LOCAL
```

No original artifact, JAR, class, resource, network input, Minecraft replay, provider/factory behavior, world, EULA, or Done behavior is read, executed, or claimed. Parent genuine replay remains deferred.
