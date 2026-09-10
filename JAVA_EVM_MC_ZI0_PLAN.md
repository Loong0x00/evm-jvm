# MC-ZI0 production plan — implementation freeze

Status: **ACCEPTED IMPLEMENTATION**; see JAVA_EVM_MC_ZI0_REVIEW.md. Original freeze followed independent parent
preflights. See JAVA_EVM_MC_ZI0_IMPLEMENTATION_PREFLIGHT.md. Parent reproduced
2bb841b0c in18.423s/269950976B sampled groupRSS (identical54 controls), exact32MiB
high-offset ZIP, and strengthened Luna probes in18.730s/277540864B (54 retained+
12 extra probes,7 measured runs). Key evidence is Git-tracked under
`evidence/java-evm/zi0/`. This authorizes only the disjoint implementation write
sets below, not production acceptance or additional runtime capabilities.

ZI0 is ONLY an EVM ZIP directory/index/committed compressed-range component. AS0
64ea6b62f remains accepted byte storage, VFS0a72aa13f15 accepted JVM/filesystem.
No DEFLATE/plain CRC/ZipFile/ClassLoader/class execution/Minecraft/EULA/listener/
Done claim; first future readiness workload is unchanged vanilla1.12.2 superflat.
No host ZIP parser/name catalogue/offset map/class extraction may become authority.
No accepted artifacts/core/gas/consensus changes or automatic GitHub push.

## Namespace and budget

Package `jvmevm/artifactstore/zi0`, contract `ZI0ZipIndex`, runtime subtree `runtime/`.
Separate disk marker `JVMEVM-MC-ZI0-DISK-STORE-1\n`, manifest format1. Never reinterpret
AS0/VFS/older stores as ZI0. AS0 dependency uses its exact accepted embedded init,
runtime, ABI and fixed code hash; no accepted AS0 source changes are necessary.

Pinned solc0.8.30+commit.73712a01.Emscripten.clang, optimizer200,viaIR,Cancun,
appendCBOR=false/bytecodeHash=none. Ordinary EVM CREATE for BOTH controllers and
all AS0 pages. ZI0 runtime<=24576B, complete constructor input<=49152B (includes
64-byte args), no immutables/link references. No host SetCode/page installer.

Keep AS0 raw artifact1..33554432B,8192B/page,4096pages,4096B/read. ZIP limits:
32768 entries,4194304B CD,256B raw name,1024B each central/local extra and entry
comment,65557B EOCD tail,scan1..64 entries/call.100M/30s ordinary;1B/120s explicitly
labelled boundary; whole gate20min/4GiB. Measured view/runtime gas is not a blanket
upper bound. Failed limits block acceptance, not permit silent increases. ZI0 is
storage/code/trie state, not Java checkpoint/heap capacity; VFS quotas stay unchanged.

## Exact proposed Solidity surface

```
constructor(address sealedAS0, bytes32 assertedContent)
discover()
scan(uint32 expectedEntry,uint32 expectedCursor,bytes32 expectedRolling,uint16 units)
finish(uint32 expectedCount,uint32 expectedCursor,bytes32 expectedRolling)
entry(uint32 index) view returns(bytes rawName,bytes32 packedRecord)
lookup(bytes rawName) view returns(bool found,uint32 index,bytes32 packedRecord)
owner() address; store() address; content() bytes32; length() uint32;
phase() uint8; eocd() uint32; cdOffset() uint32; cdSize() uint32; count() uint32;
nextEntry() uint32; cdCursor() uint32; rolling() bytes32; finalRoot() bytes32;
```

All mutators/constructor nonpayable;13 scalar getters view. Exactly18 functions,
constructor and `ZI0Error(uint256 code)`, no events/fallback/receive/other callable
surface. The names/types/order above are ABI authority; runtime/getter aliases,
measurement comparator methods and host import/reset interfaces are not allowed.

Owner/store/content/length are constructor-only STORAGE bindings, fixed runtime
identity across instances. Explicit nonzero owner check FIRST (error1), then code2,
sealed/nonzero asserted-content/length binding3. Any nonzero creator may bind a public
sealed AS0, irrespective of AS0's upload owner. Address/root/code identity never
rebinds. Code hash is exactly
c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896.

