# Generated raw35 / byte268379 source stage

This generated-only capacity stage derives exactly from accepted raw34 parent
`parent-be5f9998e` (`e93b2a170`). The only runtime changes are raw selected
class count `34→35`, aggregate raw bytes `268053→268379`, and the read-only
checkpoint diagnostic class bound `122→123`.

All 88 bootstrap images, native13, String-local binding10, exception kinds14,
frames128, selected-resource count1/4096, checkpoint1MiB, Head32768,
compiler/toolchain, coordinator tail, and every other fixed limit are
parent-pinned. The engine is 393060 / 393216 bytes, retaining exactly 156 bytes
headroom; coordinator is 5394 bytes.

The generated gate proves raw35 q1/q7/direct/reopen equivalence (140 Java, 2
internal steps; epochs140/20/1), atomic raw36 refusal at driver/coordinator/
engine layers, exact aggregate268379 coordinator admission followed by the
ordinary engine reserve refusal, and atomic268380 coordinator rejection. The
two aggregate fixtures split inert padding across CountMain and Tail01 so every
individual generated class remains within the retained262144-byte DI0 input
bound (maximum219149); this prevents an unrelated transport bound from standing
in for the aggregate raw-package boundary.

The focused plus retained direct/reopen gate completed 96 rows, 347 commands,
and4498 canonical receipts in303.120 seconds (fixed cap1200). Only trusted
generated Java-8 sources are compiled. No original artifact, JAR, class,
resource, Provider construction, factory, world, or Done input is read or
claimed. Parent alone runs original35; no message formatting/provider factory/
world/Done claim is made here.

Reproduce with pinned local tools:

```sh
python3 evidence/java-evm/minecraft-entry/classcount35-byte268379-preflight/tools/build.py build/java-diff-mc-classcount35-byte268379-build-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount35-byte268379-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount35-byte268379-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount35-byte268379-preflight/tools/gate.py build/java-diff-mc-classcount35-byte268379-build-LOCAL build/java-diff-mc-classcount35-byte268379-fixtures-LOCAL build/java-diff-mc-classcount35-byte268379-gate-LOCAL
```
