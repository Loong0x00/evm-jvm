# Generated raw37 / byte282358 source stage

This generated-only capacity stage derives exactly from the accepted raw36
capacity evidence at `9c0ebbb5f`. The only runtime changes are selected raw
class count `36→37`, aggregate raw bytes `281175→282358`, and the read-only
checkpoint diagnostic class bound `126→127`.

All 90 bootstrap images and positions, native13, String-local binding10,
exception kinds14, frames128, selected-resource count1/4096, checkpoint1MiB,
Head32768, compiler/toolchain, coordinator layout, and every other fixed limit
are parent-pinned. The engine remains exactly `393208 / 393216` bytes; the
coordinator remains 5394 bytes.

The generated gate proves raw37 q1/q7/direct/reopen equivalence (148 Java, 2
internal steps; epochs148/22/1), atomic raw38 refusal at driver, coordinator
`MR0Error(2)`, and widened-coordinator engine `LinkError(1,38)` layers.
Exactly282358 aggregate raw bytes is coordinator-admitted and reaches the
ordinary engine reserve refusal;282359 is atomically rejected by coordinator
`MR0Error(12)`. The aggregate fixtures split inert padding across CountMain
and Tail01 so every generated class remains within the retained262144-byte DI0
input bound (maximum230532), preventing an unrelated transport bound from
standing in for the package-byte boundary.

The focused plus retained direct/reopen gate completed 109 rows, 380 commands,
and4623 canonical receipts in311.549 seconds (cap1200). Only trusted generated
Java-8 sources are compiled. No original artifact, JAR, class, resource,
StatusMessage, Provider construction, factory, world, or Done input is read or
claimed. Parent alone appends/runs genuine StatusMessage.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/classcount37-byte282358-preflight/tools/build.py build/java-diff-mc-classcount37-byte282358-build-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount37-byte282358-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount37-byte282358-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount37-byte282358-preflight/tools/gate.py build/java-diff-mc-classcount37-byte282358-build-LOCAL build/java-diff-mc-classcount37-byte282358-fixtures-LOCAL build/java-diff-mc-classcount37-byte282358-gate-LOCAL
```
