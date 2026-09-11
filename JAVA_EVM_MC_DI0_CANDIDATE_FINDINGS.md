# DI0 production candidate — parent integration findings

Current status: DI0 accepted by JAVA_EVM_MC_DI0_REVIEW.md. The freeze/candidate
record below is historical; its failures and scope decisions remain preserved.

Status: **integrated, NOT ACCEPTED**. Frozen plan remains JAVA_EVM_MC_DI0_PLAN.md.
Runtime worker fbe0f2381/04b4f8157/1a4c24205 integrated124d93f8a/b46f830b5/fb6e267b3;
transport89de316b9/089db4d7b integratedf4b74b531/58b24981f. All write sets checked.

## Pinned runtime independently rebuilt and replayed

Production DI0Resource source18513B SHA682d8243a6a0671f151316c8bce0a220ec1934205ca5bb4144a4d635463b4470;
init17216B SHA604d6a515fcb5efb539f998987ddba94c7f1e1d1fe3e712a5b95606bc1dab576;
runtime14978B SHA8c309455d3b0817725cd775f909abc2477b39fed6e18235114737480b05e17b0;
runtimeKeccak946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37;
combined72773d5c53533969a6b0d0a1391513330affb11b4cdf300fa4c115bab23613ca.
Maximum complete init17600B. Production v1 roots/constructor name checks/dependency
checks are the scoped differences from the independently checked parent prototype.
No new Solidity change by parent. Exact33functions+constructor+DI0Error retained.

Parent pinned build check3.017s/259997696B; integrated package tests36.544s/271785984B.
Fresh standalone final-artifact reconstruction/replay150.415s/324562944B:
37 original +29 tree/Java8 +4 enlarged64-header cases,6 same-binding q1/q128 pairs,
5 exhaustiveq1..128 sweeps including129headers,60-publication/four-process prototype
persistence and dynamic-cache resume all pass. Actual completed changed-SSTORE OOG
proof at90000gas, not the worker's uncounted70000 trial; page-CREATE failure and
same-child retry pass. Maximum observed step75607496gas; not a universal bound.
Evidence: evidence/java-evm/di0/parent-58b24981f/.

## Finding1 — legal stored-block state rejected by Go Head/Open

The Go validator treated EVERY pendingLength as a Huffman match length<=258 with a
nonzero distance. Raw stored-DEFLATE actually holds LEN up to65535 in that field,
with distance0. EVM step(0,1) successfully published the valid stored header; then
Head refused it as `DI0 pending copy is noncanonical`, and Open used the same
validator. This is a reachable legal-state transport bug, not copied-state damage.
A parent hand-built65535-byte stored stream is independently accepted by Go flate;
the pre-fix strict positive test failed and is preserved as stored-head-failure.log.

Parent fixes session.go validation by mode: method0 has no block/pending state;
stored mode has uint16 LEN, distance0, fixed=false, byte alignment; header boundary
has no pending copy; Huffman mode retains258/32768 and paired/non-before-output
constraints. Do NOT compare stored LEN with declared remaining output/input in Go:
the EVM must execute and report genuine later overrun/truncation, not a host decoder.
Added phase1 publicationRolling==zero guard. Seven labeled COPIED-state negative
controls retain strict mode constraints; they are not live ownership-bypass claims.

## Finding2 — same-process test mislabeled as fresh-process

The transport worker test `...DurableFreshProcessStages...` only called Close/Open
inside ONE process. It is now named `...DurableSameProcessStages...`; archived worker
captures remain unchanged. The standalone runtime driver really used subprocesses,
but that did not establish the new production Session's process-reopen behavior.

Parent added two actual SEVEN-process chains, stored65535B and dynamic90309B:
mid-upload -> discovered index -> stored header/dynamic table -> VERIFIED -> first
output page -> FINAL -> full read-only FINAL reopen. Fourteen distinct child PIDs,
expected trie root on every reopen, no repeated CREATE, correct resource/trie root
labels, full EVM output byte reads. Child working directories contain no source
checkout/runtime files. Final repeated stage has identical resource AND trie roots.
Stored final: work2049/pages8; dynamic: work3541/pages12.

## Additional parent controls

- Exact output0/90309/158794/262144 and constructor+1 refusal through production
  Session, opaque NUL/non-UTF8 names, complete EVM reads, EOF/+1/read4097/page bounds.
- Late EVM output CREATE failure exactDI0Error30 with no disk sync; successful retry
  creates the same child address. Real underlying SyncKeyValue counter validates
  actual sync THEN error, after-trie, before-manifest and after-rename failures.
- Prepublication failures preserve manifest/actual trie root/controller nonce and
  absent child; publication errors return gas only. Postrename failure poisons
  APIs; exact reopen observes the genuinely published page and finishes normally.
- Parent suite including existing tests passes45.126s/273592320B; vet passes.
  Trimpath test binary run from a separate source-free build directory, including
  child process chains, passes9.856s/347553792B (including compilation).
- Accepted AS0/ZI0 build checks/full tests pass30.290s/544030720B. Core/params match
  pinned geth upstream; JVM/localcontinuation/AS0/ZI0 files unchanged from16f8b8b43.
  No claim of a new full VFS/legacy aggregate run.

Each cited gate uses the20min/4GiB outer watchdog; EVM ordinary calls100Mgas, explicit
small-gas negative probes labeled. No cap increase or host-decoded output authority.

## Still pending before DI0 acceptance

Complete the frozen16-group parent checklist, particularly remaining metadata/
routing/head consistency boundaries, broader per-mutation durable publication counts
and filesystem failure points, and full input high-offset transport coverage. The
60-publication number above belongs to the independently replayed runtime DRIVER,
not the newly implemented production Session; do not merge those claims. Final
review/checkpoint and Make/demo integration remain pending. No class loader yet.

An independent additional transport-review worker was provider-blocked and delivered
NO result/commit; its worktree remained clean. It is not credited as verification
and was not retried/bypassed. Findings/tests above are separately performed by the
parent. No active implementation/review worker remains at this checkpoint.

No official JAR inflation, Java/ClassLoader/Minecraft execution, EULA, listener,
world or genuine Done. No subsequent GitHub push authorization.
