# P59 source-only audit

## Scope and verification

- Worktree: `/home/user/evm-jvm/linked-hash-map-put`, branch `java-linked-hash-map-put`, HEAD `d1744f0eafc95e9e20d7892be171e36cd87e1485` (matches assigned base).
- Read-only snapshot: `evidence/java-evm/minecraft-entry/linked-hash-map-put-source-base-p58/`.
- `source-manifest.json` says 18 approved files, accepted guest commit `ae2bc90d30aaebd4b50f5eba47765816164afeb0`. A local SHA-256/byte-count check passed all 18, with zero unmanifested files (the manifest itself is the 19th tree file).
- Snapshot is source-only: nine Java source files, canonical driver, coordinator source/JSON/build, engine source/JSON/build, pins, and root helper. No original Minecraft JAR/classes/resources/worlds/receipts and no parent/performance-review material were present or read.

## Relevant accepted Java facts observed in the snapshot

- `LinkedHashMap` is the constructor-only class with real `HashMap()` super-call, `accessOrder=false`, and an explicitly unbound native `put` override. Removing that override would permit unordered inherited insertion and is not acceptable.
- `HashMap` has package-visible inherited `table`, `entrySet`, `size`, `modCount`, `threshold`, and final `loadFactor`. Its implementation's private static final `Node<K,V>` is not an extension point. Preserve the accepted source/image and do not relax compiler/private stubs.
- `HashMap.put` uses key `hashCode`, Java 8 spread, and incoming-key `equals` on hash collisions; its own bucket order is not LinkedHashMap insertion order. Existing treeification path can refuse. `HashMap.hashCode`, `equals`, and most map operations are explicit unbound refusals.
- Existing `HashMap.EntrySet` is private, cached through inherited `entrySet`, and its iterator is a bucket-order iterator over private `Node`. It cannot be safely repurposed for subclass-owned entries. The typed `toArray(T[])` Java source has a short-array refusal before writes, then iterates/casts/stores and null-terminates the first remaining position; it does not touch later target positions.
- Source-only snapshot metadata confirms the accepted `LinkedHashMap` image 113 baseline is 431 bytes, SHA-256 `746398af42137bb424040c85113cdd5f1296d29e983e0e819f320f2c108ddc3f`, and independently reproduced Java8 `-g:none`.
- Other snapshot Java inputs are compile context only. Their accepted images remain fixed; none are to be recompiled into the runtime as replacements.

## Design consequence

A narrow implementation can preserve all accepted old images other than image 113 by maintaining genuine ordered entry nodes in subclass-owned state, overriding `put`, `entrySet`, and `hashCode`, and adding at most three ordinary Java helper images for entry/view/iterator. This deliberately does not claim to populate inherited HashMap buckets. Every other inherited state-dependent operation must remain an explicit refusal boundary. The detailed proposal and its open approvals/gates are in `PLAN.md`.

This section records the initial read-only audit. Subsequent approved implementation and candidate-only generated execution are recorded in `PLAN.md` and `RESULT.md`; the accepted P58 source snapshot itself remains unchanged.
