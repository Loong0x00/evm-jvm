# MC-AS0 parent acceptance review

Status: **ACCEPTED — bounded immutable EVM artifact-byte store** after parent
integration, transport corrections and final-artifact gates. AS0 is not a JVM
profile: VFS0a72aa13f15 remains the accepted Java/filesystem runtime. No ZIP parsing,
DEFLATE, class loading, JVM mount, Minecraft/EULA/listener/Done claim follows.

## Exact artifact

Runtime655bdfe21->fed2c156c; harness77efd3a24->a468c3bcf. Parent changed NO Solidity
or emitted EVM bytes during acceptance, only Go validation/transport/tests.

| artifact | bytes | SHA256 |
|---|---:|---|
| AS0ArtifactStore.sol |7012|2483cd1fadd424773beb4ba1698b79ce36e4aebe26454e2b50c80e50a8a55be1|
| fixed runtime |2831|e7f8e95b0af80bf15e89a01ceb635d8ae858560c606cc86ac3877d8f0de69b13|
| init code |3166|b792253995eafb2ecbc6d7c6c6f28fc0fc03ad0d5073a97f4c62b4ea93dd0f88|

Runtime Keccak c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896;
ABI SHA d3b4e5528a42e10ef0dbcd0b789c8206c976615593dd459690e50d896d2175dd;
combined SHA8e625fc046ebbd2de5a950b9f753347d02d071fd3c1191ac498de14aa353b89b.
Pinned solc0.8.30/optimizer200/viaIR/Cancun/metadataoff build check passed independently
both before and after parent fixes; zero immutable substitutions/link references.

## Accepted behavior

One ordinary EVM CREATE constructs a controller with constructor-only storage owner/
length. Only the controller's EVM CREATE issues immutable STOP||raw data-code pages.
Go never installs controller/page code or supplies a page-byte map. Each page/chain/
sealed commitment is computed in EVM from actual bytes, addresses, order and lengths;
caller Pi/chain values are checked transport assertions. Empty or at-full appends
fail before CREATE; seal requires exact byte length and ceil page count.

Sealed public reads use EXTCODEHASH and EXTCODECOPY, check each touched page, strip
STOP, and return bounded raw bytes. Sealing establishes completeness, not secrecy:
page code is publicly inspectable before sealing. The root is instance-bound, not a
location-independent digest or official whole-JAR SHA256 proof. All test input/output
SHA256 values are host transport checks, never an EVM compression-state claim.

Each disk Append/Seal commits and syncs trie AND code, then publishes/fsyncs the
manifest before returning. Failure before publication reloads the old root; ambiguous
postrename publication poisons the session until reopen. No success root/page/event
escapes publication failure. Reopen verifies pinned code and EVM getters, never
redeploys. Metadata is regular-file/size-bounded and validated before LevelDB; requested
root aliases are allowed while internal links are refused. Initial incomplete stores
without a manifest fail closed and are preserved, not assigned invented roots.

## Parent findings and fixes

The initial package passed its existing worker tests (parent replay2.718s), but parent
checks found omissions in three Go guard areas:

1. Exact ABI validation did not reject fallback/receive or anonymous versions of the
   two events. It now rejects all four non-frozen shapes.
2. Top-level link checks missed nested LevelDB entries: a symlinked state/CURRENT
   reopened successfully. The state tree is now checked for links before LevelDB opens;
   a real owned-file reproducer confirms refusal without modifying the external target.
3. Head shape checks accepted a non-final partial-page cursor in TEST-only altered
   copied state. Head now requires page alignment unless cursor equals declared length.

These do not demonstrate an EVM ownership/cryptographic bypass or remote exploit.
Logs `/tmp/mc-as0-parent-shape-before.log`, `/tmp/mc-as0-parent-head-before.log` retain
failures; `/tmp/mc-as0-parent-final-probes.log` retains successful corrected controls.
No workaround changed EVM code/gas/accounting or any accepted profile.

## Sixteen coverage groups and final evidence

