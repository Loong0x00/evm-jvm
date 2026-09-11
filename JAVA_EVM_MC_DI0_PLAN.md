# MC-DI0 bounded resource decoder — implementation freeze

Current status: DI0 accepted by JAVA_EVM_MC_DI0_REVIEW.md. The freeze/candidate
record below is historical; its failures and scope decisions remain preserved.

Status: **FROZEN FOR IMPLEMENTATION, NOT ACCEPTED**. See
JAVA_EVM_MC_DI0_IMPLEMENTATION_PREFLIGHT.md for independent replay, the additional
64-header counterexample and explicit EVM budget-yield refinement. This freeze is
not a general Java/ZIP conformance claim or a production acceptance record.

Goal: EVM derives exact compressed range/metadata from accepted ZI0, decodes ZIP
method0/raw-DEFLATE method8, verifies plaintext length+CRC32, and issues immutable
EVM-created plaintext pages. No host decoder/canonical tree/CRC/offset catalogue/
output installer authority. No official server input in worker fixtures; no Java
ClassLoader/main/MC/EULA/listener/world/Done. First future MC target remains unchanged
vanilla1.12.2 superflat. Accepted AS0/ZI0/VFS/core/artifacts/quotas stay unchanged.

## Namespace, compiler and budgets

Package `jvmevm/artifactstore/di0`; production contract `DI0Resource`; dedicated
runtime/ subtree with DI0Resource.sol, init.hex/runtime.hex/abi.json,
combinedartifacts/DI0Resource.json and defensive embedded `Artifact()` bytes.
Solc0.8.30+commit.73712a01.Emscripten.clang, optimizer200,viaIR,Cancun,metadataoff
(appendCBOR=false,bytecodeHash=none), no immutable/link substitutions or fallback.
Ordinary CREATE only: runtime<=24576B, COMPLETE init including constructor args
<=49152B. A256-byte rawName adds384 ABI bytes. No host SetCode/alternate evaluator.

DI0-only plaintext cap262144B/entry is now explicitly frozen for implementation,
not yet accepted. It covers the pinned JAR's static declared entry maximum158794B
and90309B largest class; it does not expand mutable VFS/Java heap/checkpoints or
promise all declared output fits at runtime. Full staging<=8192 32-byte words;
maximum lookback32768, copy/stored action<=32 bytes; output pages8192B<=32 pages,
page runtime STOP||raw <=8193B; reads<=4096B. Method0 can have empty input/output;
method8 still needs a valid stream. Empty output is zero pages/nonzero final root.

Accepted input budgets unchanged: AS0<=32MiB/4096 pages of8192B/4096B reads and ZI0 metadata
limits. Step units1..128; publish units exactly1. Ordinary100Mgas/30s, explicit
boundary1B/120s; entire gate20min4GiB. Fixed EVM step reserve25000000gas, below.
No silent cap increases, caller-disabled guard or arbitrary whole-block work action.

Embedded runtime package name runtimeassets; Artifact() returns a defensive []byte
copy of combined JSON. Freeze the accepted ZI0 combined-artifact structure: exact
keys contractName,abi,bytecode,deployedBytecode,immutableReferences,compiler,
sourceHashes,codeHashes,dependencyPins,limits,storageLayout. Hex is lowercase/no0x.
sourceHashes has DI0Resource.sol; immutableReferences empty. compiler/codeHashes
retain ZI0's exact nested keys; dependencyPins has AS0RuntimeCodeKeccak256 and
ZI0RuntimeCodeKeccak256. storageLayout has solc storage/types. limits exact keys:
archiveBytes33554432,as0PageBytes8192,as0ReadBytes4096,rawNameBytes256,
outputBytes262144,historyBytes32768,copyBytes32,outputPageBytes8192,outputPages32,
readBytes4096,stepUnits128,publishUnits1,stepReserveGas25000000,
runtimeBytes24576,completeInitBytes49152. No metadata-selected alternate profile.

## Exact Solidity ABI

Exactly33 functions plus constructor and DI0Error(uint256 code), no events, receive,
fallback, debug/comparator/state-import/reset/upgrade or other callable surface.
Constructor/mutators nonpayable; getter/view outputs typed as below.

