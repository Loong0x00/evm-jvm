# P37 array `clone()` intrinsic — worker result for independent parent review

**Status:** worker implementation and generated EVM gates pass; this is not parent acceptance. The official Minecraft JAR/world was not read or executed. No Minecraft startup, EULA, world generation, or `Done` claim is made.

## Source change

- Exact source-only base: commit `1f604f3fc49aa92d4593114c0733177f5e841ce0`, manifest SHA-256 `26406f82ca8bb7a3cc51c6187f6b42d8504c7d7d7411430989e0958dde3108cd`.
- P36 source-proof verifies all nine baseline manifest files, the ordered 103-image bootstrap leaf set, root `851a47c08ef61b29471de2db8b764c88989b18e2c523490bbe9b0588a8725faa`, unchanged engine/coordinator ABIs and storage layouts, no binding changes (21 global / 12 String-local), and only `_resolveVirtual` / `_execute` changed as Solidity functions.
- Engine source SHA-256 `e6775dc4bf560cbfda57a77b8347515c54d9d10651182f6eb40ef000805047bb`; init 410,808 bytes; runtime 410,780 bytes, SHA-256 `9145fbb48f5dae753d77c2591e7aa3f6b0e6f6f3c1e0ffdf1f5545626d08aa96`, Keccak `61d5020d370eced2479ff7be2a998550a5a5801b59cc4f423c111835c1318b14`. This oversized engine is exercised only by local preinstalled-code `Call`, not EIP170/CREATE.
- Coordinator source SHA-256 `5047118613f9234ba632ffbfebcfc50cafe35b683d2d616bf23ef62d864ca871`; runtime 5,411 bytes, SHA-256 `e72e53a29e308b2a63ffd0e550e9a809aa37469fb5bd7decbd6b833697356f1e`, Keccak `083a87b4073ca9cd1fe3ca76c744e6d7b1bce5092f3108b4415be72ff8c2499d`.
- No new native binding or bootstrap image. Existing raw-input, array, element, runtime, and checkpoint caps remain unchanged.

The narrow resolver handles only array-owner `clone:()Ljava/lang/Object;`. The execution path checks null/type/kind/assignability and existing quotas, then eagerly allocates a distinct normal guest array with identical rank/leaf metadata and shallow-copies all raw element cells. It returns the new reference. Ordinary `Object.clone()` remains unimplemented/unhijacked. Per-invocation hierarchy scratch is rebuilt for runtime reference-array leaves at clone and cast checks; it is not serialized into the checkpoint.

## Final generated-fixture run

Primary evidence: `results/gofmt-final01/` (run summary, final generated-fixture manifest, source proof, clone summary, reopen summary, coordinator summary). Fixture manifest SHA-256: `5bca9395c227c373df2ac96cb2980f163faa7664eeb02df684b82aca2e16a8e8`. The local JDK is `javac 1.8.0_504`; 36 generated host-oracle cases pass. No host oracle executes the original server.

