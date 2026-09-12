# Exact-source provenance

The fourteen files in `sources/exact/` are byte-for-byte copies of the committed
fixtures at `evidence/java-evm/capacity-baseline/preflight/fixtures/` from parent
draft commit `5ed777fd5`. They are retained here so this worker's builder has no
mutable dependency on a parent-owned evidence directory.

`generate.py` hard-rejects a run unless their SHA-256 values match the following
pinned map. It additionally compiles the Big pair on exact Java 8u504 and rejects
it unless `BigEntry.class` is 90874 bytes with CP count 2565 and 2552 methods,
and unless both recorded class digests and the recorded deterministic ZIP digest
match `fixtures/big2-meta.json` in the parent preflight evidence.

The chain fixtures are generated source (saved in each fresh output under
`generated-sources/`); `sources/boundary/` are the two Java sources used before
the TEST-only valid unknown-attribute construction.
