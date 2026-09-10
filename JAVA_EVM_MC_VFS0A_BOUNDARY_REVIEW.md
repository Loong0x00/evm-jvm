# FINAL VFS0a independent boundary/rollback review

Status: **independent boundary review PASS; no runtime fix requested**. Parent remains
sole final acceptance/production-fix owner. Reviewed integration commit
`40e86bb21a6a04994f550713c4ae189857281a76`; this is not a Minecraft startup,
EULA, listener, connectivity, standard deployment, or `Done` claim.

## Exact reviewed artifact

The embedded runtime and artifact deployed bytecode are byte-identical:

- runtime: **293010 bytes**, SHA256
  `78d57a051311538c13ed6b60a59ceab5800722bf49ec9e9f3683bb23521739c9`
- EVM code hash: `3cca94879feafc98d3e50a0169751b06e56695384b88ad68245a6de84840cb73`
- Solidity source: 507564 bytes, SHA256
  `168a965ad0aa43eb3216d97cf38169da63d0a4294ea9f9651ab86ddd0d0c04c3`
- combined artifact JSON: 619948 bytes, SHA256
  `6dc889b2461775397d7cdbdffd0c82c9fa1f8e9680ddb3a5b06af270f2a549b8`
- ABI file: 18953 bytes, SHA256
  `16346751accb944db73a8a8b33bee6923c9ccabca1896af41f4926a2895e6520`

A pinned solc 0.8.30, optimizer200, viaIR, Cancun, metadata-off `build.js --check`
reproduced the same source/runtime hashes and 293010-byte size under the explicit
327680-byte LOCAL ceiling. Compiler warnings include the expected EIP-170/EIP-3860
oversize warnings; no standard CREATE compatibility is inferred.

The independent trusted Java8 review fixture is embedded only in
`boundary_review_test.go`: source 3825 bytes/SHA256
`4a3cac388ed57c9c2cc2e47d3641c46e0bcf943bcec2dda60f9ce429e4571a8e`;
root class 3126 bytes/SHA256
`bae73df7e6a40303c8b567ec5b36fe5d899c3b962dfd56e2d5843b5001f50cf8`.
It is compiled with Java8 `-source 8 -target 8 -g:none`. Production Go receives
only opaque raw class/seed/checkpoint bytes.

## Independent boundary results

All controls below execute the reviewed runtime through EVM `start`/`resume`.
Checkpoint assertions use the bounded parent TEST-only typed wire decoder; decoded
bytes are never rehashed and submitted as live resume authority.

| PLAN groups | Independent result |
|---|---|
| 11 | Five separate failed-open controls (missing input, missing output parent, directory input, read-only output, ENOTDIR input) returned exact Java messages and left inode/descriptor/logical-byte counts unchanged. Descriptor, file, aggregate, inode, and seed quota failures exposed no success tuple and did not publish/change a head. |
| 13 | Genuine wrapper Code established byte sign `-1`, single-write low-8 masking (`-1 -> 255`, `0x123 -> 35`), null-before-bounds/closed, bounds-before-closed, and zero-length-before-closed behavior for input and output. |
| 14 | Two writers produced a zero-filled gap; a stale reader retained its cursor over truncation; an append descriptor wrote at the file's current EOF after a later truncating open. Final inspected bytes were exactly `[81,82]`. Existing final-artifact corpus gap/stale/append controls also passed. |
| 17 | Ordered seed roots and VFS roots changed on seed reordering; lexical collision reverted `VFS0aProfileError(1,0)`; 16 seeds and exactly 65536 seed/file bytes passed; 65537 reverted exact seed quota; an actual read-only `/ro/input` was read successfully. |
| 18 | Exactly 64 EVM wire inodes passed. A Java `mkdirs` from 63 to 64 passed; a two-component `mkdirs` attempt hit exact requested65/limit64 and atomically failed. A separate seed-creation 65 boundary gave the same quota. |
| 19 | Exactly 32 descriptors passed and all remained typed phase3 CLOSED records with zero bind depth/PC. The 33rd open crossed calls because of the unchanged 4096-unit call ceiling, reverted exact requested33/limit32, and retained the prior issued head. This is genuine closed-record/no-GC evidence. |
| 20 | One file at exactly65536 passed; +1 reverted per-file quota `(4,65537,65536)`. Aggregate exactly65536 passed with one byte from a read-only seed plus65535 newly written; +1 reverted aggregate quota `(5,65537,65536)`. |
| 21 | Genuine write and read transfers of4096 passed. 4097 reverted `VFS0aProfileError(3,pc)` at actual invoke PCs37 (write) and38 (read). |
| 22 | Actual combined Java heap (two guest byte arrays) plus VFS seed state emitted an **exact 1048576-byte checkpoint**. Measured shape:130950 primitive cells plus119 seed data bytes; gas293631394. The same Java shape with one additional VFS byte reverted exact `LC0StateError(1,0)` and published nothing. This is live EVM-issued evidence, not a padded/rehashed blob. |
| 26 | A 1-gas resume safely OOGed with no tuple/checkpoint/log/head change; a 25,000,000-gas start hit exact reserve `LC0ControlError(7)`; retry from the exact old issued root then advanced one epoch. Disk durability injection likewise returned diagnostic gas only, preserved the old durable head across reopen, and allowed old-root retry. |
| 27 | The independent append/gap/stale root at one-call4096/internal4096 and q1/internal1 had identical machine root, VFS root, result, and total counters. q1/internal1 used612 calls for608 JVM +4 internal steps, within the VFS-only4096-slice and ordinary4096-total-unit limits. |
| 29 | Runtime address/store marker remained VFS0a-specific; wrong-owner reopen and an IOE0 store marker were rejected without modifying the store. Final package copied-state inspect/provenance and old-store tests passed. Accepted IOE0 independently passed its package control. |
| 30 | Injected post-blob durability failure leaked only nonzero diagnostic gas—no SliceResult, checkpoint, log, or revert payload—and did not move the in-process or reopened durable head. |
| 31 | A disk checkpoint taken runnable after a native four-byte write was closed and resumed to the same terminal state after reopen. A separate OS child process reopened that issued checkpoint and completed it. The final package also passed its distinct true-new-process pending-truncate/bind-corridor test on this artifact. |

