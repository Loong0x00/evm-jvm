# Bounded `TreeMap` constructor generated evidence

Source commit `9e599cec1` appends only bootstrap slot 85 (`java/util/TreeMap`) to
accepted parent `fe370c161`.  The image was produced by the pinned Java-8
compiler with `-source 8 -target 8 -g:none`; it is 132 bytes,
`c203bc1cf3e4f7d9901b49f0415e10e0aa6331eb99c366e24f68b6fc2a60e067`, has
`java/lang/Object` as its only superclass, no interfaces or fields, and only
`<init>()V`.

The source-only verifier pins all six parent inputs and proves that all 85
prior image bytes/order are unchanged. It also proves the sole append, the
raw replacement reservation, class-count/diagnostic updates, fixed limits,
optimizer200/viaIR settings, and the retained outlined post-VFS tail. The
source build produced a 386844-byte engine under the 393216-byte local cap
(6372-byte headroom); exact compiler and artifact hashes are in `pins.json`.

The generated-only gate passed in 187.99393193097785 seconds: 2606 canonical
receipts in 71 successful q1/q7/direct/reopen worlds and 228 recorded
commands (227 successful; the one exit-2 raw31 driver boundary is expected and
asserted). `TreeMap` constructor identity has equal q1/q7/direct machine root
`0xf1ec9f41dd8e0dc35e6634b0df9f3cb9c2e5d0a6b357374ce3872f039593b382`,
34 Java and 2 internal steps, and matching opaque checkpoint payload hash.
The no-use root keeps slot 85 uninitialized. A raw replacement is rejected
before guest execution. The omitted `put` member stops as EVM `CallError`
selector `0xd631c3a4`, words `[3,13]`, with an unchanged root; the separately
named omitted `SortedMap` stops as canonical missing-class selector
`0x555db429`, diagnostic `java/util/SortedMap`, with an unchanged root.

`generated-gate-summary.json` and `canonical-receipts.json` preserve all
retained String.lastIndexOf/StringBuilder/System.err/failed-init/raw30/raw31/
byte-boundary/EnumSet/queue/OOM results. `monitor.json` preserves the complete
per-command gate timing and explicitly records that no external RSS sampler
was available. The diagnostic files preserve the focused TreeMap outcomes.

Reproduce only with local pinned inputs (no network):

```sh
python3 evidence/java-evm/minecraft-entry/tree-map-constructor-preflight/tools/build.py \
  build/java-diff-mc-tree-map-constructor-build-9e599cec1
python3 evidence/java-evm/minecraft-entry/tree-map-constructor-preflight/tools/generate_fixtures.py \
  build/java-diff-mc-tree-map-constructor-fixtures-9e599cec1
python3 evidence/java-evm/minecraft-entry/tree-map-constructor-preflight/tools/gate.py \
  build/java-diff-mc-tree-map-constructor-build-9e599cec1 \
  build/java-diff-mc-tree-map-constructor-fixtures-9e599cec1 \
  build/java-diff-mc-tree-map-constructor-gate-9e599cec1
```

This is bounded generated-only evidence. It does not access or run original30,
any Minecraft artifact, provider behavior, logging output, a world, or Done.
It does not claim `Map`, `SortedMap`, `NavigableMap`, ordering, comparators,
mutation, get/put/entrySet/lastKey, serialization, clone, or a broader JVM.
