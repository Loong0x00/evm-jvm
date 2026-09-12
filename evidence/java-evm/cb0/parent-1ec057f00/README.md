# Parent CB0 candidate repairs and acceptance captures

Canonical findings/acceptance: JAVA_EVM_MC_CB0_REVIEW.md. Initial candidate1ec057f00,
head/artifact repair4b93a6e6f, final parent Go changes/tests in the acceptance commit.
No worker task status, interrupted transport or preflight was called acceptance.

Initial failures: initial-parent-failures.log and session-fixes.log preserve actual
legal subset/order, marker/link, metadata-before-DB, reopen-install and strict-no-log
failures. The last was a parent freeze mistake: the unchanged engine emits a nested
CheckpointCommitted. Explicit amendment, actual event validation and published-only
receipt were required. pipeline-fixed/parent-durable/cas-metadata/high-offset/
filesystem-errors capture incremental independent gates, not fabricated successes.

One go test attempt failed before compilation with /tmp quota exceeded:
write /tmp/go-build3706010470/b001/_testmain.go: disk quota exceeded.
This line is a retained observation from the tool output, not a full transcript.
We changed ONLY these command environments' TMPDIR to the repo's ignored build path;
no global settings or unrelated files were altered/deleted.

run-final.sh / final-* was the first large combined gate. The API tool's700s timeout
killed the observer while its own test group kept running. Child results ultimately
passed, including source-pin rebuild/VFS391.432s/relocated169.59s high-input test,
but final-watchdog.json DOES NOT EXIST. Do not infer a completed monitored gate or
RSS from its final PASS line. This failure is explicitly retained, not erased.

bounded-final/run.sh is the subsequent COMPLETE watchdog gate:549.345817s,
1202511872B sampled groupRSS, exit0, no20min/4GiB limit hit. It reruns full CB0
including32MiB, full AS0/ZI0/DI0/VFS0a packages, pinned CB0 build/controller/strict
result-page-root checks/vet/relocated durable Java. The separately observed VFS
source-pin rebuild and duplicate relocated32MiB are not redone. Runtime reports
copied here contain generated fixtures/metadata only, not official server bytes.

Archived scripts retain their capture destinations. Use NEW ignored build/output
and log paths on reproduction; do not overwrite historical failures or captures.

Final test-only coverage audit: expanded real process chain to eight phases
(input/index/decode/ready/start/resume/finish/FINAL), and real Linux dir-fsync EINVAL
after actual owned manifest rename. The latter first failed an invented text
expectation, not state behavior; initial process-dirsync-delta.log is retained.
The corrected assertion checks actual renamed sentinel plus exact OS fsync error.
No production hashes changed after bounded-final/. Full CURRENT CB0 package/vet/
relocated tests rerun separately in test-delta*,54.842s/351748096B.
