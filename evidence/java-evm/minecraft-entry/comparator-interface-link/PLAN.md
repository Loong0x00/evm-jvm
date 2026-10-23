# P45 Comparator interface append — bounded implementation record

P45 appends only a minimal Java 8 `java/util/Comparator<T>` interface image after P44's 107 bootstrap images. The image has `Object` as its superclass, is public/abstract/interface, and exposes the generic abstract SAM `int compare(T,T)` plus the Java 8 abstract `equals(Object)` declaration. It deliberately does not provide `reversed`, `thenComparing*`, natural-order/static helpers, or fabricated method results. Those remain unsupported/refused. No comparator implementation or comparison is performed by host code or a native binding.

P45 reserves the raw `java/util/Comparator` name even if input bytes equal the bootstrap image. Guest-provided concrete implementations must be ordinary classfile implementations; bridge and inherited interface dispatch are not hard-coded. The new bootstrap index is 107; indices 0–106 are expected to remain byte/order identical to P44. Derived diagnostic combined inventory is 150 raw images + 108 bootstrap images = 258 classes (indices 0–257); it is not a new raw-class quota. Comparator[] metadata's expected descriptor is `[Ljava/util/Comparator;` and encoding `0x201`. Existing uint8 raw coordinator count, uint16 engine checkpoint class index, ABI/storage fields and all quotas stay unchanged.

The engine bootstrap domain and coordinator package/class/selected-resource/VM domains are versioned P45. Coordinator `ENGINE_CODEHASH` binds the newly built P45 runtime. No coordinator ABI/storage change is intended.

## Scope and exclusions

This task only covers the Comparator bootstrap/link capability and generated-only test preparation. No official Minecraft input, original class/resource/world/receipt, other worktree, network, or push is permitted. Parent owns original-entry replay. Do not run the frozen original replay here. No interpreter opcode/heap/codec/ABI/storage/native-binding/cap change is allowed unless a measured blocker is escalated first.

## Required checks

1. Verify source-base manifest and all nine lengths/SHA-256 values before editing.
2. Fresh pinned solc engine and coordinator builds, then hash/ABI/storage audit.
3. Confirm P44 image prefix and new Comparator class bytes/root; compile Java 8-only generated concrete implementation/interface fixtures.
4. Fresh genuine geth-EVM q1/q7/coarse and fresh-process checkpoint equivalence, including custom compare outcomes, generic bridge/type/null outcomes, interface assignability, high Comparator[] index 257, raw150+108 metadata, and atomic typed refusal for omitted helpers/raw platform replacement.
5. Keep original Minecraft replay and all original evidence exclusively parent-owned.

No count/budget enlargement is authorized. If an actual finite test limit prevents a gate, preserve that failure and request a scoped continuation rather than silently changing the cap.
