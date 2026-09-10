# MC-ZI0 parent acceptance review

Status: **ACCEPTED — bounded EVM ZIP metadata/index component**. This is NOT
DEFLATE/plain CRC verification, ZipFile/ClassLoader, class loading/execution or
Minecraft startup. VFS0a72aa13f15 remains the accepted JVM/filesystem profile;
AS064ea6b62f remains the accepted immutable byte-store dependency. No EULA/listener/
world/Done claim, no host catalogue/extraction authority, no GitHub push.

## Exact accepted runtime

Sol delivery549e0e809/119935802 ->ab1a0b88e/d10d9700d. No parent production Solidity
or emitted-byte changes were needed. Pinned solc0.8.30+commit.73712a01.Emscripten.clang,
optimizer200,viaIR,Cancun,metadataoff; exact18functions+constructor+ZI0Error, no events,
fallback/receive/immutables. Controllers/pages use ordinary EVM CREATE.

| item | bytes | SHA256 |
|---|---:|---|
| ZI0ZipIndex.sol |17317|78329d1610c0ba180c7e267989bf36190a9d9eb536020acce42234066a94a2ae|
| runtime |9177|74ea23889368b3381843e39bb2caf53a66de8dbfdb3dc58dc4a066c97a33d7a3|
| init (plus64-byte args=9937 total) |9873|f3d6d4614cf916cc4be4cd1ef58212642d829d63b710cea9d140181bafd00870|

Runtime Keccak0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77;
combined artifact SHA424246923fd5a022ec7dabda19f6847ad36896d5fd34ca8598e7c3f32719443e;
canonical ABI-schema SHAd4cbb83eb725e27c6d16d32d333a6b576af47fde093a7d071bc01ff69980b9b6.
The raw ABI file and canonical ABI hash are different representations; do not
interchange them. Assets live in runtime/combinedartifacts/ZI0ZipIndex.json.

The accepted protocol is JAVA_EVM_MC_ZI0_PLAN.md. The EVM binds fixed AS0 code,
address and sealed content; discovers a bounded unambiguous EOCD, parses exact
CEN/LOC/name/method/flags/extra/descriptor framing, rejects overlap, and builds a
2-slot-per-entry index and rolling/final commitment. Host expected roots/cursors
are assertions, not imported metadata. Final entry/lookup checks full name bytes.
Opaque binary/NUL/dot/slash names receive no host/VFS normalization. CRC/plain size
are metadata only. ZIP64/preamble rules are explicitly narrow, not ZIP conformance.

## Integrated Go defects and corrections

Initial Goacd40faa3/8d076105f had only synthetic-stub compilation/vet. Parent found
fresh disk Open omitted AS0 CREATE, an extra ABI event was accepted, and copied-state
Head checks missed page-count truncation/partial cursor/wrong owner. Initial normal
disk pipeline and parent negative tests really FAILED; they remain in Git under
`evidence/java-evm/zi0/production-14c565614/`. No stub build was counted as acceptance.

Sol follow-up27cb00967 ->095a3d407 supplied real artifact tests and corrected fresh
initial publication, exact artifact/compiler/schema/pins, head decoding/binding/caps,
publication recovery/poisoning, namespace/metadata/link and lifecycle checks. Parent
reran it against the real9177B artifact; all earlier failures now reject/pass correctly.

Parent acceptance then strengthened rather than merely trusting that delivery:

- Replaced broad1B allowances in ordinary test paths with actual100M calls and
  reran the entire suite. API boundary ceiling remains1B; no cap increased.
- Counted real underlying SyncKeyValue calls, checked every manifest/root, and
  injected failure AFTER real DB sync. Failed append exposed gas only and restored
  the old actual trie root; retry reused the same ordinary child address.
- Added full20554-entry true NEW-PROCESS resume at entry10240. The child performs
 163 actual synced mutations (162 remaining scans+finish), then parent reopens and
 verifies identical final roots and first/middle/last named lookups.
- Removed a hidden unreported readonly content getter from each manifest publish.
  Transport caches ONLY the immutable content assertion after the successful pinned
  EVM constructor proved it; durable reopen revalidates it with EVM getters. It is
  not a ZIP cache or an alternate guest authority. Failed unpublished CREATE clears
  both route/content; uncertain publication remains poisoned. All tests reran after
  this production Go change. Mutation gas now has no hidden publish-getter call.

