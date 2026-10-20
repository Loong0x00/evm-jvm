# P21 MAX_OBJECTS2048 candidate — build blocked, not accepted

Scoped worker files for the one ordinary-object-capacity stage. The untouched base is the accepted P20 engine at `../parent-max-arrays-2048/artifacts/engine/MCEntryInterpreter.sol`; no historical parent evidence or source was changed.

## Candidate/source audit

`engine/MCEntryInterpreter.sol` is exactly the P20 source after the fresh P21 domain-label transition plus `MAX_OBJECTS=1024` -> `2048`. `rebuild.py` normalizes P21 back to P20 and the one cap back to1024, then requires byte-for-byte equality with the accepted P20 source. It also computes both roots from the 97 ordered source leaves using the local Go Keccak helper. `artifacts/source-audit.json` records P20 root `845e0c87…` and P21 root `e4bfd093…`; all97 leaf hashes are identical. `MAX_ARRAYS` stays2048, `MAX_HANDLES` remains derived and evaluates to4353. No lazy allocation, GC, fake reclamation or terminal-state continuation is added.

## Generated fixtures

`generate_retained_fixtures.py` copies the already-reviewed generated packed/sparse/Integer/Object/Math/raw71 fixtures and adds four Java8-targeted one-class programs. Each program executes exactly N `new java.lang.Object()` allocations; class entry names include the required `.class` suffix in the capacity binding manifest. `artifacts/generated-capacity-fixtures.json` preserves archive/class hashes and allocation counts without archiving class bytes. `ObjectCapacity2049.javap.txt` confirms the bytecode performs one `new java/lang/Object` and constructor invocation per loop iteration.

`capacity_preflight.py` must be run before `full_generated_gate.py`. It runs only the four q4096 generated capacity cases, each through public setup/finish/reopen, and checks exact ordinary-object/field/array counters and checkpoint hashes. The OOM assertion is intentionally `kind7` plus class derivation from the authenticated exception heap record. The source root order puts `_bootstrapOutOfMemoryError` at bootstrap leaf9; the one raw capacity fixture makes its machine class-list index10. Canonical terminal `javaClass` is intentionally empty. q1/q7 are expressly not attempted for the high-count worlds. The full gate retains the existing q1/q7/direct/reopen packed, sparse, malformed, Integer, Object, Math, and raw71 controls under the ordinary1B external gas cap.

## Verification status / blocker

Source normalization, root/leaf audit, fixture generation, manifest hashes, and Java8 bytecode disassembly completed locally. The Solidity compile, object-capacity EVM preflight, and full generated gate did **not** run, so this stage is not accepted and has no verified runtime-size result.

Only cached dependencies were permitted. `jvmevm/runtime/node_modules/solc` is absent. `cd jvmevm/runtime && npm ci --offline --ignore-scripts --no-audit --no-fund` failed because the cache lacks `tmp@0.0.33` (`ENOTCACHED`, request for `tmp-0.0.33.tgz`). No network or sibling worktree was used. Once the pinned compiler is available from an authorized local cache, run:

```sh
python3 evidence/java-evm/minecraft-entry/max-objects-2048/rebuild.py build/java-diff-mc-max-objects-2048-build-<unique>
python3 evidence/java-evm/minecraft-entry/max-objects-2048/generate_retained_fixtures.py build/java-diff-mc-max-objects-2048-fixtures-<unique>
python3 evidence/java-evm/minecraft-entry/max-objects-2048/capacity_preflight.py build/java-diff-mc-max-objects-2048-build-<unique> build/java-diff-mc-max-objects-2048-fixtures-<unique> build/java-diff-mc-max-objects-2048-preflight-<unique>
python3 evidence/java-evm/minecraft-entry/max-objects-2048/full_generated_gate.py build/java-diff-mc-max-objects-2048-build-<unique> build/java-diff-mc-max-objects-2048-fixtures-<unique> build/java-diff-mc-max-objects-2048-gate-<unique>
```

Keep `GOPROXY=off`, `GOSUMDB=off`, and the gate's finite 1200s/30s-call/1B limits. The parent separately owns fresh P21 max-gas replay of the unchanged original; this worker neither has nor reads original JAR/classes/resources/worlds/checkpoints and makes no Minecraft, EULA, world, `Done`, standard-chain, or readiness claim.