Every mutator checks owner, phase, then AS0 binding; consumers check binding then
FINAL phase. Getters are diagnostics, not publication authority. Phases0 BOUND,
1 STAGING,2 FINAL. Discover once; scan CAS is ALL entry/cursor/rolling fields.
Units0/>64 OR no remaining entries after correct CAS reject11 (no at-end no-op).
Finish requires scanned count, exact CD cursor/end and asserted rolling equality.
Empty ZIP goes discover->finish without scan. `finalRoot` zero until finish;
entry/lookup reject before FINAL. Raw EVM storage/code is public, so this is not
confidential staging. Failed batches publish no prefix of that batch.

## ZIP profile and byte authority

Use only EVM AS0.read, never larger than4096 per dependency call. All reads bounded
before metadata/range use; no whole-JAR memory buffer. EOCD search at most65557 last
bytes; consider classic ending candidates with exact comment-to-EOF, disk0/CDdisk0,
equal entry counts and CDoffset+size==candidate position. Exactly one candidate,
count/CD caps and zero-count iff zero-CD-size. No ambiguity guessing/host recovery.

CEN signatures/framing/extras/names and disk/flags/method/CRC/sizes/LOC offsets parsed
in EVM. LOC signature/name bytes/flags/method must agree; both extras framed and
ZIP64 extra ID1 rejected. Nonempty names are opaque bytes, not normalized paths or
UTF strings. No NUL/slash/dot/Unicode transformation. Exact equal names rejected;
strictly increasing LOC offsets and nonoverlapping full local-record ends required.
Prefixes/gaps may be opaque. Data and descriptor ends must not enter CD. Exact CEN
count/cursor must consume CD. Trailing structured material between CD and EOCD is
unsupported by exact adjacency, not silently skipped.

Methods0/8 only. Allowed flags0x080e; bits1/2 only for method8. Reject all others,
ZIP64 sentinel sizes/offsets, multidisk and encryption. Method0 comp==plain; no plain
CRC computed. With bit3 absent LOC CRC/sizes equal CEN. With bit3 present LOC values
are zero, classic signed16 or unsigned12 descriptor repeats CEN CRC/sizes and stays
before CD. Stated CRC and declared plain size remain untrusted-content metadata.

ZIP64 policy: structured ZIP64 between CD and EOCD fails adjacency; sentinels and
extra ID1 fail. For an otherwise empty classic ZIP, reject locator signature at
exactly EOCD-20 when present. Never scan arbitrary prefixes/payloads/names for ZIP64
markers, and never advertise general ZIP64 support or universal signature rejection.
This deliberately bounded profile is not general-purpose ZIP conformance.

## Record and root

Two logical nonzero storage slots/entry: `records[index]`, name hash->index+1. No
name-byte duplication or host index. On occupied bucket reread the old full name:
identical bytes error18 duplicate, unequal bytes error19 unsupported collision.
Lookup checks full supplied bytes against the referenced AS0 name before returning
success; a bucket hit alone is insufficient. Missing key returns(false,0,zero record).

Packed LSB bits:0..24 namePos;25..49 LOCpos;50..74 dataStart;75..99 compressedSize;
100..131 plainSize;132..163 CRC32;164..172 nameLen;173..188 flags;189..192 method;
193..194 descriptor(0 none,1 unsigned12,2 signed16);195..255 zero. All four25-bit
positions/sizes fit the32MiB archive bound with framing; plainSize32bit (except ZIP64
sentinel), nameLen1..256. Derived dataEnd=dataStart+comp, recordEnd includes descriptor.
No Go decoder may turn this into production class/resource lookup authority.

H=keccak256;D0=H(ASCII MC-ZI0/index/v1);DE=H(ASCII MC-ZI0/entry/v1); abi.encode:
I0=H(D0,this,owner,store,AS0_CODEHASH,content,uint32 length,uint32 eocd,
     uint32 cdOffset,uint32 cdSize,uint32 count).
