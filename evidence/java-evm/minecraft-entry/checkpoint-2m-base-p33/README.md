# Parent-provisioned accepted P33 source snapshot (read-only baseline)

Authorized source-only whitelist, provided by the parent while worker waits at request r1. No original JAR/resources/raw classes, worlds/checkpoints/original receipts, or original binding manifests are included.

- `engine/`, `coordinator/`, `p33-pins.json`: exact independent P33 compiled sources/artifacts, 398336B engine; accepted1MiBCP profile. Do not edit this frozen baseline.
- `reference-transport/canonical-driver.go.txt`: exact ordinary1B/30s opaque P33 Go transport (q65536 bound, codehash/owner/package/read/counter proofs). Its authenticating source is not the historical executable LC0 profile.
- `reference-transport/`: source-only decoders/verifiers/helpers, not results. Original verifier source is only an adaptation reference, not permission to use original inputs. Ordinary verifier is reference-only and contains old per-profile limits that must be explicitly scoped.
- `generated-only-reference/`: current math-double-min-max generated tool sources/bootstrap/fixture source, no test or original input binaries. These templates retain P28 label/address/pins; parent P33 generated_gate shows explicit domain/address/real artifact repinning. They are source references, not automatically runnable accepted P33 validators without this normalization.
- `SOURCE_MANIFEST.json`: every provisioned file and SHA256, provenance plus exact P33 hashes.

Create separate append-only checkpoint-2m stage; runtime ceiling stays1MiB, CP doubles2MiB. Preserve this baseline and existing legacy defaults. No underlying EVM changes. No source access outside own worktree/dependencies granted by this snapshot. Pinned solc/js-sha3 already live in your own jvmevm/runtime/node_modules.
