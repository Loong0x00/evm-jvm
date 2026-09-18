# Generated raw34 / byte268053 source stage

This generated-only capacity stage derives exactly from accepted Iterable parent
`parent-cc433baf7` (`6032de1ac`). The only runtime changes are raw selected
class count `33→34`, aggregate raw bytes `262158→268053`, and the read-only
checkpoint diagnostic class bound `121→122`.

All 88 bootstrap images (including Iterable and the replacement Collection),
native13, String-local binding10, exception kinds14, frames128,
selected-resource count1/4096, checkpoint1MiB, Head32768, compiler/toolchain,
coordinator tail, and every other fixed limit are parent-pinned. The engine is
393060 / 393216 bytes, retaining exactly 156 bytes headroom; coordinator is
5394 bytes.

The generated gate proves raw34 q1/q7/direct/reopen equivalence (136 Java, 2
internal steps; epochs136/20/1), atomic raw35 refusal at driver/coordinator/
engine layers, exact aggregate 268053 coordinator admission followed by the
ordinary engine reserve refusal, and atomic 268054 coordinator rejection. The
two aggregate fixtures split inert padding across CountMain and Tail01 so every
individual generated class remains within the retained 262144-byte DI0 input
bound (maximum219010); this prevents an unrelated transport bound from standing
in for the aggregate raw-package boundary.

The focused plus retained direct/reopen gate completed 96 rows, 347 commands,
and 4494 canonical receipts in299.275 seconds (fixed cap1200). Only trusted
generated Java-8 sources are compiled. No original artifact, JAR, class,
resource, Provider construction, factory, world, or Done input is read or
claimed. Parent alone appends the genuine class and reruns original34.

Reproduce with pinned local tools:

```sh
python3 evidence/java-evm/minecraft-entry/classcount34-byte268053-preflight/tools/build.py build/java-diff-mc-classcount34-byte268053-build-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount34-byte268053-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount34-byte268053-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount34-byte268053-preflight/tools/gate.py build/java-diff-mc-classcount34-byte268053-build-LOCAL build/java-diff-mc-classcount34-byte268053-fixtures-LOCAL build/java-diff-mc-classcount34-byte268053-gate-LOCAL
```
