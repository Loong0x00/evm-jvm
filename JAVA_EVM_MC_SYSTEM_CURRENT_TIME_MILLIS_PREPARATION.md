# Java-on-EVM Minecraft bounded System.currentTimeMillis preparation

Accepted `parent-033e6ff8f` runs unchanged original38 with genuine StatusData to60584J/50I in19 successful LOCAL4.2B/q4096 blocks. Exact blocker is StatusData.<init> PC5 invoking `System.currentTimeMillis()J` solely to populate a status timestamp.

Replace only bootstrap image44 System to add a deterministic bounded LOCAL clock returning long zero. This is a stable epoch value for repeatable EVM replay; no host/block/wall-clock fidelity or monotonicity claim. Preserve existing System APIs/initialization,91-image order/runtime-derived root,raw38/285489,diagnostic129,native13,and all limits/toolchain/semantics. Runtime<=393216 (baseline393157,59B headroom); verified semantics-preserving cleanup only, no commitment weakening. Focus long zero q1/q7/direct/reopen and retained controls<=1200s canonical receipts. Worker no originals; parent accelerated replay. No formatted status/provider factory/world/Done claim.
