# Artifact index / append-only run notes

The final worker artifacts for this scoped candidate are:

- `SHA256SUMS-worker4.txt`: hashes for all stage files present at final packaging (except the checksum manifest itself).

- `source-audit.json`: exact one-constant P23 source, 97-leaf/root, fresh compiler, ABI/layout audit.
- `build-pins-worker4.json`: final offline build and harness pins, including the test-only q256 diagnostic mode hash.
- `generated-capacity-fixtures-worker3.json`: corrected fixture expectations/hashes. This manifest is authoritative for the generated Object2048/2049/4096/4097 class files.
- `capacity-preflight-summary-worker8.json` and `capacity-gas-blocker-worker8.json`: canonical preflight and explicit ordinary-1B OOG blocker. 4097 was not attempted.
- `full-generated-gate-summary-worker4.json.gz`: retained 11814-receipt generated gate with corrected capacity caveat.
- `malformed-quantum-summary-worker3.json`: 42 malformed checkpoint refusals.
- `ordered-receipt-hashes-worker4.json.gz`: final ordered receipts/counters for capacity and retained generated worlds.

Earlier uniquely named artifacts are deliberately preserved, not overwritten. In particular, `generated-capacity-fixtures.json` was an initial manifest with a stale expected boundary (it labeled 2049 rather than 4097 as OOM); its generated class bytes match the corrected fixture generation, but do not use its expected-outcome metadata. `generated-capacity-fixtures-worker3.json` is the corrected manifest. The unsuffixed capacity and receipt archives and `*-worker3` full-gate/receipt archives are preliminary captures; use the final `worker8` capacity and `worker4` retained/receipt artifacts above.
