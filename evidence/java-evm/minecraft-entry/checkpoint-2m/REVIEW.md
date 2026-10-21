# Generated-only review: P33 checkpoint-only 2 MiB profile

## Result

The append-only profile compiles and passes its full generated-only direct,
reopen, and ordinary-CREATE coordinator gate. Durable evidence:

- [`runs/p34-checkpoint-2m-generated-r2-20261021/run-report.json`](runs/p34-checkpoint-2m-generated-r2-20261021/run-report.json)
- [`runs/p34-checkpoint-2m-generated-r2-20261021/gate-summary.json`](runs/p34-checkpoint-2m-generated-r2-20261021/gate-summary.json)
- [`runs/p34-checkpoint-2m-generated-r2-20261021/reopen-summary.json`](runs/p34-checkpoint-2m-generated-r2-20261021/reopen-summary.json)
- [`runs/p34-checkpoint-2m-generated-r2-20261021/coordinator-summary.json`](runs/p34-checkpoint-2m-generated-r2-20261021/coordinator-summary.json)
- [`runs/p34-checkpoint-2m-generated-r2-20261021/fixture-manifest.json`](runs/p34-checkpoint-2m-generated-r2-20261021/fixture-manifest.json)

Engine runtime: 398,336 bytes, SHA-256
`86a00ce92b3f3d61f62bcfffe7df7dee50958cac8663e4449d386dd16a6dbe8d`, Keccak
`3a1bb6dce1edb2d0d4785244c20d5be94168af6b2dbb2737820c304907490248`. Its
runtime cap stays 1,048,576 bytes. Coordinator runtime: 5,411 bytes, Keccak
`0f0089301fba8ec5057027b90605e12c13652837edb998ed83460fb1f1f609c1`.

The generated positive retains two eager `Object[65536]` arrays (131,072
zero-filled elements) and yields a 1,050,210-byte checkpoint in all five routes:
q1 (7 slices), q7, q4096, q65536, and direct. Machine root, VFS root, Java/internal
step totals, and heap identities agree across routes. The genuine coordinator
exact-150-class / 1,063,930-raw-byte route returns a 1,050,806-byte checkpoint.
The q1 checkpoint and coordinator checkpoint are archived and their local
SHA-256/Keccak calculations match their gate summaries and EVM roots.

The independent child process reopens all four pinned checkpoints, including the
1,050,210-byte q1 pair checkpoint. The old P33 runtime still completes a small
generated profile with its original 1 MiB configuration root, but refuses the
actual eager-array pair at serialization with `LC0StateError(1,0)` and no root,
head, or log mutation. The new profile's four-array output-boundary control also
returns `LC0StateError(1,0)` atomically. A separate read-only validator receives
exactly 2,097,153 synthetic malformed bytes and refuses them with the same typed
error without publishing state.

For the same generated ArrayList control, the legacy and new configuration roots
are respectively `0x385501057e95fa2031b15f12e8af9b4e8e869428564f1e737746da323628fd17`
and `0x2e41755d35bd8a23d390386c6d9b17dd874385839451480a0e8bbe027e1b6a46`;
the runtime codehash also changes. The pinned P33 domain/address and all 100
bootstrap images, 21 existing native bindings, raw limits, 262,144-element
array cap, and other configured limits remain unchanged. The source verifier
checks the exact two engine limit edits and the coordinator's single engine
codehash repin against the P33 source snapshot. The fresh build also proves ABI
and storage-layout equality.

## Verification

- `python3 tools/verify_source.py`: passed (exact P33 source delta and 64-file
  baseline snapshot manifest verified).
- `go test ./evidence/java-evm/minecraft-entry/checkpoint-2m/transport`: passed.
- `go build ./evidence/java-evm/minecraft-entry/checkpoint-2m/tools`: passed.
- `go build ./evidence/java-evm/minecraft-entry/checkpoint-2m/reference-transport`: passed.
- `tools/generate_fixtures.py`: passed with 41 cases, 21 generated-only Java 8
  host oracles, exact 1,063,930 raw-byte positive, and exact 1,063,931 refusal.
- `tools/run_gate.py p34-checkpoint-2m-generated-r2-20261021`: passed with the
  ordinary test-only 1,000,000,000 per-call gas and 1,200-second wall budgets;
  direct engine gate took 1,007,960 ms. No budget was expanded.
- First run's coordinator build-path harness error and two fixture preflight
  failures are preserved under `runs/` rather than overwritten. The gate runner's
  exact pre-normalization source is archived; its later edit only removed one
  trailing space (see `source-hash-amendment.json`).

No original JAR/classes/resources/worlds/checkpoints/receipts were read or
executed. No original Minecraft replay, EULA acceptance, startup, or genuine
`Done` result is claimed. The runtime remains oversized and LOCAL/preinstalled;
this is not standard CREATE/EIP-170 deployment compatibility or overall P34
Minecraft acceptance.
