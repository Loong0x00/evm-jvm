# MAX_ARRAYS 2048 — generated acceptance

## Scope

This is a disposable LOCAL candidate based on accepted P19 at `parent-668583cae`. The engine source differs by exactly one line: `MAX_ARRAYS = 1024` becomes `MAX_ARRAYS = 2048`. `MAX_HANDLES` remains derived (`2048 + 1024 + 256 + 1 = 3329`). `MAX_OBJECTS=1024`, array length/elements caps, all 97 bootstrap images/root, checkpoint wire, ABI/storage layout, coordinator authorization, and ordinary 1B call budget remain unchanged. No original Minecraft artifact was read or executed.

## Result

- Candidate engine runtime: **392,090 bytes / 393,216 cap**.
- Runtime SHA-256: `4f8cb03726540d9a6ec4883ec057bd8a8f8d9a68fe146660467e0a67441556b4`.
- Runtime Keccak-256: `6ff2ab0714affd78868b4d6374ff3cb1757c39a1803adec403139d1de24f98a3`.
- Accepted P19 source SHA-256: `532ae7aa569e0b2ca6d9c9bb9ebffb292cb4328dd8e6da3c77c5520f75481b53`; candidate source SHA-256: `0038a345c811599f347dc7492d04ba76bfc97e3bc13970b0b7fe726a96e8531d`.
- Actual source-derived 97-leaf bootstrap root: `f4cf01e4356d76476b5ccd0949152c0422010df332d20bb1c84855793921dc81`.
- Full generated retained gate: **PASS, 986.032 seconds / 1,200-second limit**, 283 recorded commands (one expected raw-72 driver guard exit 2), 11,827 canonical public receipts across 64 worlds.
- Existing packed/sparse/malformed, Integer/Object/Math, and raw-71 generated controls remain in the q1/q7/direct/reopen gate.

## Capacity boundaries

Four Java-8-compiled generated fixtures make only zero-length `int[]` allocations. The canonical empty `String[]` main argument is the first counted array; the fixtures request 1023, 1024, 2047, and 2048 additional allocations respectively.

| Target ordinary arrays | Result | Guest counters / terminal |
|---:|---|---|
| 1024 | normal completion | ordinaryArrays=1024, ordinaryObjects=0, arrayElements=0 |
| 1025 | normal completion | ordinaryArrays=1025, ordinaryObjects=0, arrayElements=0 |
| 2048 | normal completion at boundary | ordinaryArrays=2048, ordinaryObjects=0, arrayElements=0 |
| 2049 requested | typed guest OOM at cap | ordinaryArrays=2048, JavaKind=7, exception handle=2050 mapped to OOM class index 10 |

The four capacity worlds used the ordinary direct quantum 4096, ordinary 1B EVM-call ceiling, terminal checkpoint validation, and a separate reopen. Their exact checkpoint hashes, full heap counters, and receipt references are in `results/05-local-a/capacity-checkpoints.json` and `canonical-receipts.json`. High-count capacity q1/q7 chains were **not attempted**: they would create thousands of full-heap checkpoint/revalidation slices. This is a bounded capacity proof, not a claim that q1/q7 are semantically different or impossible. Retained controls still cover q1/q7/direct/reopen.

## Reproduction and evidence

The successful source build is `build-03-local-a`; final corrected generated fixtures are `fixtures-04-local-a`; the passing full gate is `gate-05-local-a`. Exact pins, one-line source audit, 97 leaves, all command statuses, capacity-fixture hashes, and canonical receipts are archived in `results/05-local-a/`; verify `SHA256SUMS` there.

From this worktree, future runs must use new append-only IDs, for example:

```sh
python3 -B evidence/java-evm/minecraft-entry/max-arrays-2048/build.py 06-local-b
python3 -B evidence/java-evm/minecraft-entry/max-arrays-2048/full_generated_gate.py \
  build/java-diff-mc-max-arrays-2048-build-06-local-b \
  build/java-diff-mc-max-arrays-2048-fixtures-06-local-b \
  build/java-diff-mc-max-arrays-2048-gate-06-local-b
```

`build.py` pins local/offline dependencies and rejects pre-existing output paths. The full gate is itself limited to 1,200 seconds; each successful EVM call is independently bounded and receipt-checked. `tools/verify_capacity_outputs.py BUILD FIXTURES GATE` reopens only generated capacity checkpoints.

Earlier interrupted `build-01-local-a` / `build-02-local-a` outputs and the empty `results/01-local-a` directory were preserved. Two initial local harness assertions were corrected and recorded in `results/05-local-a/attempt-history.json`; the final run passed. Parent evidence was used read-only and not modified. No original-server replay, EULA, Minecraft startup, world generation, genuine Done, or readiness claim is made by this result.
