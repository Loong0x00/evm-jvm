# Generated raw49 / byte322481 source stage

This generated-only capacity stage implements
`JAVA_EVM_MC_CLASSCOUNT49_BYTE322481_PREPARATION.md`. It derives exactly from
the accepted `String.equalsIgnoreCase(String)` evidence at `parent-e73e45fce`.
It changes only selected raw-class count `48→49`, aggregate raw bytes
`314425→322481`, and the read-only checkpoint diagnostic class bound `141→142`.

All 93 ordered bootstrap images, including the bounded Java-8
`String.equalsIgnoreCase(String)` code at String root-leaf26 and `Objects`
image93, remain byte-identical and ordered. Native13, String-local binding10,
exception kinds14, frames128, selected-resource count1/4096, checkpoint1MiB,
Head32768, compiler/toolchain, runtime-derived bootstrap root, and every other
fixed limit remain pinned. The fresh-domain root is computed from those 93
leaves, never embedded as a substitute interpreter root.

The only runtime/coordinator/driver changes are the fresh domain and identity,
raw count, aggregate byte guards, committed limits tuple, fixed coordinator
arrays, product count guards, and diagnostic bound. The rebuilt engine is
`391507 / 393216` bytes (1709-byte headroom); coordinator is5394 bytes. The
fresh runtime-derived 93-image root is
`4523c44ef38d2d4a1def3a40f47085984f2dcdabc3823925c539c30a2fa1edc1`.

The generated gate executes trusted Java-8 fixtures only: raw49
q1/q7/direct/reopen, raw50 refusal at the product/coordinator/engine layers,
exact 322481/322482 aggregate-byte boundaries, and retained equalIgnoreCase
controls. It completed in 688.3972290509846 seconds (709 commands, 11601
canonical receipts), below the fixed 1200-second whole-gate cap.

No original artifact/JAR/class/resource, provider construction, factory
execution, world, or Done input is read or claimed. Parent alone owns the
genuine ReflectionUtil append and any factory execution or accelerated replay.

## Reproduction

From repository root with fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/classcount49-byte322481-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount49-byte322481-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount49-byte322481-preflight/tools/build.py build/java-diff-mc-classcount49-byte322481-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount49-byte322481-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount49-byte322481-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount49-byte322481-preflight/tools/gate.py build/java-diff-mc-classcount49-byte322481-build-repro-LOCAL build/java-diff-mc-classcount49-byte322481-fixtures-repro-LOCAL build/java-diff-mc-classcount49-byte322481-gate-repro-LOCAL
```
