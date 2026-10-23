# P49 parent-verified LinkedHashMap construction subset

Parent independently rebuilt Java8/Solidity/coordinator/driver, verified real private field state and high index263 arrays+clones, raw put/inherited refusals, separate-process reopen and a fresh original125 run. No ordered mutation implementation is claimed.

The worker metadata incorrectly omitted the `JVMEVM:` DBOOT prefix and labeled init-code lengths as runtime sizes. Parent rejected those claims and preserved failed assertions/reports. Actual114-image root `302c3174aec4caf25a3bcd8d3fc6990cd9fd18d4e79e5701c92680e4151f00c9`; runtime429953B SHA732cb0e440706a312cd438a613fc874b132a3d43ccb3122c7e100b36c42d10b4, coordinator runtime5411B. Guest code and EVM charging were unchanged by these metadata corrections. Source-derived root verification is now strengthened to use both actual DBOOT literals and all ordered leaves.

Parent proof: `../parent-linked-hash-map/`; root document `JAVA_EVM_MC_LINKED_HASH_MAP_PARENT_PREFLIGHT.md`. Worker receipts below retain their original execution provenance; their runtime bytes already match the independently built code.

---

## Historical worker candidate description

# LinkedHashMap P49 construction-only candidate

This candidate appends one generic Java 8 `java/util/LinkedHashMap` image at bootstrap slot 113 to the accepted P48 source set. It provides only genuine `LinkedHashMap()` construction, the `HashMap()` superclass chain, private-final `accessOrder=false`, empty-state observers/backed empty view inherited from P48, and an explicit unbound native `put(K,V)` guard.

No ordered storage, mutation/get API, extra constructor, LinkedHashMap Node/entry helpers, HashMap/superclass change, EVM semantic/ABI/storage/codec/quota/gas change, original Minecraft input, or acceptance claim is included. See `INHERITED_API_AUDIT.md` and `results/gate-summary.json`. `results/manifest.json` pins the candidate's sources, generated class image, builds, fixtures, and selected actual EVM receipts. Candidate status remains **awaiting independent parent review**.
