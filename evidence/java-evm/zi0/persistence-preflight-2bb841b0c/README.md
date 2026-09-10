# ZI0 persistent-index preflight: independent baseline replay

NOT production/freeze/acceptance. Worker2bb841b0c integrated as a00108e08. Original
source/driver/artifact/report are retained under worker/ (Go source as .go.txt).
worker-manifest.json verifies their original lengths/hashes. No copyrighted server
artifact was uploaded or executed; all ZIP bytes here are generated fixtures.

Parent reconstructed a fresh disposable workspace at
build/java-diff-mc-zi0-persistence-parent-2bb841b0c/, changing ONLY the build.js/main.go
workspace path. Pinned compilation produced byte-identical prototype.json. A fresh
compiled executable ran through evidence/java-evm/watchdog.py with20min/4GiB caps;
parent/{build.log,replay.log,watchdog.json,report.json} are the captures.

Independent replay passed:18.423s external,269950976B sampled peak process-groupRSS,
exit0/no limit. All6 runs matched worker gas, roots, entry counts, byte/CD sizes and
publication counts EXACTLY; all54 control records matched. The20554-entry generated
input had4057736bytes,2100796-byte CD,496 AS0 append calls and322 scan calls. Its
823 publications are1 AS0 CREATE+496 append+1 seal+1 index CREATE+1 discover+322 scan+
1 finish. New-process mid-index continuation and separate final reopen passed.
Parent observed41449535B disk (worker41449537B); this is filesystem/LevelDB layout,
not an encoded-state invariant. No batching/cap increase is inferred or permitted.

These are baseline controls, not independent negative-case completeness. The toy
transport still lacks production namespace/symlink/bounded metadata/pin/failure-
publication guards. Its control helper's positive expectation also needs tightening:
a positive case that returns a valid ZI0Error can currently be reported instead of
failing the helper. None did so in this recorded run (explicitly compared outcomes).
Old overlap/bad-range fixtures fail earlier method0-size checks; dedicated controls
must reach overlap/range rejection itself. Constructor owner0 and at-EOF no-op scan
behavior need explicit freeze choices. No hash collision was generated; changing a
query's byte ordinarily changes its hash and does not test the collision guard.

Further parent tests should exercise copied TEST-only bucket corruption for actual
full-byte mismatch, direct post-write OOG rollback, geometry-specific errors,
adversarial small-TLV extra fields and EOCD candidates. Archive all such new probes
and results here before the production ABI/transport freeze. No temporary directory
is sole authority for this evidence.

Parent additionally executed `max32m_test.go.txt` against the same unchanged artifact:
exact33554432B generated ZIP, high25-bit name/LOC/data offsets33554388/33554269/
33554321, full AS0 upload then genuine EVM discovery/index/entry/lookup. Pass1.10s
(external1.166s/216977408B sampledRSS), no limits. This covers actual packed high
bits, not just an AS0 capacity claim. Logs and watchdog are in parent/max32m*.
