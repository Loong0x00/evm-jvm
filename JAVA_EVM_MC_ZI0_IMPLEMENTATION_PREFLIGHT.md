# ZI0 parent implementation preflight and freeze decision

Status: **ready to freeze bounded production implementation, NOT accepted ZI0**.
Runtime/transport still have to be implemented, embedded, independently tested and
accepted. AS0/VFS/core unchanged. No inflation/plain CRC/ClassLoader/MC startup.

## Independent baseline

Worker2bb841b0c integrateda00108e08, evidence archived6a65f64a8. Pinned parent
rebuild was byte-identical. Independent full run18.423s/269950976B sampled groupRSS,
exit0/no limits; every gas/root/counter of6 runs and all54 controls matched. Target
20554 entries/exact2100796B CD generated input4057736B made823 publications:
AS0create1+496append+seal1+indexCreate1+discover1+322scans+finish1. New-process
mid-index and separate FINAL reopens passed. Disk41449535B versus worker41449537B
is layout variation, not state encoding. Capacity32768/exact4MiB CD also passed.
Source9102B runtime/init9752B pins remain those of the disposable worker prototype.

Parent exact32MiB ZIP additionally exercised high packed name/local/data offsets
33554388/33554269/33554321 and actual EVM lookup. Pass1.166s/216977408B sampledRSS;
full AS0 append sum7289399396gas/max1830926, discover69091422, scan146700.
Evidence under `evidence/java-evm/zi0/persistence-preflight-2bb841b0c/` includes
source/driver/artifact/reports/manifests and parent max32m test. No server JAR input.

## Pure-Go Luna contribution, parent correction and replay

User-permitted `openai-codex/gpt-5.6-luna`/high successfully completed the scoped
pure-Go probe task d385a9197->9113e7a5b. This establishes actual use for this task,
not universal model reliability. Parent still owns acceptance. Terra remains only
registry-confirmed, not inference-tested. No Fast/priority/global setting changes.

The contribution added geometry-specific errors23/27, zero-owner/no-op observations,
actual name-bucket mismatch, OOG/retry, opaque binary names, bounds and max-TLV
fixtures. Parent reviewed it and strengthened four test details before counting
its own final replay:

- Positive-case oracle still allowed a valid ZI0Error instead of failing. Parent
  requires positive controls to return success; none failed in the final replay.
- Cached root/GetStorageRoot alone do not prove full rollback. Parent additionally
  computes the actual state root using StateDB.Copy().IntermediateRoot(true).
- Reaching SSTORE alone is weaker than confirming a changed write completed. A
  diagnostic next-opcode observation now confirms changed state BEFORE the later
  OOG, followed by exact post-revert root/slots/nonces/log equality BEFORE reload.
  This is rollback diagnosis only; no trace is recovered/published as success.
- The 'dense valid candidates' fixture had2048-byte spacing. Parent uses22-byte
  spacing across the maximum tail; gas is79233310, not the earlier69172720 sample.

Parent also corrected the zero-owner result's misleading rolled_back=true (the
unpublished CREATE actually succeeded), and describes the bucket mutation accurately
as isolated TEST-only memory state rather than a cryptographic hash collision.

The final parent-adjusted run passed **18.730s /277540864B** sampled groupRSS, exit0,
no limits. Seven measured runs,54 retained controls,12 additional probes; parent
code and all output are under
`evidence/java-evm/zi0/persistence-parent-probes/parent/`. Key results:

| control | EVM observation |
|---|---|
|max64 records: name256/comment1024 and256 zero-length TLVs in EACH extra|47225700 scan gas versus the one-TLV18.535M sample|
|dense actual EOCD ending candidates|exactZI0Error6,79233310gas|
|100000-gas scan after a completed changed SSTORE|OOG; actual trie root/slots/nonces/logs reverted, no host reload before valid retry; retry equals fresh binding|
|isolated nameIndex redirect to another record|exactZI0Error19/full-byte mismatch; original hit restored; no real hash collision claimed|
|stored comp AND plain adjusted to expose overlap/range|exact27 and23, not earlier method-size15|
|binary/NUL/nonASCII/dot/slash names|exact hits and distinct normalization-looking misses|
|entry/lookup bounds|exact31/32; existing CAS/unit10/11 controls retained|
|zero owner / at-end scans|accepted in disposable prototype; observations, NOT policy passes|

## Freeze choices, not grandfathered prototype gaps

JAVA_EVM_MC_ZI0_PLAN.md governs production. Require nonzero constructor owner1
before dependency checks and reject correctly-CASed at-end scans with11; do not
retain the prototype's zero owner or no-op work. Empty ZIP discover->finish works.
Keep exact20-entry ABI (18 functions,constructor,error), scalar diagnostics and
separate finalRoot; no public staging entry/lookup or measurement surfaces.

Keep the explicitly bounded ZIP64/preamble policy: reject structured records between
CD and EOCD by exact adjacency, sentinels/extra ID1, and for empty classic archives
only the locator marker at EOCD-20. Do not search opaque names/payloads or claim
full ZIP conformance. Metadata/ranges are not verified plaintext/CRC or class data.

Production Go transport is a NEW namespace doing ordinary AS0 upload and separate
ZI0 CREATE on one trie. No old store adoption, host page installer or parser. Every
mutation, including each AS0 append, publishes independently. Actual source/error/
metadata/code-pin/symlink/failure-publication guards must meet the frozen plan and
accepted AS0 precedent; disposable prototype shortcuts are NOT grandfathered.

All32MiB/8KiB/4096-read/32768-entry/4MiB-CD/64-unit/100M30s/1B120s/20min4GiB limits
remain unchanged. Largest measured discovery79.23M and scan47.23M provide evidence,
not an unconditional future-artifact gas bound. Final artifacts must pass again.
One Solidity writer and at most2 disjoint runtime/harness workers; parent independently
integrates/verifies16 groups. No acceptance from this freeze or worker completion.
