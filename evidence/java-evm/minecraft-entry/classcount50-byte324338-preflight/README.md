# Generated raw50 / byte324338 source stage

This generated-only capacity stage implements
`JAVA_EVM_MC_CLASSCOUNT50_BYTE324338_PREPARATION.md`. It derives exactly from
the generated raw49/byte322481 source evidence at
`classcount49-byte322481-preflight`. It changes only selected raw-class count
`49→50`, aggregate raw bytes `322481→324338`, and the read-only checkpoint
diagnostic class bound `142→143`.

All 93 ordered bootstrap images remain byte-identical and ordered. Native13,
String-local binding10, exception kinds14, frames128, selected-resource
count1/4096, checkpoint1MiB, Head32768, compiler/toolchain, runtime-derived
bootstrap root, and every other fixed limit remain pinned. The fresh-domain
root is computed from the same 93 leaves, never embedded as a substitute
interpreter root.

The only runtime/coordinator/driver changes are the fresh domain and identity,
raw count, aggregate byte guards, committed limits tuple, fixed coordinator
arrays, product count guards, and diagnostic bound. The rebuilt engine is
`391507 / 393216` bytes (1709-byte headroom); coordinator is5394 bytes. The
fresh runtime-derived 93-image root is
`8e3ce62aaaa9a765172319ceffe9747baf2252c3e3b86947e38ab411bdc8c367`.

The generated gate executes trusted Java-8 fixtures only: raw50
q1/q7/direct/reopen, raw51 refusal at the product/coordinator/engine layers,
exact 324338/324339 aggregate-byte boundaries, and retained controls. It must
complete under the fixed 1200-second whole-gate cap with canonical receipts.

No original artifact/JAR/class/resource, provider construction, factory
execution, world, or Done input is read or claimed. Parent alone owns the
genuine `ReflectionUtil$PrivateSecurityManager` append and any class/factory
execution or accelerated replay.

## Reproduction

From repository root with fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/classcount50-byte324338-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount50-byte324338-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount50-byte324338-preflight/tools/build.py build/java-diff-mc-classcount50-byte324338-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount50-byte324338-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount50-byte324338-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount50-byte324338-preflight/tools/gate.py build/java-diff-mc-classcount50-byte324338-build-repro-LOCAL build/java-diff-mc-classcount50-byte324338-fixtures-repro-LOCAL build/java-diff-mc-classcount50-byte324338-gate-repro-LOCAL
```
