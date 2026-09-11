# MC-DI0 bounded resource decoder — parent acceptance

**ACCEPTED within the frozen bounded DI0 profile.** This is a resource decoder,
not a JVM/ClassLoader/Minecraft execution milestone. The first Minecraft readiness
target remains unchanged vanilla1.12.2 superflat with its own genuine Done.
At this acceptance checkpoint no official JAR entry has yet been inflated.

## Identity and boundaries

Runtime DI0Resource14978B SHA256
8c309455d3b0817725cd775f909abc2477b39fed6e18235114737480b05e17b0;
Keccak946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37.
Init17216B SHA604d6a515fcb5efb539f998987ddba94c7f1e1d1fe3e712a5b95606bc1dab576;
maximum complete init17600B. Source18513B SHA
682d8243a6a0671f151316c8bce0a220ec1934205ca5bb4144a4d635463b4470.
Combined artifact72773d5c53533969a6b0d0a1391513330affb11b4cdf300fa4c115bab23613ca;
canonical ABI d44a67c73dd94c463dcb25ce00a8b6814967f3a1f37ed0c60770ce818f63f7ee;
layout5c07eef01462da0f9685e37dff3bd65c1e10769b82375963973ff41743ecaffc.
Final Go session.go SHAd18ffc4427b3ba31bb2a7e12916d695bc9f16b14ca83ddf8739d69e148cfd23e;
di0.go SHAd5c43368f3e0df4c6f049acfba4005b612a7e55d8cc2f503c110182a2976210c.

Pinned solc0.8.30+commit.73712a01.Emscripten.clang,opt200,viaIR,Cancun,metadataoff.
Exact33 functions+constructor+DI0Error, no events/fallback/receive/immutables.
Ordinary EVM CREATE for controller and output pages, no host SetCode/decoder/page
installer. EVM gets names/ranges/metadata from accepted ZI0 and bytes from AS0;
all Huffman/DEFLATE/CRC/output decisions remain in EVM. Go only transports/persists.

DI0-only262144B plaintext/entry,32768 lookback,32-byte copy actions,8192B pages<=32,
4096B reads. AS0 input32MiB and accepted ZI0/JVM/VFS limits unchanged. The new DI0
cap is not a JVM heap/class-image/VFS quota increase. Method0/raw-method8 only;
Java8-measuredHLIT<=286/HDIST<=30, ignored terminal unused bits but rejected whole
trailing byte. This is intentionally stricter than raw Inflater/ZipFile range handling.

Explicit work contract from b67ed0865: requested units1..128 is an upper bound;
first action attempted, later actions yield below25M remaining gas with positive
actual progress. Ordinary100Mgas/30s tests, explicit smaller failure probes and
separate1B/120s allowance; no hidden retargeting to smaller quantums or raised gas.
Largest observed tested step75607496gas is NOT a universal performance theorem.
FINAL reads use EVM-created page code, not staging; CRC/length/exact range first.
Empty output has zero pages/nonzero resource commitment. Resource F != trie root.

## Independent parent corrections and preserved failures

Earlier optimization still OOGed with64 empty dynamic blocks/q128. Parent's explicit
bounded-yield refinement resolved this without changing opcode/gas accounting.
Parent production integration then found a reachable transport bug: a legal stored
DEFLATE header holds LEN65535/distance0, but Go applied the Huffman258/matched-distance
rule to it. ac454a910 fixed validation by mode and retained strict copied-state
negative controls. Its original failing positive test is preserved.

The worker's claimed fresh-process Session test was actually same-process reopen;
it was renamed. Parent added14 real child-process stages, not credited that label.
An additional reviewer was provider-blocked and delivered no result; not credited
or retried. Parent performed the additional checks directly.

Final parent metadata test kept the DB locked while submitting invalid manifests.
An empty-trie root incorrectly reached DB open; it now rejects with other impossible
metadata BEFORE DB access. The old failure is preserved in metadata-first.log.
All corrections are Go-only; production Solidity/artifact bytes remain unchanged.

## Frozen sixteen-group acceptance map

1. Exact artifact/schema/compiler/source/runtime/init/layout/dependency pins, defensive
   embed, caps and ordinary CREATE: final-artifact-check.log, runtime/package tests.
2. Separate AS0/index/decoder lifecycle, owner/name/root/phase/CAS and constructor
   rollback: package tests plus final runtime reconstruction controls.
3. Method0/stored/fixed/dynamic, overlapping matches/history32768/wrap, alternate
   length258 and Java8 API distinctions:37 baseline+29 tree cases, generated oracles.
