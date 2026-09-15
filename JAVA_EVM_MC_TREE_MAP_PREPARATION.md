# Java-on-EVM Minecraft bounded `TreeMap` preparation

## Measured blocker

The parent `String.lastIndexOf(String)` implementation in `parent-fe370c161` builds at386525/393216 and passes its generated gate. Fresh unchanged original30 advances to12002J/40I, then q7 and narrowed q1 atomically request exactly `java/util/TreeMap` at site4104/context80. The active frame is genuine `org/apache/logging/log4j/LogManager.<clinit>` classIndex4/methodIndex31 PC80. All1718 successful receipts verify canonically.

Parent-only bytecode inspection proves the immediate active surface is only:

```
new java/util/TreeMap
invokespecial java/util/TreeMap.<init>:()V
```

The following `ProviderUtil.hasProviders()` branch is false in the measured immutable resource package, so no `SortedMap` operation has yet been reached. This does not authorize fabricated provider results or broad map semantics.

## Strict scope

1. Append one Java-8-produced bounded `java/util/TreeMap` bootstrap image86 after the accepted85 images; preserve all85 prior images/order and reserve raw replacement.
2. Implement genuine ordinary guest construction and stable identity only. Do not claim ordering, `SortedMap`/`NavigableMap`, put/get/entrySet/lastKey, comparator, mutation, serialization or clone behavior before a measured active use.
3. The bounded image may expose only `<init>()V` and inherit Object. Its deliberate type/API limits must be explicit; omitted method/interface use must refuse honestly rather than fabricate map results.
4. Preserve bootstrap count86, raw30/262144, all fixed limits, runtime-derived commitments, optimizer200 toolchain, outlined post-VFS tail and runtime <=393216. Exact diagnostic class bound becomes116.

## Required generated-only gates

- parent-pinned reverse verifier, Java8 provenance, append-only first85 proof;
- q1/q7/direct/reopen/canonical constructor/non-null/stable-identity probe;
- uninitialized and raw replacement refusal controls;
- an explicit omitted `SortedMap`/mutation refusal control;
- all retained lastIndexOf/StringBuilder/System.err/failed-init/raw30/31/byte-boundary/EnumSet/queue/OOM controls;
- source build, runtime size/hashes, receipts and monitoring.

No original artifact access in candidates. Parent alone runs original30; no provider, logging-output, world or Done claim.
