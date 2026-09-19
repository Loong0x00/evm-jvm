# Bounded Java 8 `StringBuilder(int)` source stage

This generated-only stage derives from `parent-7227a13b1` /
`thread-local-get-preflight`. It replaces **only bootstrap slot 84**
(`java/lang/StringBuilder`) with a 624-byte Java 8 `-g:none` image, SHA-256
`57eac8ab607a23fbb0a06a6af655321b7cf634b3d8c448d4c36fbaac99994fd9`.

The retained bounded representation has no separately observable spare
capacity: `value.length` is logical content length. The ordinary `(I)V`
constructor therefore executes guest bytecode that stores `new char[0]` for
all nonnegative capacities; `0`, `1`, and `255` all begin empty and append at
index zero. On negative input it executes ordinary `newarray char` with the
negative count, so the existing interpreter raises catchable guest
`NegativeArraySizeException`. No host StringBuilder, host capacity policy, or
native binding participates.

The existing `()V`, `append(String)`, and `toString()` Code remains in the
same image. `capacity`, `ensureCapacity`, `setLength`, `append(int)`, and all
other members are absent and refuse through ordinary member resolution.

All 90 image positions remain ordered. `root-commitment.json` independently
records the root derived at runtime as `keccak256(abi.encode(DBOOT, h))`:
`842464491035a9f67034b5c943f785230649c0d5c59e66532a91826192bc5945`.
Raw37/282358, diagnostic127, native13, the resource pipeline, compiler,
frames, heap, VFS, checkpoint/Head, EVM gas policy, and all other limits stay
pinned. The measured engine is 392934 / 393216 bytes (282 bytes headroom); the
parent baseline was 392834. Coordinator remains 5394 bytes.

The trusted generated fixture gate covers q1/q7/direct/reopen for capacities
0, 1, 255 and -1, plus retained controls. It completed 430 commands in
357.671 seconds (cap 1200) and independently verified 5294 canonical receipts.
The three nonnegative fixtures each reached 171 Java/2 internal steps at
q1/q7/direct epochs 171/25/1; the caught negative fixture reached 16/3 at
16/3/1. Omitted `capacity`, `ensureCapacity`, `setLength`, and `append(int)`
all reject atomically as `CallError(3,pc)` with no Head.

This stage never opens an original artifact, JAR, class, resource, checkpoint,
or world. It makes no setLength, ThreadLocal.set, provider/factory, world, or
Done claim. Parent alone reruns unchanged original37 and measures the q7 gas
boundary.

Reproduce with pinned local tools:

```sh
python3 evidence/java-evm/minecraft-entry/string-builder-capacity-constructor-preflight/tools/build.py build/java-diff-mc-string-builder-capacity-build-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-capacity-constructor-preflight/tools/generate_fixtures.py build/java-diff-mc-string-builder-capacity-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-capacity-constructor-preflight/tools/gate.py build/java-diff-mc-string-builder-capacity-build-LOCAL build/java-diff-mc-string-builder-capacity-fixtures-LOCAL build/java-diff-mc-string-builder-capacity-gate-LOCAL
```