- Clone matrix: q1 / q7 / q4096 / q65536 use 850 Java steps and 4 internal steps, with identical machine root `32a2acaec95fb7be8c06faa0624f84a4eb2a7b8767f43f15f7c3a1b2e51729fd` and VFS root `0xd6260df389ccc1750bedd8a3032a9226b10a2c41ec065d030e8d4f292d6957dc`. Calls: 850 / 122 / 1 / 1. The matrix covers all primitive array types, reference and multidimensional arrays, covariant `String[]` through `Object[]`, exact runtime array type, shallow reference sharing, mutation independence, empty arrays, raw float/double payloads, and caught null NPE.
- A separate null receiver case catches guest NPE and returns normally.
- Maximum-length `double[65536]` clone completes; read-only MR01 heap audit reports 3 arrays (entry args + source + clone) and 131,072 elements. Gas: 293,038,951.
- Array-quota failure is caught as guest OOME; audit remains exactly 4,096 arrays / 4,094 elements (entry args included), proving the failed clone did not publish. Aggregate-element OOME is caught; audit remains 5 arrays / 196,611 elements, below the unchanged 262,144-element quota.
- Seven malformed/unsupported/wrong-owner and ordinary-`Object.clone` controls return typed EVM refusals with identical pre/post root/head. The generated valid `Cloneable` object probe rewrites only `invokespecial Object.clone` to `invokevirtual`; ordinary Object clone resolution returns the existing `CallError(3)`, not an array clone result.
- q1 final checkpoint: 4,085 bytes, epoch 850, 105 diagnostic classes. A distinct OS process (prior PID 709982, reopen PID 710266) reopens and read-only-validates the same state root, checkpoint root, machine root, and heap; no resumed guest state is fabricated.
- Canonical paired route: generated `ArrayCloneMatrix` is the entry in a 150-class / exact 1,063,930-byte package. AS0→ZI0→DI0 indexing/decoding, ordinary coordinator CREATE, local engine Call, and terminal MR01/head validation pass. ZIP is 1,081,756 bytes; 3,224 EVM calls; max call gas 242,435,752; total gas 11,585,286,243; terminal lifecycle/outcome 2, with 850 Java / 4 internal steps and 253 diagnostic classes. This is a generated fixture route, not Minecraft execution.
- Initial clone-only test budget 1,000,000,000 gas / 1,200 seconds per call; no shortage required a budget change. Full canonical coordinator uses separately labeled 2,000,000,000 / 2,400 test-only limits. EVM charging is unchanged.

## Retained P36 regression evidence

The prior full P36 gate is `results/clone-reopen-v1/retained-p36-attempt-1/gate-summary.json` plus its fresh-process `reopen-summary.json`. It passed on the **identical engine runtime SHA-256** `9145fbb4…6d08aa96`, with 2,000,000,000 gas / 2,400-second test-only limits; elapsed wall time was 1,114.415 seconds. The latest null-receiver run cross-checks the prior fixture-manifest hash, every prior source hash, every prior bundle manifest, and every compiled prior class hash; the only added Java source/class is `ArrayCloneNullReceiver`. Thus the full P36 suite was not needlessly replayed after adding that isolated generated NPE oracle.

## Preserved discovery failures

These are retained as preliminary failures, not accepted results:

- `results/cloneaccepted01/`: q1 covariance call initially returned `ReferenceError(2,241)` at `String[]`→`Object[]`; fixed by rebuilding the runtime leaf hierarchy in the current call.
- `results/covariancefix01/`: clone matrix reached completion but `checkcast Object[]` still raised guest `ClassCastException`; fixed in the array cast branch.
- `results/semantics-final01/`: first quota fixture exhausted arrays during its setup because the entry `String[] args` consumes one array; changed setup to exactly 4,096 arrays including args and verified the caught clone OOME.
- `results/quota-boundary-fixed01/` and `results/objectclone-control01/`: clone semantics passed, but the worker harness passed a fresh empty report directory to its reopen verifier. Fixed by using the same report directory in a distinct verifier process; `results/clone-reopen-v1/` and final reopen evidence pass.
- `run-gate-worker01.stdout.log`: no EVM was run; a previously created fixture directory correctly triggered the no-overwrite guard.

## Reproduction

From the repository root, offline dependencies already provisioned:

```sh
export NODE_PATH="$PWD/jvmevm/runtime/node_modules"
PYTHONDONTWRITEBYTECODE=1 python3 evidence/java-evm/minecraft-entry/pattern-compile-bootstrap/tools/array-clone-intrinsic/run_gate.py NEW_UNIQUE_RUN_ID --clone-only
```

This rebuilds the engine/coordinator and Go driver, compiles Java 8 fixtures, reruns clone q1/q7/direct cases plus new-process reopen and canonical coordinator route, and proves the P36 cross-reference. Omit `--clone-only` to rerun the full P36 gate as well. Outputs go to ignored `build/` for disposable VM/checkpoint data and Git-tracked `reference/array-clone-intrinsic/results/<run-id>/` for summaries/manifests; run IDs are never overwritten.

**Pending:** independent parent source review and acceptance. No push.
