# DI0 parent output/persistence replay — valid-batch gas blocker

Status: **NOT FROZEN / NOT ACCEPTED**. Sol output-page preflight0218f76f5 integrated
46a111e7c. Terra's separate fixture task was provider-blocked and did not deliver a
completed commit; its uncommitted worktree is preserved but contributes NO acceptance
result. Parent independently wrote and executed the additional generated Go/Java8
checks below; no provider restriction was bypassed or marked successful.

## Independent replay of the delivered preflight

Pinned recompilation produced the identical artifact SHA
3344a2ab8132397e6cd2d1fcbcda3aa230fb215adc3232f5b63b9d8c6dcef4a9:
source16442B/d117856b870e571eac2481ed0daf59623e0b8e3a40e7eddb2192e5d1ab54be5b,
runtime12885B/64342a799364a4687cd53b566ebffb4b45a751e3c2892a3598c9e53ee42a9b3a,
init15094B/1aaf7a67b898aa547cc2be1841b823402dc5043ec0cfb9dd9e21bb2ec42f937e.
Maximum complete init with256-byte name15478B remains below49152B.

All37 fixture outcomes, gas, roots, q1/q128 equality and controls reproduced;
durable sequence/gas/root fields also matched after excluding child PIDs/RSS/time
and LevelDB disk size. Parent gate36.119s/105246720B sampled groupRSS, exit0/no
20min4GiB limit. Four real processes resumed sequences20->48->49->60->60,
phases VERIFIED->mid-publish->FINAL->read,90309B/12 pages,60 mutation publications.
Disk1401922B versus worker1401921B is filesystem layout, not an encoding invariant.
Persistence report's `finalRoot` is its final TRIE root, not DI0's resource finalRoot;
those concepts must be named separately in production.

Parent evidence under `evidence/java-evm/di0/parent-0218f76f5/`. This replays the
disposable driver, not a production transport/metadata/publication-failure gate.
No official JAR entry was inflated or Java server code executed.

## Parent takeover of tree/oracle coverage

Parent's generated22-case set uses new Go bitstream builders and the existing
HOST-TEST Java8u504 oracle. Go flate is secondary. No host trees/offsets/decoded data
are supplied to the EVM; the raw generated ZIP is indexed through accepted AS0/ZI0.
The parent wrote these probes independently rather than counting the failed Terra
attempt. Source and small generated raw streams/ZIPs are retained under trees*/.

Positive controls agree across EVM and Java8 Inflater/ZipFile/ZipInputStream:
singleton EOB/empty distance, unused singleton/complete distance trees, repeat16/17/
18 crossing the literal/distance alphabet boundary, all256 fixed literals and the
Java8-accepted length284 extra31 encoding of258. Negative fixtures reach exact DI0
codes19 missing EOB,20 oversubscription,21 invalid incomplete LL/distance,18 repeat
overrun and22 attempting a match with an empty distance alphabet. These controls
extend the earlier count/padding/range comparisons without retargeting their oracles.

### Three valid-stream ordinary-budget counterexamples

A complete286-symbol literal tree with a depth15 code assigned to literal A,
a complete30-symbol distance tree, and300 A bytes is valid under all three Java8
APIs and Go flate. A second valid fixture has32 consecutive empty dynamic blocks,
max-count header framing, and a final EOB. Blocks are packed continuously by bits,
not concatenated with invented byte padding.

| generated stream / requested units | actual EVM result at100M |
|---|---|
|depth15 full tree, q1|valid300B,302 actions, max15970851gas|
|depth15 full tree, q64|valid300B, max58290576gas|
|depth15 full tree, q128|OOG,100000000gas; no work/output/page/final result published|
|32 empty dynamic blocks, q1|valid empty result,64 actions, max16074956gas|
|32 empty dynamic blocks, q8|valid empty result, max79311435gas|
|32 empty dynamic blocks, q64|OOG at100000000gas|
|32 empty dynamic blocks, q128|OOG at100000000gas|

Thus lowering128 to64 does NOT fix the whole issue. A finite ~16M atomic header does
not imply128 actions fit100M. Rebuilding decoder tables/arrays inside repeated symbols
and dynamic headers also accumulates per-call EVM memory cost. The worker's10.946M
header and87.732M single-step samples were not global worst-case bounds.

`trees-final/evm.json` and `trees-final/java8.json` capture22 cases. The STRICT gate
exits1 for those three valid-stream OOGs; they are NOT semantic refusals or successful
inflations. Earlier observer runs exited0 after recording observations; do not count
those exits as a passing budget gate. The OOG states remain at work/output0 and no
final plaintext is harvested. Smaller-quantum valid results are separate real runs.

## Scope of the next pre-freeze performance work

ONE Sol/high worker owns ONLY JAVA_EVM_MC_DI0_BUDGET_RESULTS.md (aim<=220lines),
`evidence/java-evm/di0/budget-preflight/` and ignored
`build/java-diff-mc-di0-budget-preflight/`. No peer/accepted/production/core/settings
changes, Fast/priority, spawning, push, official input inflation, Java/Minecraft/
EULA/listener work. Only one Solidity writer. Key source/results in owned tracked
paths, never solely /tmp. This is a new bounded performance task, not a retry of
Terra's blocked provider request.

Optimize the disposable EVM decoder, keeping actual byte/tree/CRC/lookup decisions
inside EVM and all current format rules/output-page ownership unchanged. Prefer
building canonical decoder structures once per block/header or reusing bounded
per-call tables instead of reconstructing them for every symbol. Fixed-code direct
lookup is acceptable if all fixed symbols and reserved-code behavior are verified.
Code-length-tree decoding should likewise avoid fresh arrays for every length token.
No host canonical tables/decoded map, no output-prefix fabricated from OOG traces.

Target the unchanged public upper bound1..128 actions with real100M ordinary calls
for the delivered37 cases and all parent22, including repeated expensive headers.
Do not silently switch advertised/requested units to8/64, use1B, or classify valid
OOG as success. If an explicit EVM gas-aware early-yield rule or changed work-unit
contract is required, propose and measure it separately, preserving positive
progress, CAS, determinism and exact q1/larger output/state equality; parent must
approve a scope change before freeze. No accepted quotas may change.

Keep256KiB output as the explicit unaccepted DI0 proposal,32KiB maximum lookback,
8192B output pages/at most32 pages, final-only read<=4096, actual EVM CREATE,
CRC+length/exact compressed range, Java8-compatible counts<=286/30 and ignored
terminal unused bits. Full bounded staging is allowed; do not force a ring buffer
without a measured reason. If caching adds state, clear/rebuild it correctly across
stored/fixed/dynamic transitions and true new-process resumes.

Measure worst legal/malformed headers, long-code literals, mixed and repeated
blocks, changed history across32768,256KiB output, q1/q128 equality, output pages,
post-write OOG and failed page issuance/retry, and all60-publication/four-process
persistence controls. Add alternate tree shapes/symbol order so optimization is not
fixture-specific. Runtime<=24576B/fullinit<=49152B,100M30s ordinary/1B120s explicit
boundary only, whole20min4GiB, accepted AS0/ZI0 inputs32MiB/8192/4096 unchanged.
Record actual max call/aggregate gas, work/call counts, CRC/output/page/state roots,
code/RSS/time/disk and exact failure outputs. Do not assume byte-identical final trie
roots with OLD code; q1/q128 equality must hold on the SAME new artifact/binding.

Retain old failed measurements, new source/artifact pins and strict replay commands.
Parent independently validates before any production ABI/transport freeze. No DI0
acceptance, official inflation/ClassLoader or Minecraft readiness follows here.