4. Reader refill/bit/cache transitions and stored/fixed/dynamic tables: those cases
   and actual stored65535/dynamic90309 subprocess chains.
5. Invalid counts/trees/repeats/reserved symbols/distances/CRC/length/end: strict
   nonzero exact error expectations in final reconstructed runtime drivers.
6. Actual requestedq1..128,64/129 repeated dynamic headers, positive progress/no
   valid OOG: five complete sweeps on final artifact, plus production Session sweep.
7. Six same-binding q1/q128 pairs and five sweeps compare output/input/work/CRC/pages/
   resource/trie roots. Different artifacts' trie roots are not conflated.
8. Parent production transport0/90309/158794/exact262144 and+1 constructor refusal,
   complete EVM reads, opaque NUL/non-UTF8 names. No unrelated quota increase.
9. Independent B/O/PC/P/F computation from trusted generated input/oracles, empty
   and multi-page cases, all page/read boundaries; full32MiB high-offset disk input
   with4096 pages and8192 actual EVM read calls. DataStart33554313, actual output.
10. Direct90K first-action OOG after a completed CHANGED SSTORE, actual root comparison
    before host restore; late EVM page CREATE error30 and same-child retry. No trace
    state/bytes used as recovery or output authority.
11. Real underlying SyncKeyValue wrapping BEFORE initial CREATE:14 completed syncs
    in both memory and disk across every mutation family, every success reloads and
    disk manifest matches BEFORE receipt. Views/failed EVM calls do not sync.
    Full32MiB production Session observes4104 post-Open syncs (initial Open excluded).
    Standalone runtime driver's60-publication result remains a separate measurement.
12. Fourteen distinct OS processes cover mid-upload/discovered index/stored header
    or dynamic cache/VERIFIED/first page/FINAL/full-read-only reopen. No re-CREATE;
    exact expected trie roots on reopen. Empty/multi-page semantics retained.
13. Namespace/incomplete-directory/internal CURRENT links and bounded regular
    metadata;14 wrong context/format/owner/length/routes/name/code pins/root cases
    reject BEFORE DB open. Copied-state tests are not live ownership-bypass claims.
14. Actual code/trie sync followed by injected failure; real OS CreateTemp/rename
    errors; failure hooks AFTER real temp create/write/fsync/close and directory
    fsync. Prepublication old-root/routes/nonce/retry/diagnostic preservation;
    postrename poison/exact reopen. These injected post-operation failures are not
    claimed as physical disk damage tests. Failed publication receipts contain gas
    only, no logs/revert/created address/success root.
15. Concurrent stale CAS, copied views, Close/poison, relocated trimpath embedded test
    executable. Child CWDs have no source/runtime files. Existing source is not used
    for execution; generated fixture oracles remain clearly test-only.
16. Final combined pinned build/package/vet/fresh runtime reconstruction/accepted
    AS0+ZI0 regression/relocated parent/fixture run under one20min4GiB watchdog:
    **253.599s,491962368B sampled peak groupRSS,exit0,no limit hit**. Package51.577s.
    Protected core/params/JVM/localcontinuation/AS0/ZI0 paths unchanged. Core/params
    previously independently matched pinned geth upstream. No new full VFS/legacy
    aggregate execution claimed for a component that does not alter those paths.

Sources/tests: jvmevm/artifactstore/di0/ and runtime/.
Parent evidence: evidence/java-evm/di0/parent-58b24981f/ and
 evidence/java-evm/di0/parent-final-ac454a910/ (tracked scripts,reports,hashes,failures).
Earlier preflight and worker captures stay historical, not final acceptance evidence.

Reproduce component: `make java-mc-di0-test`; generated resource fixture only:
`make java-mc-di0-demo`. Full reconstruction script in runtime-candidate/replay.sh
requires a fresh ignored output directory. Whole-gate command is run-final.sh.
Use new log/output names rather than overwrite archived acceptance captures.

## Next dependency, not an implicit capability claim

Now permitted: parent transport-integrity check of the pinned original server JAR,
opaque AS0/ZI0 upload/index and actual EVM decoding of selected resource/class names.
Archive only metadata/hashes/reproducer, not copyrighted input/output payloads.
Only after that: bounded lazy class loading/linking/initialization and startup-needed
platform work. No host Java evaluator, stubbed server logic, fabricated Done, EULA,
listener/world, standard-chain full-JVM claim or implicit GitHub push authorization.