```
constructor(address finalIndex,bytes32 assertedIndexRoot,bytes rawName)
step(uint32 expectedWork,uint16 units)
publish(uint8 expectedPage,bytes32 expectedRolling,uint8 units)
read(uint32 offset,uint32 length) view returns(bytes out)
page(uint8 at) view returns(address pageAddress,bytes32 codeHash,
                           bytes32 pageCommitment,uint32 length)
owner() address; index() address; store() address;
indexRoot() bytes32; content() bytes32; packedRecord() bytes32; nameHash() bytes32;
binding() bytes32; outputRolling() bytes32; publicationRolling() bytes32;
finalRoot() bytes32;
entryIndex() uint32; dataStart() uint32; compressedSize() uint32; plainSize() uint32;
expectedCRC() uint32; outputCount() uint32; inputByte() uint32; work() uint32;
crc() uint32; pendingLength() uint16; pendingDistance() uint16;
inputBit() uint8; method() uint8; phase() uint8; blockMode() uint8;
blockFinal() bool; fixedBlock() bool; publishedPages() uint8;
```

All instance identity is constructor-written STORAGE, no setters/immutables. Nonzero
owner check FIRST(1), then ZI0 code2, FINAL/asserted nonzero root3, name length1..256
and found lookup4, then record/AS0-code/method/output-cap/range5. Names are opaque
bytes, hashed after EVM full-name lookup; no slash/NUL/dot/Unicode normalization.
Any nonzero creator may bind a public accepted FINAL index, irrespective of its owner.

ZI0 runtime Keccak0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77;
AS0 runtime Keccakc8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896.
Resolve all packed fields through EVM ZI0 lookup, never caller offsets or lengths.
Pin immutable index/store/address/root/content/record/name binding. No rebinding.
Mutators check owner then phase then dependency identity, then work/publication CAS
and unit validity. Verify both accepted code hashes, ZI0 FINAL/root/content/store
against constructor bindings once per mutator (not once per output byte). Dependency
errors may bubble on TEST-only damaged dependency state, not ordinary profile errors.

Phases1 DECODING,2 VERIFIED,3 PUBLISHING,4 FINAL. CRC+length+exact compressed range
must pass before VERIFIED/output page CREATE. Empty verified output automatically
FINAL with no publish call. Nonempty publish issues one page; the last page atomically
FINALizes. No separate finish/import path. Final read/page gate9 first, then bounds;
read checks actual page code hashes and EXTCODECOPY skips STOP. Staging storage is
public EVM state, not confidential, but is NEVER a final read source.

## Decoder semantics and progress

Raw RFC1951 only for method8 (no zlib/gzip framing); method0 copies raw indexed bytes
with comp==plain. Use LSB bit elements and canonical Huffman bit order, fixed/stored/
dynamic blocks, length3..258 and distance1..32768 not before output start. Overlap
copies observe newly emitted bytes; history uses bounded staged output, not a host
map. Reserved fixed286/287 and distance30/31 reject. Java8-accepted code284+extra31
alternative length258 is allowed. CRC startsffffffff, reflected polynomialedb88320,
complement at verification; expectedCRC remains metadata until recomputed in EVM.

Dynamic counts: HLIT257..286,HDIST1..30; code-length order RFC1951. Repeats16/17/18
require legal predecessor/count bounds and may cross LL/DIST boundary. Code-length
tree must be complete; LL/DIST may be complete or singleton length1; distance may
be empty only if unused. LL must contain EOB256. Reject oversubscribed/malformed
incomplete trees and invalid decoded symbols. Build/reuse canonical tables in EVM;
rewrite counts and ensure stale ordered entries cannot be reached. Fixed/stored
modes do not consult stale dynamic tables. Cache transitions and fresh-process
resumption must retain semantics for all previously tested tree families.

Stored alignment bits and final unused high bits may be nonzero. BFINAL/EOB must
consume the entire indexed compressed byte range (except unused final bits); a
whole trailing byte rejects23. This deliberately matches the measured ZipInputStream
size check and is stricter than raw Java8 Inflater/ZipFile. Do not retarget those
oracles or advertise unrestricted Java8 Inflater compatibility.

One action: a bounded block header (including one finite dynamic table construction),
one Huffman symbol+bounded extras, or at most32 pending-match/stored/method0 bytes.
An optimized atomic dynamic header is allowed, no arbitrary whole data block action.

**Explicit gas-aware upper-bound semantics:** check owner/phase/binding/CAS/units,
create bounded reader, then attempt the FIRST action. Before every LATER action,
if gasleft()<25000000 stop this call successfully and save actual cursor/state.
Each completed action increments work exactly once. Thus `units` is a maximum, NOT
a guarantee of that increment. Every successful step has positive progress; low gas
can still genuinely OOG in the first action and must revert normally. No hidden host
retry, trace harvest, invented work or gas counter. Final work/output/state/root for
identical binding must be independent of call grouping/gas-yield points. Input-byte/
bit and pending-copy state persist precisely; reader fragments are call-local,
<=4096B, refilled only from the indexed AS0 range. Boundary tests must retain actual
requested128, not quietly use8/64 to make the gate pass.

