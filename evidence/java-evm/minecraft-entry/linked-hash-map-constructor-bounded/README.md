# LinkedHashMap P49 construction-only candidate

This candidate appends one generic Java 8 `java/util/LinkedHashMap` image at bootstrap slot 113 to the accepted P48 source set. It provides only genuine `LinkedHashMap()` construction, the `HashMap()` superclass chain, private-final `accessOrder=false`, empty-state observers/backed empty view inherited from P48, and an explicit unbound native `put(K,V)` guard.

No ordered storage, mutation/get API, extra constructor, LinkedHashMap Node/entry helpers, HashMap/superclass change, EVM semantic/ABI/storage/codec/quota/gas change, original Minecraft input, or acceptance claim is included. See `INHERITED_API_AUDIT.md` and `results/gate-summary.json`. `results/manifest.json` pins the candidate's sources, generated class image, builds, fixtures, and selected actual EVM receipts. Candidate status remains **awaiting independent parent review**.
