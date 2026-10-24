# Parent P60 revision

Worker REPORT.md describes its original candidate binary and incomplete q1 probe,
not the final parent result. Parent independently reproduced both old/new Java8
images and fixed a measured preexisting cold-reference-array hierarchy restore
issue in `_requireAssignable`; Java append/growth/Itr algorithms stayed unchanged.
Current pins/artifacts/canonical1B driver are the parent-corrected version.

Authoritative review: `JAVA_EVM_MC_ARRAY_LIST_ADD_PARENT_PREFLIGHT.md`.
Proofs: `../parent-array-list-add/artifacts/hash-based-table-resource-blocker.json`.
Independent fresh reproducer from repository root:

```
python3 -B evidence/java-evm/minecraft-entry/parent-array-list-add/rebuild.py build/java-diff-mc-array-list-add-build-parent-NEW
```

Do not resume worker worlds or pre-repair parent worlds using current artifacts.
Generated ordinary1B, measured raw1508B and quota-case2B are distinct; original
MAX/60s is separately authorized. No host original parser/execution or fake result,
no standard-chain deployment/complete Java SE/server readiness claim.