## Output pages, roots and codes

After verification, controller-owned ordinary CREATE issues STOP||staged bytes,
8192B except last remainder. No external raw-page/code/commitment input exists.
Verify issued EXTCODEHASH, ordered page lengths/count/addresses; failure reverts
page/nonce/root. Page/read cannot grant FINAL authority early. At most32 records.
Full staging may remain allocated; final readers exclusively use verified page code.

H=keccak256;D(s)=H(ASCII s); ALL encodings abi.encode (not packed). Production domains
MUST NOT reuse preflight domains. Types/order:

B=H(D("MC-DI0/binding/v1"),this,owner,index,ZI0_CODE,indexRoot,store,AS0_CODE,
    content,uint32 entryIndex,nameHash,packedRecord,uint32(262144)).
O0=H(D("MC-DI0/output/v1"),B).
Oi=H(D("MC-DI0/byte/v1"),Oprev,uint32 outputIndex,uint8 byte).
P0=H(D("MC-DI0/publication/v1"),B,uint32 verifiedLength,uint32 computedCRC,
     Ofinal,uint32(8192)).
PCi=H(D("MC-DI0/page/v1"),B,uint8 pageIndex,uint32 pageLength,H(raw)).
Pi=H(D("MC-DI0/published/v1"),Pprev,uint8 pageIndex,uint32 pageLength,pageAddress,
     H(STOP||raw),PCi).
F=H(D("MC-DI0/final/v1"),B,uint32 verifiedLength,uint32 computedCRC,Ofinal,
    uint8 pageCount,Pfinal).

Coded errors preserve preflight1 owner;2 ZIcode;3 ZIphase/root;4 name/lookup;
5 binding-record/method/cap;6 phase;7 step CAS;8 units;9 unpublished;
10 read bounds;11 input;12 method0range;13 BTYPE;14 LEN/NLEN;15 LLsymbol;
16 distancesymbol;17 distance/range;18 repeat;19 EOB;20 oversubscribed/length;
21 incomplete tree;22 decode;23 compressed-end;24 plain-length;25 CRC;
26 output overrun;27 count profile;28 publish CAS;29 publish unit/range;
30 CREATE failure;31 issued/read code;32 page bounds. No semantic error0/OOG shortcut.

## Opaque transport (new namespace, not old-manifest adoption)

Go package owns one AS0 upload, one ZI0 index and one DI0 instance on a single trie.
Marker `JVMEVM-MC-DI0-DISK-STORE-1\n`, format1. It is a proof-session scaffold, not
an instruction to re-upload the JAR for each future guest resource; runtime DI0
instances may share an accepted index through later guest loader/factory integration.
No accepted AS0/ZI0 source modifications, code/account extraction or host SetCode.

Exact Session API uses address/common.Hash roots, []byte opaque bytes, uint64 gas:
NewMemory(owner,length uint32), Open(directory,owner,length) create ONLY AS0;
Append(cursor uint32,raw,Pi,gas), Seal(cursor uint32,chain,gas);
CreateIndex(content,gas), DiscoverIndex(gas),
ScanIndex(entry,cursor uint32,rolling,units uint16,gas),
FinishIndex(count,cursor uint32,rolling,gas);
CreateDecoder(assertedIndexRoot,rawName,gas);
Step(expectedWork uint32,units uint16,gas),
Publish(expectedPage uint8,expectedRolling,units uint8,gas);
Read(offset,length uint32,gas), Page(at uint8,gas);
InputRead(offset,length uint32,gas), InputPage(at uint64,gas);
Entry(index uint32,gas), Lookup(rawName,gas); Head(gas), Creation(), Close().
Creation refers to the initial AS0 CREATE; reopened Performed=false/gas0. Only one
successfully published index/decoder route per session. Separate CREATE/mutation
calls and publication, no hidden multi-call batch or initial-empty-trie success.

