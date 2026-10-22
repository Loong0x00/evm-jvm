# NavigableMap link-only slice (P43 source base)

## Scope

Implement the exact measured missing `java/util/NavigableMap` interface link for the original Guava dependency. Starting point is the verified source-only P43 baseline in `../navigable-map-source-base-p43/` (base `b4b50fe3bf0b9d70be99a64a3563431c24e49aec`, runtime SHA256 `1cc023e3613138f6e943e049e5b69c0acee01f3500c8ffdb60d236bfe9058584`, 106 images/root `f9bc0a2e1368e55ca1e9b8f04ce5addf0d8d2427ce73c9996a05c7a1fddec670`). All nine source-manifest files were checked for exact byte length and SHA256 before work began.

Append one genuine Java 8 public abstract interface image `java/util/NavigableMap<K,V>` extending the existing link-only `SortedMap<K,V>` marker. It adds no methods and makes no claim of NavigableMap API behavior. The existing SortedMap image and all existing bootstrap images remain byte-for-byte unchanged and in the same order. Add a canonical mirror at derived image index 106; raw input classes remain a separate prefix and raw cap stays 150. The combined derived-class count at raw150 is 257, with highest image index 256.

Wire the new bootstrap into root authentication and class preparation, and reserve `java/util/NavigableMap` in the actual raw-class namespace guard. No new native, dispatch behavior, API surface, quota, engine protocol, or coordinator change is in scope. Any method call outside the empty interface surface must follow existing JVM linkage/refusal behavior; no fabricated return values.

## Index-width audit

Coordinator `classCount`/binding indexes count only raw decoder bindings, not derived engine bootstrap images; they stay uint8 and raw150. Engine checkpoint class count and frame class indexes are serialized as two bytes. Audit actual engine casts/caches before testing index 256; only opcode/constant-pool tags may be uint8. Do not migrate schemas or quotas.

## Required tests and evidence

- Fresh genuine Java 8-generated class image and classfile flag/name/superinterface/signature verification.
- Compare all 106 old bootstrap bytes/order and recompute the 107-leaf root; independently authenticate deployed engine/coordinator artifacts.
- Actual fresh EVM tests for interface hierarchy, type checks/cast, a raw-name collision refusal with atomic latest head/root, and omitted API refusal.
- Representable exact raw150 / derived257 execution, including index256 interface resolution and checkpoint reopen in a distinct process.
- q1/q7 and coarse execution equivalence for machine/VFS/heap/counters; retained Function/regex/clone smoke where feasible.
- Build/vet/source audit. Preserve each failure and only commit scoped code, generated fixtures, and selected durable results. No original Minecraft execution or original inputs are included.

## Resource policy

Finite 1B per-call gas and 1200-second outer process budget initially. A measured shortage may be doubled coherently with the failed attempt preserved and separately labeled. Ordinary 2B budget or quota changes are not allowed.