Additional raw bundle controls accepted four distinct valid classfiles and rejected
five with exact `LinkError(1,5)`. An exact65536-byte malformed raw input crossed the
aggregate-byte gate and then failed exact `ClassError(1,0)`; 65537 failed earlier
with exact `LinkError(1,65537)`. This is validation-order evidence, not a claim that
the malformed exact64KiB input is executable Java.

All successful checkpoints were independently decoded and their typed inode,
descriptor, and logical-byte counts compared with EVM `SliceResult`. Failed calls
were checked for exact selectors/words and absent speculative outputs. No OOG trace
or failed-call state was harvested as proof.

## Final-artifact gate and resources

The final command was run after the review test reached its final contents:

```sh
go test ./jvmevm/localcontinuation/vfs0a -count=1 -v
```

Result: PASS in328.960s (92 run records,28 top-level PASS records, no FAIL/SKIP).
It includes all24 Java8 roots, all declared q1/q7 chains, seven path-regression EVM
roots, pending-bind true-new-process continuation, transport/durability/provenance,
parent wire checks, and this review. The log itself records runtime293010B and SHA
`78d57a...39c9`, so the prior292377B harness result was not reused.

A process-tree watchdog enforced1200s/4294967296 bytes: completed in329.331s,
peak aggregate RSS269291520 bytes, neither limit hit. Evidence:

- `build/java-diff-mc-vfs0a-boundary-review/full-package-final.log`, SHA256
  `01b9d8b102f31d95fc3185ef8b82ba7303b729c0797251ccf51a7f5584ed043d`
- `build/java-diff-mc-vfs0a-boundary-review/full-package-final.json`, SHA256
  `62c65a79e42d252a9d27d80b530490d2070664f36f50b8f53b65d63b4ec9998d`
- focused final review log: `boundary-tests-final.log`, SHA256
  `48988dd0146474a10ac132c8686432e44c0b0c813cd625869af63f2326e68ad5`
- accepted IOE0 control: PASS39.884s, log SHA256
  `d38cd6ee905f23c0153ae243ec2236c2a913a1f613a9b47ac02bdb515f0cb917`
- reproducible runtime build log SHA256
  `e442b2c3880ace39e2cbc3fbf8943faa8df1d5a37b849ba59b10cb5e8f212a3a`

Semantic evidence is the committed test plus final watchdog log. Commands:

```sh
go test ./jvmevm/localcontinuation/vfs0a -run '^TestVFS0aBoundary' -count=1
NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules \
  node jvmevm/runtime/local/vfs0a/build.js --check
go test ./jvmevm/localcontinuation/ioe0 -count=1
```

Budgets were unchanged:100M/30s ordinary;1B/120s only for explicit transfer/quota/
checkpoint boundaries;25M reserve;1..4096 units/call; ordinary4096 total and dedicated
quota/copy65536 total; VFS-only4096 slices; checkpoint1MiB; LOCAL code320KiB. No
silent cap increase or unreachable quota combination is claimed.

## Disposition and limits

No acceptance blocker was found in the assigned groups on FINAL293010B. The review
recommends that the parent may count this boundary/rollback slice as passing, subject
to the parent's separate source review, other reviewer evidence, legacy gates, and
sole final acceptance decision. The runtime remains LOCAL and oversized for standard
CREATE. True Minecraft1.12.2 startup and its ready marker remain future work.