Operation result: GasUsed,StateRoot,Logs,RevertData,CreatedAddress; CreatedAddress
only successful CreateIndex/CreateDecoder. EVM failures gas+revert only; publication
failures gas only. Views report their exact gas separately. InputRead/InputPage and
Entry/Lookup may reuse accepted Go result types without host parsing; Read returns
Bytes/GasUsed; Page returns Address,CodeHash,Commitment,Length,GasUsed. Head returns
StateRoot,AS0(as0.Head),Index(zi0.IndexHead),Decoder(DI0Head),GasUsed. DI0Head has
Address,RuntimeCodeHash,29 typed diagnostic getter values,GasUsed; zero address
means absent decoder and other decoder fields zero. No host Huffman/CRC decoder.

Every successful EVM mutation commits+reloads in memory. Disk also syncs trie AND
code, unique owned regular manifest temp fsync, rename, directory fsync BEFORE any
success return. Restore last published root/creator nonce/routes before publication
failure; ambiguous after-rename failure poisons all APIs until exact reopen. No
lost-root reinitialization, orphan wipe, replayed construction or OOG trace recovery.
Use constructor-verified immutable binding caches when needed for manifest routing,
not unreported extra EVM calls during publication. No cursor/phase/tree from manifest
may become decoder authority; reopen re-reads/checks EVM getters and dependencies.

Manifest/code/source/ABI/compiler/layout/dependency hashes and size limits must be
pinned against embedded final combined artifacts, not asserted JSON/manifest values.
Strict bounded regular metadata/context/owner/input length/routing/pins BEFORE
LevelDB open; no foreign AS0/ZI0/VFS marker acceptance or nested/internal symlinks.
Requested root aliases may canonicalize. Preserve incomplete nonempty directories
and unpublished diagnostics; never assign invented roots. Copied-state views, mutex,
closed/poison checks, idempotent Close. Verify actual code, creator nonce0/1/2-derived
AS0/index/decoder routes and EVM phase/binding/cursor/output/page/CRC/root shape.
Metadata checks are bounded ABI validation, not a host index/decoder.

Pin the same AllDevChainProtocolChanges/block1/time1/zero coinbase,difficulty,value,
gasPrice,random,GetHashFn context as accepted ZI0; InitialBaseFee/BlobTxMinBlobGasprice,
Origin bound owner. No core/code-size/gas-rule override. Explicit caller allowance
1..1B, ordinary gates at100M; signed-chain intrinsic/failed-tx nonce semantics are
not claimed by this LOCAL successful-state publication transport.

## Work allocation and mandatory parent acceptance

At most TWO Sol/high workers, no Fast/priority/spawn/peer/core/settings/push. Runtime
writer owns ONLY jvmevm/artifactstore/di0/runtime/** and its
 evidence/java-evm/di0/runtime-candidate/** captures; Go writer owns package except
runtime/** and parent_test.go, plus evidence/java-evm/di0/transport-candidate/**.
Parent owns docs/Make/gitignore/independent tests/integration/acceptance. No synthetic-stub-only delivery: test against real runtime
assets when available and disclose temporary read-only build overlays. Key source/
results stay in tracked owned files/evidence/java-evm/di0/, never /tmp-only.

Sixteen independent final gate groups:
1 exactABI/artifacts/repro/caps/ordinaryCREATE/fixed-instance-code identity;
2 dependency/name/root/owner constructor/phase and all three-controller lifecycle;
3 method0/stored/fixed/dynamic,32KiB overlap/wrap and Java8 policy/corners;
4 Reader refill/bit and block/cache transitions acrosscalls/pages/processes;
5 count/tree/repeat/reserved/bad-distance/length/CRC/end negatives exactselectors;
6 requestedq1..128/budget-yield positiveprogress/64+129dynamicheaders/no valid OOG;
7 same-binding output/input/work/CRC/pages/FINAL/trie-state equality acrossgrouping;
8 sizes90309/158794/exact262144/+1/empty withoutacceptedquota changes;
9 EVM-issued pages/code/hash/ordered roots, final-only views/high offsets/bounds;
10 direct first-action post-write OOG and late pageCREATE rollback/same-child retry;
11 real every-call memory/disk sync/publicationcounts versus caller bookkeeping;
12 genuine processreopen midinput/index/decode/table/verified/midpub/FINAL,no redeploy;
13 namespace/pins/metadata bounds/internal links/incomplete state refusal;
14 all prepublication old-root recovery/postrename poison and gas-only failedreceipt;
15 concurrency/staleCAS/copiedviews/relocated source-independent embedded executable;
16 finalartifact watchdog/vet/repro and acceptedZI0/AS0/protectedcore regression.

Only final parent evidence may accept DI0. No official inflation/ClassLoader/Java
execution or Minecraft readiness follows from this implementation freeze.
