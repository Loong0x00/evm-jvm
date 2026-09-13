# Parent arraycopy evidence

See root `JAVA_EVM_MC_ARRAYCOPY_PARENT_PREFLIGHT.md` for scope, pins and results.
`run.sh` reconstructs/reproduces the bad candidate, rebuilds the repaired engine,
and asserts generated outcomes. `follow.sh` tests bootstrap/edges/original13;
the preserved first invocation fails only at the old512-observation assertion.
`continue-first.py.txt` is that exact historical observer. `advance.py` uses
normal bounded512-step batches with fresh reopen, never changes runtime caps.
`frontier.py` supports declared original bindings and q1/q7 in NEW worlds only.
`verify_receipts.js` independently re-encodes nested ABI and validates successful
public receipt chains; `test_verifier.py` mutates generated evidence only.

`engine/`, `coordinator/`, `pins.json`, `executed_bounded_driver.go.txt` are the
final parent source/artifact/transport derivative. `rebuild.py ... repaired`
recreates them from candidate source with the narrow arity/identity changes.
No accepted source is changed. All generated bootstraps and JAR fixtures are
TEST-only; no original execution-path host Java/ZIP/class interpreter is used.

`parent-evidence.tar.gz` is an explicit metadata/checkpoint allowlist with entries
hashed in `archive-files.json`; no original archive/class/resource-page or any
LevelDB payload is included. Original checkpoints are EVM-issued mutable state,
not original class images. `TEST-only-*.txt` are static explanatory excerpts,
not input authority. Worker receipts remain historical and unaccepted.
