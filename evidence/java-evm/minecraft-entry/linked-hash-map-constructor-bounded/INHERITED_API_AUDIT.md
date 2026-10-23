# LinkedHashMap P49 inherited API audit

The only added image is the ordinary Java 8 `java.util.LinkedHashMap<K,V>` leaf at ordered bootstrap slot 113. It extends the accepted P48 `HashMap<K,V>` image. It contains only its genuine generic class signature, `serialVersionUID`, the private-final `boolean accessOrder`, `LinkedHashMap()`, and one explicit unbound native override `put(K,V)`.

## Constructor state

- Java 8 source and classfile are included. `javap -p -s -c` shows `LinkedHashMap()` invokes `HashMap.<init>()`, then writes `false` to `accessOrder`, then returns.
- The exact accepted P48 HashMap source initializes only `loadFactor` to `DEFAULT_LOAD_FACTOR` (0.75f); `table`, `entrySet`, `size`, `modCount`, and `threshold` remain Java-default null/zero. The no-argument HashMap constructor does not allocate a table. No HashMap source or image was modified.
- A fresh genuine EVM guest run completed the LinkedHashMap constructor chain and tested empty size/isEmpty, cached empty entrySet, its empty iterator/NoSuchElementException, and same-target typed `toArray`. This establishes successful constructor execution and its observable empty subset. The private field values are established from the executed classfile plus the exact P48 HashMap source; no new reflection/accessor API was added.
- The omitted `head`/`tail` ordered links and full field layout are intentionally not claimed. `accessOrder=false` is the sole LinkedHashMap state field in this construction-only class.

## Dispatch and refusal boundary

- `put(K,V)` is explicitly declared `native` and deliberately unbound. Generated EVM calls through a `LinkedHashMap` receiver with LinkedHashMap-, HashMap-, and Map-typed references each terminate at an atomic raw `CallError(4,13)`. Therefore the ordinary guest `HashMap.put` body cannot populate a LinkedHashMap through virtual/interface dispatch.
- The `LinkedHashMap(int)` overload is absent; a generated request raw-refuses as `CallError(3,6)` before committing a Java step.
- Raw replacement of the reserved `java/util/LinkedHashMap` image raw-refuses as `BootstrapProfileError(1,1)`.
- P48 HashMap's ordinary `size()` and `isEmpty()` report its genuine empty state. Its ordinary cached `entrySet()` and helper iterator are retained; `EntrySet.size/isEmpty/iterator`, `EntryIterator.hasNext/next`, and typed `toArray(T[])` describe the empty view. `next()` raises the accepted `NoSuchElementException`. For this profile, these remain truthful because no admitted mutation can add an entry.
- The P48 HashMap implementations of all other map surface remain unchanged: its own `put(K,V)` guest body is hidden by the subclass override; native/unbound `get`, contains operations, putAll/remove/clear/keySet/values, Object equals/hashCode/clone, default Map operations (`getOrDefault`, `forEach`, `replaceAll`, `putIfAbsent`, conditional remove/replace, compute variants, merge), EntrySet mutations/content/equality/hash/ordinary Object-array conversion/stream surfaces, and iterator.remove remain raw refusals. No method receives a fabricated constant or fake object result.
- `Object` identity semantics and full ordered storage/insertion/access-order behavior are not claimed. No LinkedHashMap mutation, remove/get, int/map/access-order constructor, Node/helper, superclass, HashMap, ABI, heap/codec, gas/quota, coordinator-wire, or engine execution semantic was added.

## Bounds and high-index proof

P48 limits remain fixed: 150 raw classes / 1,063,930 raw bytes, 21 global bindings, String-local 12, 8,192 arrays, 4,096 objects, 262,144 elements, 12,545 handles, 2 MiB checkpoints, 25,000,000 gas reserve, 1,000,000,000 ordinary call gas, 1 MiB runtime, 128 frames, and the existing JVM/internal step limits. Coordinator `classCount` remains `uint8` and its four raw-class arrays remain `[150]`; no raw-class count widening was made.

The generated high-index EVM fixture contains exactly 150 raw classes and reaches a terminal, fresh-reopened EVM result after creating and testing `LinkedHashMap[]`. With all 114 bootstrap images, the LinkedHashMap leaf is class index 263; the accepted array base `0x100` yields metadata `0x207`. The EVM `instanceof LinkedHashMap[]` test succeeds. This is an actual EVM result, not merely a source arithmetic claim; the input ZIP contains generated test classes only.