Step=H(DE,previous,uint32 index,H(rawName),uint16 nameLen,uint16 flags,uint16 method,
       uint32 crc,uint32 comp,uint32 plain,uint32 local,uint32 dataStart,
       uint32 dataEnd,uint32 recordEnd,uint32 cenRecordEnd).
Final root is the final rolling value, not a location-independent file digest or
whole-JAR SHA256. Splitting scans differently must not change it for identical input
binding/instance, and no caller-supplied list of roots/records can initialize it.

## Error codes

Keep prototype codes:1 owner;2 AS0 code;3 binding/length;4 phase;5 short ZIP;
6 EOCD;7 count/CD caps;9 empty-ZIP locator policy;10 scan CAS;11 units/no remaining;
12 CEN signature;13 lengths;14 flags/disk/sentinels/packed bounds;15 method/size;
16 range;17 CEN extra;18 duplicate;19 collision;20 LOC header;21 LOC lengths;
22 LOC extra/name;23 data end;24 LOC CRC/size;25 descriptor;26 descriptor end;
27 order/overlap;29 finish;30 unpublished;31 entry bound;32 lookup length.
8/28 reserved, no measurement API. Ordinary invalid-profile probes require exact
selector0x2cb107ad and code, not any failure. AS0 dependency errors may bubble for
TEST-only damaged dependency state; unexpected OOG/panic is not semantic rejection.

## Opaque Go transport scope

Provide ABI/Runtime/InitCode from embedded verified combined artifact only. New
namespace owns one AS0 upload and at most one ZI0 index on the SAME EVM state/trie.
No merging/extracting account code from another profile, no redeploy-on-reopen.

`NewMemory(owner,length)` / `Open(directory,owner,length)` create ONLY AS0 initially;
caller transports opaque chunks through `Append(cursor,raw,Pi,gas)`, then
`Seal(cursor,chain,gas)`. Separate `CreateIndex(contentAssertion,gas)` invokes ordinary
ZI0 constructor on that sealed store. It is NOT combined with Seal into an invisible
multi-call batch. Only one successfully published index is routable per session.
Then `Discover(gas)`, `Scan(entry,cursor,rolling,units,gas)`, `Finish(count,cursor,
rolling,gas)` execute the exact methods. Expected values are transport assertions.
`Read(offset,length,gas)` and `Page(index,gas)` route AS0 raw views (not named ZIP
consumption); `Entry`/`Lookup` return EVM name/packed bytes unchanged plus accounting.
`Head` reports committed trie root, both addresses and EVM-read AS0/index getters,
with explicit absent-index address0. `Creation` distinguishes new AS0 creation from
reopen (no replayed CREATE gas); `Close` is deterministic/idempotent. Bound owner
never has a caller-selectable override in the production session API.

Go scalar arguments mirror ABI widths; gas is uint64; roots/packed records are
common.Hash, addresses common.Address, names/raw bytes []byte. Append/Seal/
CreateIndex/Discover/Scan/Finish return `(Operation,error)` with GasUsed,StateRoot,
Logs,RevertData and CreatedAddress (nonzero ONLY after successful CreateIndex
publication). EVM failure returns gas+raw revert data; publication failure gas only.
Creation() returns `(as0.Creation,error)` for the initial AS0 create (Performed=false
on reopen). Page(uint64,gas) and Read(uint32,uint32,gas) may return accepted as0.Page/
as0.Read types. Entry(uint32,gas) returns Name,PackedRecord,GasUsed; Lookup([]byte,gas)
returns Found,Index,PackedRecord,GasUsed. No host decoded catalogue fields are needed.
Head returns StateRoot,AS0(as0.Head),Index(IndexHead),GasUsed; IndexHead contains
Address,RuntimeCodeHash,all13 typed scalar getter values and its getter GasUsed.
Index.Address0 explicitly means not yet constructed and other index fields are zero.
Head.GasUsed is the sum of actual AS0+index getter gas, not prior mutation gas.
Runtime()/InitCode()/ABI() return defensive embedded copies/decoded ABI with errors,
never paths/compiler fallback. Session entry points except idempotent Close check
closed/poison state.