## Sixteen final gate groups

| group | actual final coverage |
|---|---|
|01|pinned source/init/runtime/combined/ABI/layout/compiler, defensive copies, exact surface, owner0 refusal|
|02|ordinary AS0 creation/upload/seal then separate ZI0 CREATE, content/code binding, constructor rollback/retry|
|03|EOCD/prefix/empty/ambiguity/ZIP64 policy, maximum tail and dense candidate controls|
|04|CEN/LOC flags/methods/extras/descriptors, genuine geometry23/27, descriptor/CD boundary|
|05|opaque names and cross-batch duplicates; isolated TEST-only bucket redirect exercises actual full-byte mismatch19|
|06|independent record/root derivation, q1/q64 identical index and final state roots|
|07|owner/CAS/phase/units/EOF refusal, mid-batch failure and post-write direct OOG/retry (runtime replay plus session tests)|
|08|final-only entry/lookup, negative bounds, raw AS0 byte ranges; no plaintext claim|
|09|20554/exact2100796B CD durable823 publications;32768/exact4MiB CD/+1;64 simultaneous max fields and tiny-TLV extras|
|10|exact32MiB raw ZIP and genuine high25-bit packed offset lookup|
|11|every mutation commit/reload, actual SyncKeyValue count and manifest/actual-root agreement|
|12|fresh processes across mid-upload/sealed-AS0/BOUND/STAGING/FINAL; full20554 true child continuation, no redeploy|
|13|strict bounded metadata before LevelDB, pinned code/context/identity, namespace/incomplete/temp/internal-link rejection|
|14|prepublication old-root recovery and retry, postrename poison/reopen, gas-only failed-publication receipts|
|15|trimpath relocated executable from its own directory; copied-state views and concurrent stale-CAS serialization|
|16|final full suite/vet/repro under watchdog, AS0 regression, unchanged protected older/core paths|

## Final measurements and durable evidence

Evidence directory: `evidence/java-evm/zi0/transport-repair-27cb00967/`.
Final full suite external **20.546s /519057408B** sampled process-groupRSS, exit0,
no watchdog limit or skip. `final-suite.{log,json}` includes the real runtime package
and all transport/parent tests. `final-repro.log` and `final-vet.log` pass. The relocated
trimpath executable passes multi-process tests from its own directory (`relocated.log`).
AS0 regression passes external4.111s/288174080B (`as0-regression.{log,json}`).
Older runtime/continuation/stock/core/consensus/crypto paths have no change from64ea6b62f.
This is not a claim that every upstream geth package or all historical gates reran.

Final20554-entry synthetic transport run (4057736B,496 AS0 pages): AS0 CREATE611673;
append881638867 sum/max1830926;seal34194;ZI0 CREATE1935216;discover69092534;
322 scans2387173374 sum/max7478124;finish46129.823 separate successful publications,
not a batch. Observed disk41513629B is LevelDB/layout-specific, not a state-format size.
Capacity32768 uses512 scans4470603173 sum/max8741182. Exact32MiB upload uses4096
appends7289399396 sum/max1830926. These are mutation gas sums, not one-call gas,
instruction counts, signed intrinsic gas, wall-time predictions or Java heap capacity.
Views are separately reported. Distinct owners/input shapes/split points bind distinct
roots, so not all historical prototype gas/root figures are interchangeable.

All32MiB/8192-page/4096-read/32768-entry/4MiB-CD/256-name/1024-extras-comments/64-unit,
100M30s ordinary/1B120s boundary/20min4GiB limits remain. ZI0 does not expand VFS
mutable64KiB/1MiB checkpoint/320KiB code or accepted Java heap quotas.

Run `make java-mc-zi0-test java-mc-zi0-demo`. Demo is a generated two-entry archive,
not Minecraft. Next dependency is EVM inflation/output-bound/CRC verification over
exact indexed compressed bytes, then Java loading. The original official JAR was
only statically inventoried in these acceptance gates; no official-JAR index/execution
or whole-file EVM SHA256 proof is claimed by this acceptance.