| group | parent-reviewed final evidence |
|---|---|
|01|init/runtime/ABI pins, defensive embedded copies, exact ABI/no fallback/no anonymous events|
|02|ordinary CREATE; multiple lengths/owners return byte-identical runtime; zero/max/+1 constructor precedence|
|03|issued page addresses follow controller CREATE nonce, exact STOP||raw code; page calls stop rather than execute payload|
|04|independent init/page/code/ordered/sealed root computation, not imported catalogue/hash authority|
|05|owner/cursor/order/expected-commitment refusals and valid control|
|06|one-byte/8193/exact-page/full32MiB; at-full-before-seal empty append rejected without mutation|
|07|early/wrong-owner/wrong-chain/duplicate seal and append-after-seal refusals|
|08|zero/end/overflow/4096/+1 and cross-page reads compared with exact raw bytes|
|09|metadata index/cursor bounds; TEST-only changed copied page code causes EVM error14, original remains readable|
|10|post-CREATE wrong-Pi/OOG rollback of nonce/child/code/count/root/logs; retry issues same child|
|11|full4096pages/32MiB memory AND disk; parent independently reads back ALL32MiB through8192 EVM reads|
|12|real new-process reopen at2048 pages and resumed upload with unchanged earlier page addresses|
|13|sealed reopen/code/getter/root identity, full disk test also passes from a relocated trimpath executable|
|14|parent counted actual SyncKeyValue per append/seal and checked each published manifest; injected failure returns gas only and old-root retry succeeds|
|15|namespace/initial fail-closed/metadata bounds/owned temps/root aliases/internal links, including nested CURRENT fix|
|16|final patched package/vet/repro watchdog and unchanged accepted VFS/core paths|

Final entire package: **PASS4.096s**, external4.358s, **282877952B** observed peak group
RSS, exit0/no watchdog limit hit; `/tmp/mc-as0-parent-final-suite.{log,json}`.
Focused parent tests PASS1.365s; final vet and pinned build check pass. The relocated
`go test -c -trimpath` executable, run in its own directory without source/compiler
fallback, completed the full32MiB disk/new-process test in1.63s. Logs:
`/tmp/mc-as0-parent-relocated.log`, `/tmp/mc-as0-parent-final-repro.log`.

Both production memory and PER-CALL durable disk controls measured:
controller CREATE611673gas; append aggregate **7289399396gas across4096 calls**;
max single append1830926gas; seal34194gas; cross-page4096B read24835gas.
The parent all-byte readback control's transport SHA256 is
f0c2d9e6b1bf2c241f831969ef8a26f41aece0cb3625fb4fb9ea5751241d0269;
all8192 EVM reads used139689984gas aggregate. This is not whole-input EVM SHA256.

Do not mix those gas totals with the runtime-worker/prototype's7.232B batch-trie
replay: publication/reload cadence and committed-storage gas context differ. Production
transport commits/reloads EVERY mutation, in memory as well as on disk. Neither
sum is one-call gas, instruction count, wall-time prediction or signed intrinsic gas.

Accepted VFS0a full control passed again: external367.334s/278855680B groupRSS,
`/tmp/mc-as0-parent-vfs-control.{log,json}`. Protected accepted runtime/continuation/
stock/core paths have no diff from72aa13f15; no global full-geth CI claim is made.

## Limits and next boundary

32MiB/artifact,8192B/page,4096 pages,4096B/read; controller<=24576B,init<=49152B,
data page<=8193B.100M/30s ordinary calls,1B/120s explicit boundary;20min/4GiB gate.
Ordinary component CREATE is proven here, NOT whole-JVM signed deployment. No AS0
checkpoint/Java-step counter is invented; state lives in EVM code/storage/trie.
VFS0a64KiB mutable bytes/1MiB checkpoint/320KiB code limits remain unchanged.

Run `make java-mc-as0-test java-mc-as0-demo`. The demo is generated opaque bytes,
not Minecraft. Next ZIP/resource interpretation must execute against the committed
raw store in EVM; host extraction/catalogue/class lookup cannot become authority.
