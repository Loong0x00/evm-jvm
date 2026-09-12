# MR0 atomic publication COPY preflight (narrow; not Session acceptance)

Base: `2dfc3c95c`. This is a Go-only disposable COPY under
`evidence/java-evm/main-root/atomicity-preflight/`; it does not modify the MR0
Solidity sources, artifacts, accepted profiles, quotas, or core packages. It
uses the immutable engine SHA256
`5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875`, engine
Keccak `0x2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f`,
coordinator Keccak
`0x06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c`, and
engine route `0x4d52304d41494e454e47494e4500000000000001`.

## Repair

`atomicity_session.go.txt` stages checkpoint, StateDB/trie, and Head metadata.
It creates an explicit empty initial Head, then always reads the prior durable
Head before a mutation. Before Head rename, failure reloads the old StateDB,
restores the old in-memory manifest (including counters), drops only a known
new checkpoint/temp path, and returns gas with empty output/logs. It never
writes `resume-refused` or any observer counter/stage Head after that error.
The old Head bytes, rather than only its root field, remain authoritative.

The atomic boundary is Head rename. A fault/directory-sync/reload failure after
that rename retains the new Head/root and poisons the in-process Session; calls,
creates and subsequent Head writes refuse. Only fresh `openEnv` revalidates it.
External receipts are under `reports/`, not Session state. The test-only fault
switch is accepted only with `MR0_ATOMICITY_TESTING=1`, is a self-owned storage
boundary switch, and its `atomicity-retry` route invokes the same normal public
`resumeMain` validation/EVM/publication path twice; it supplies no code, state,
manifest, page, class, ZIP, or decoded-result authority.

The 30-second owned EVM timer now uses an atomic cancellation notification and
joins a callback that raced `Stop`. Cancellation reloads the staged root even
when EVM returns nil; CREATE and CALL still retain their distinct raw EVM
observations. The optional shorter test timeout needs both
`MR0_ATOMICITY_TESTING=1` and `MR0_ATOMICITY_TEST_TIMEOUT_MS<=30000`.

## Reproduction and evidence

Run (fresh ignored output only):

```sh
python3 evidence/java-evm/main-root/atomicity-preflight/run_atomicity.py \
  build/java-diff-mc-main-root-atomicity-NAME
```

The Python driver uses `start_new_session`, polls all process-group members via
`ps`, kills the entire group at 20 minutes, and records group RSS watchdog JSON
per compiler/driver command. It compiles only the Go COPY and validates the
immutable JSON artifacts through the binary pins. Fixture Java is test-only.
It performs normal public `setup-chain`, `atomicity-resume`, `atomicity-retry`,
and fresh-process `verify` calls.

`run-20260912T132222Z/` preserves (the earlier `run-20260912T132103Z/` remains archived) command logs/watchdogs, external receipts,
all Heads, selected raw checkpoints, artifact/source hashes, and the fault
summary. It proves nine pre-rename storage points (blob creation/write/sync/
rename/dir-sync, trie sync, manifest create/write/sync): byte-identical old
Head, unchanged old CP, empty failed output/logs and same-process normal retry.
It proves both post-rename points poison then fresh reopen the newly published
Head. Actual `chmod 0500` checkpoint-directory EACCES reproduces the historical
public CLI shape but now preserves exact old Head/CP and permits public retry
plus fresh reopen. A real read-only Head plus non-writable parent directory
exercises manifest-create EACCES. `positive-12-summary.json` records the 12
positive direct/q1/q7 setup/finish/verify worlds, including terminal exception
nonzero Java references.

This is deliberately **not** complete MR0 Session acceptance: it does not
prove the parent-owned strict receipt verifier, all Open/CAS/capacity/transport
coverage, or Minecraft/official-JAR execution.
