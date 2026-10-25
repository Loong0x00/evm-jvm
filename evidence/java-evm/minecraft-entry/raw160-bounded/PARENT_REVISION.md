# Parent P62 acceptance

The worker README/evidence describes its initial candidate and remaining gates.
Parent independently rebuilt the same runtime and completed class161/constructor
160-161/byte exact+1/high287/retained/reopen/config160/fresh original151 tests.

Authoritative review: `JAVA_EVM_MC_RAW160_PARENT_PREFLIGHT.md`.
Authoritative pins: `../parent-raw160/artifacts/parent-build-pins.json`.
Original proof: `../parent-raw160/artifacts/immutable-table-resource-blocker.json`.

Reproduce into a fresh directory from repository root:

```
python3 -B evidence/java-evm/minecraft-entry/parent-raw160/rebuild.py build/java-diff-mc-raw160-build-parent-NEW
```

Only explicit LOCAL raw count150→160 changes. Java images, external ABI, engine
storage/checkpoint codec/native22/String12/other caps/geth rules stay. Necessary
private coordinator array extents160 shift following fields+31 slots; fresh profile
only, no old-coordinator storage migration. No standard CREATE/server Done claim.