Every successful CREATE/Append/Seal/CreateIndex/Discover/Scan/Finish commits+reloads
in memory; disk additionally syncs trie AND code, then unique manifest temp fsync,
rename, directory fsync before success. Atomic local publication is not signed-chain
transaction/intrinsic-gas semantics. A failed operation reloads the prior published
root including creator nonce; no success root/address/page/event escapes it. Ambiguous
postrename failure poisons until reopen. Return actual gas even for failed execution/
publication, but no trace-derived success. Getters/views operate on copied EVM state.

Manifest format/context/requested owner/length/expected code pins/root/addresses are
bounded regular metadata verified BEFORE LevelDB open. Compare code pins with embedded
artifacts, not self-asserted manifest hashes. After opening verify actual code and EVM
bindings/head; fields such as ZIP cursor/phase may NOT become manifest authority.
AS0/index absence and sealed phases must agree. Reopen never constructs missing code.
No existing AS0/VFS directory adoption. Incomplete initial directories fail closed and
are preserved. Reject fixed/internal symlinks (including LevelDB descendants), unknown
metadata fields/oversized or nonregular files; explicit root aliases can canonicalize.
Publication temps must be owned unique regular files. Preserve unknown failure evidence;
never overwrite a damaged store with a fresh root. Use AS0 accepted transport guards
as the minimum precedent, not the disposable preflight transport's shortcuts.

Pin the accepted preflight/AS0 execution context: AllDevChainProtocolChanges,
block1,time1,zero difficulty/coinbase/value/gasPrice/random/GetHashFn output,
InitialBaseFee and BlobTxMinBlobGasprice. Origin is the bound nonzero owner; gas
is the explicit call allowance. No EVM/consensus/size-limit overrides. Manifest
context must bind this exact profile, not accept caller-selected VM rules.

Report each EVM operation gas and view sums honestly; separate AS0 upload/index
CREATE/discover/scans/finish/reads, publication counts, CPU/RSS and disk bytes. Neither
aggregate gas nor LevelDB disk delta is computational instruction count or Java heap.
Do not count changed-query misses as exercising the full-byte collision guard.

## Authorized implementation and mandatory acceptance gates

At most2 disjoint workers: runtime owns ONLY `jvmevm/artifactstore/zi0/runtime/**`;
harness owns package except runtime/** and parent_test.go. Parent owns docs/Make/
gitignore/integration/independent parent tests. One production Solidity writer;
Sol/high for critical semantics, Luna/Terra allowed for frozen pure coding, noFast/
priority/spawn/peer writes/settings/push. Key evidence goes in Git-tracked
`evidence/java-evm/zi0/`; disposable intermediates only in build/test temp dirs.

Sixteen parent gate groups:
1 artifacts/exact ABI/repro/ordinary CREATE identity and zero owner;
2 true AS0 upload/seal/index binding and constructor rollback/retry;
3 EOCD ambiguity/prefix/empty/ZIP64 policy and max-tail patterns;
4 CEN/LOC framing/flags/methods/extras/descriptors/geometry-specific refusal;
5 opaque names/duplicates across batches and actual full-byte mismatch guard;
6 root/record independent packing derivation and q1/q64 equality;
7 CAS/phase/unit/no-op refusal, atomic mid-batch failure and direct OOG rollback;
8 final-only entry/lookup/negative bounds and correct raw AS0 ranges;
9 20554 target-shaped/32768 entries/exact4MiB CD/+1 and max-TLV batch;
10 exact32MiB ZIP/high25-bit offsets without cap changes;
11 every-call memory commit/reload versus durable disk publication counts;
12 real mid-upload/sealed-AS0/bound/staged/FINAL fresh-process reopen and no redeploy;
13 manifest namespace/bounds/pins/internal-link/incomplete-store refusal;
14 prepublication recovery/postrename poison/failure gas-only receipts;
15 embedded source-independent executable and concurrent stale-call/refusal checks;
16 final artifacts under watchdog, vet, AS0 regression and protected older/core paths.

All acceptance is final-artifact evidence, not worker completion or this freeze. No
production ABI/code pins may be declared accepted before independent final gates.
