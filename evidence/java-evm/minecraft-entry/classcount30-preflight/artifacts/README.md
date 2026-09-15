# Generated cap30 gate evidence

This archive records the single LOCAL384 source build and one generated-only gate for
`MC-CLASSCOUNT30-C30`. It is pinned by `../parent-input.json` and the strict reverse
verifier `../tools/verify_source.py` to `parent-3ed302a92`.

Reproduction from this worktree (with the pinned local `solc` dependency already
installed) was:

```sh
python3 evidence/java-evm/minecraft-entry/classcount30-preflight/tools/build.py \
  build/java-diff-mc-classcount30-formal1
python3 evidence/java-evm/minecraft-entry/classcount30-preflight/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/classcount30-preflight/tools/generate_fixtures.py \
  build/java-diff-mc-classcount30-fixtures
python3 evidence/java-evm/minecraft-entry/classcount30-preflight/tools/gate.py \
  build/java-diff-mc-classcount30-formal1 \
  build/java-diff-mc-classcount30-fixtures \
  build/java-diff-mc-classcount30-gate
```

`engine/` and `coordinator/` retain the pinned compiler outputs. `fixtures/` contains
only generated Java-8 CountMain/Tail fixtures and their binding metadata. The source
and inputs do not read an original server archive, class, resource, or world.

`generated-gate-summary.json` records q1/q7/direct/reopen results for 29 and 30,
reordered30, all three independently reached 31-class refusals, and both aggregate
byte boundaries. `canonical-receipts.json` records the independent canonical ABI,
event, checkpoint, and read-range verification for the seven successful worlds.
`failures/`, `heads/`, and `commands/` retain compact exact failure/Head/timing
receipts. `SHA256SUMS` covers this durable evidence archive.
