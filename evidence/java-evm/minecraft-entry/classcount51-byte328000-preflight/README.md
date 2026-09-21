# Generated raw51 / byte328000 source stage

This generated-only capacity stage implements
`JAVA_EVM_MC_CLASSCOUNT51_BYTE328000_PREPARATION.md`. It derives exactly from
the accepted generated evidence at `parent-e883ec304`. It changes only raw
class count `50→51`, aggregate raw bytes `324338→328000`, and the read-only
checkpoint diagnostic class bound `144→145`.

All 94 ordered bootstrap images remain byte-identical and ordered. Global
native14, String-local binding11, exception kinds14, frames128,
selected-resource count1/4096, checkpoint1MiB, Head32768, compiler/toolchain,
and the runtime-derived bootstrap root remain pinned. The bootstrap root is
`7f7e1d7f3e44ffe70415e4075f7a94e02c2b1835e6c63b983f0d152d64d312c4`.

The only engine/coordinator/driver changes are the raw count, aggregate-byte
guards, committed limits tuple, fixed coordinator arrays/product count guards,
rebuilt code hashes, and diagnostic bound. The rebuilt engine is
`373596 / 393216` bytes (19620-byte headroom); coordinator is 5394 bytes.
`tools/verify_source.py` reconstructs each staged source from
`parent-e883ec304` with literal replacements and rejects bootstrap, semantic,
or extra binary changes.

The full gate uses trusted generated Java-8 fixtures only. It runs raw51
q1/q7/direct/reopen, raw52 refusal at the product/coordinator/engine layers,
exact 328000/328001 aggregate-byte boundaries, and inherited retained
controls direct/reopen. It completed under the fixed 1200-second whole-gate
bound with independently canonicalized receipts. Durable outputs are under
`results/`; `SHA256SUMS` covers every tracked stage file other than itself.

No original artifact/JAR/class/resource, genuine `ni` append/replay, provider
construction, factory execution, world, EULA, or Done input is read or
claimed. Parent alone owns genuine `ni` replay.

## Reproduction

From repository root with fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/classcount51-byte328000-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount51-byte328000-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount51-byte328000-preflight/tools/build.py build/java-diff-mc-classcount51-byte328000-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount51-byte328000-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount51-byte328000-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-substring-int-preflight/tools/generate_fixtures.py build/java-diff-mc-string-substring-int-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount51-byte328000-preflight/tools/gate.py build/java-diff-mc-classcount51-byte328000-build-repro-LOCAL build/java-diff-mc-classcount51-byte328000-retained-fixtures-repro-LOCAL build/java-diff-mc-string-substring-int-fixtures-repro-LOCAL build/java-diff-mc-classcount51-byte328000-gate-repro-LOCAL
```
