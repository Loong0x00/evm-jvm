# MC-CB0 fixed class package / LOCAL shared-world coordinator

Status: **FROZEN FOR IMPLEMENTATION, NOT ACCEPTED**. Independent evidence and draft
corrections: JAVA_EVM_MC_SHARED_WORLD_PARENT_PREFLIGHT.md. Latest user says continue
(no pause), default agent model is5.6 Terra. Use default model, high reasoning; no
Sol override/Fast/priority/global settings changes. Parent independently verifies.

## Scope and unchanged dependencies

Genuine fixed generated-class package: opaque ZIP -> accepted AS0/ZI0 -> up to4
accepted DI0 decoders -> EVM-only FINAL reads -> unchanged VFS0a JVM start/resume.
NO raw class bytes in Java execution API, host ZIP/class catalogue/parser/inflater/
Java evaluator, private Session reflection/unsafe, decoded page SetCode or failed
trace recovery. Not general/lazy ClassLoader, Minecraft execution, EULA, networking,
world/Done, full Java SE or standard-chain full-JVM deployment.

New package `jvmevm/localcontinuation/cb0`; small controller runtime in its runtime/
subtree. Existing AS0/ZI0/DI0/VFS0a/core files and quotas remain unchanged.
AS0 input<=32MiB,4096 pages8192B; ZI0 existing caps; DI0 output262144/entry,32KiB
lookback,32-byte copy,8192 output pages<=32,4096 read; CB0<=4 selected resources,
aggregate1..65536 raw class bytes, names<=256 including.class. Existing VFS0a fixed
38 bootstrap images, heap/fields/args8/checkpoint1MiB/VFS64KiB/64inodes/32FD and
JVM/internal units1..4096. CB0 initial VFS seeds are EMPTY, no seed API added yet.
The selected entry's internal class and method names still obey VFS0a's ASCII limits;
no broader Unicode/path name normalization is claimed.

Pinned dependencies (Keccak runtime):
AS0 c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896;
ZI0 0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77;
DI0 946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37;
VFS0a e7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84,
292968B/SHA717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86,
fixed LOCAL address0x4a564d45564d564653304152554e54494d450001, nonce0.

## Exact controller ABI / constructor package

Name `CB0ClassCoordinator`; exactly10 functions + constructor + CB0Error(uint256 code).
No events/fallback/receive/debug/import/upgrade/owner-transfer/rebinding/registration
setter, immutables or link substitutions. Instance identity in constructor STORAGE.

```
constructor(address fixedOwner,bytes32 fixedInstanceSalt,address[] fixedDecoders,
 bytes[] fixedRawNames,bytes32[] assertedIndexRoots,bytes32[] assertedResourceRoots,
 bytes32 assertedPackageRoot)
owner() address; finalIndex() address; finalIndexRoot() bytes32;
packageRoot() bytes32; instanceId() bytes32;
totalClassBytes() uint32; classCount() uint8;
classBinding(uint8 at) view returns(address decoder,bytes rawName,
 bytes32 resourceRoot,uint32 classSize)
start(bytes32 assertedPackageRoot,uint8 entryAt,string entry,int32[] args,
 uint64 maxJvmSteps,uint32 maxInternalSteps) returns(bytes engineReturn)
resume(bytes32 assertedPackageRoot,uint64 expectedEpoch,bytes32 expectedCheckpointRoot,
 bytes checkpoint,uint64 maxJvmSteps,uint32 maxInternalSteps) returns(bytes engineReturn)
```

All mutators/constructor nonpayable, getters/bindings view. Constructor:
nonzero fixedOwner==msg.sender FIRST;1..4 matching array lengths; engine code pin;
for each ordered resource: DI0 code, no repeated decoder OR raw name, name valid
(exact .class suffix, nonempty stem, no NUL/backslash/dot in stem), FINAL, nameHash,
nonzero exact indexRoot/F, size1..65536, aggregate<=65536, same index/root and DI0
owner==fixedOwner. Finally index code/FINAL/root/owner checked. Order is significant,
not silently sorted; same names/order/roots are revalidated by EVM, no host authority.
One fixed JVM instance derived below, no instance ID supplied during start/resume.

Every start/resume: owner then asserted package then entry index(start only);
check exact engine and final index code/phase/root/owner; recheck each DI0 code/
phase/nameHash/index/root/F/size/owner against stored registry; read each class in
<=4096B STATICCALL fragments and validate returned length, assemble in EVM; call
unchanged VFS0a ABI with those actual bytes. No host class input. Start uses selected
stem as internal name and empty seeds. Resume passes existing EVM checkpoint/epoch
CAS; engine independently verifies class images/declared names/continuation/Code.
Bubble existing engine/resource errors unchanged. Engine head owner=coordinator.
Do not reclassify a guard refusal as OOG or accept Java output from failed EVM calls.

Error codes preserve measured semantics:1 ctorowner;2 count/array lengths;3 engine
code;4 DIcode;5 duplicate ref/name;6 rawname;7 nonFINAL;8 nameHash;9 indexroot;
10 resourceF;11 classsize;12 aggregate;13 mixedindex;14 DIowner;15 indexidentity;
16 packageassertion;17 callerowner;18 callpackageassertion;19 classindex;
20 changed DI binding;21 fragmentlength. Budget/CAS/class/Java failures may bubble
from exact VFS0a/DI0; don't invent coordinator code0/OOG-success.

H=keccak256,D(s)=H(ASCII s); all encodings abi.encode, NOT packed. Production domains
must not reuse preflight domains. Constant domains P="MC-CB0/package/v1",
R="MC-CB0/resource/v1", V="MC-CB0/vm/v1".
R0=H(D(P),this,owner,engineAddress,engineCode,DI0code,ZI0code,uint8 count).
Ri=H(D(R),Rprev,uint8 i,address decoder,H(rawName),indexRoot,F,uint32 size).
Package=H(D(P),Rfinal,uint32 total,address commonIndex,commonIndexRoot).
Instance=H(D(V),this,Package,fixedInstanceSalt). Salt may be zero.
Package is EVM-derived; a caller's precomputed value is only an assertion.

## Artifact contract

Solc0.8.30+commit.73712a01.Emscripten.clang,opt200,viaIR,Cancun,metadataoff
(appendCBOR=false,bytecodeHash=none). Runtime<=24576B, COMPLETE init<=49152B;
maximum constructor args2016B for four256B names. Engine<=320KiB is a separate
accepted LOCAL code installation, never a small-controller deployment claim.
Ordinary calls100Mgas/30s; explicit boundary1B/120s; whole gate20min4GiB.

runtimeassets.Artifact() returns defensive combined JSON []byte; fixed CB0 source,
abi/init/runtime hex, reproducible build/package-lock in runtime/. Combined schema
same keys as DI0:contractName,abi,bytecode,deployedBytecode,immutableReferences,
compiler,sourceHashes,codeHashes,dependencyPins,limits,storageLayout. Lowercase hex
without0x. contractName CB0ClassCoordinator; sourceHashes only CB0ClassCoordinator.sol;
compiler/codeHashes exact DI0 nested shapes. dependencyPins exact keys
AS0RuntimeCodeKeccak256,ZI0RuntimeCodeKeccak256,DI0RuntimeCodeKeccak256,
VFS0aRuntimeCodeKeccak256,VFS0aAddress (lowercase40 hex,no0x).
limits exact keys:archiveBytes33554432,resources4,classBytes65536,rawNameBytes256,
resourceReadBytes4096,checkpointBytes1048576,jvmUnits4096,internalUnits4096,
engineRuntimeBytes327680,runtimeBytes24576,completeInitBytes49152,seedFiles0.
No metadata-selected alternate profile. Actual source/ABI/layout/compiler/init/
runtime/combined pins independently checked in Go, not trusting edited JSON fields.

## New opaque shared-world transport

Marker `JVMEVM-MC-CB0-LOCAL-STORE-1\n`, format1; never adopt another namespace or
private StateDB, infer syncs from readable metadata, or repair reopen by CREATE.
Own normal StateDB/trie/DB plus copied views, mutex/closed/poison checks. Context
same AllDevChain block1/time1/zero origin value,coinbase,difficulty,gasprice,random,
GetHashFn; InitialBaseFee/BlobTxMinBlobGasprice; Origin=bound owner.

**Atomic fresh initialization refinement:** install exact LOCAL VFS0a account/code
(nonce0, no gas claim) then ONE ordinary AS0 CREATE(owner nonce0), commit/reload and
publish ONE initial root containing both. Expose neither an engine-only routable
manifest nor partial successful initialization. Incomplete nonempty directories
are preserved/refused after failure. Reopen never reinstalls code or CREATEs.
All later successful EVM mutations each independently commit/reload/publish. This
production initialization contract is explicit, not claiming the preflight's two
initial commits were one. Existing accepted profiles are not changed.

Public API uses common.Address/common.Hash, []byte and uint64 gas as in DI0:
NewMemory(owner common.Address,length uint32),Open(directory,owner,length),Close();
Initialization() returns EngineInstalled bool,EngineAddress,EngineCodeHash,StateRoot,
AS0 as0.Creation (Performed/gas0 on reopen). Source/engine installer no other SetCode.
Append/Seal/CreateIndex/DiscoverIndex/ScanIndex/FinishIndex as accepted DI0 signatures;
CreateDecoder(expectedSlot uint8,indexRoot,rawName,gas), slot==current decoder count,
max4; no further decoder creation once coordinator exists.
StepDecoder(slot uint8,expectedWork uint32,units uint16,gas);
PublishDecoder(slot uint8,expectedPage uint8,rolling,units uint8,gas);
CreateCoordinator(salt,ordered []ResourceBinding,assertedPackageRoot,gas), exactlyonce;
ResourceBinding{Slot uint8,RawName []byte,IndexRoot common.Hash,ResourceRoot common.Hash}.
All non-Java mutations return di0.Operation (or an identical declared type).
No implicit getters/mutations in publication. Routes/names/index assertions cached
only after the corresponding pinned EVM constructor proves them, not ZIP metadata.
Ordered refs are caller assertions; EVM validates size/identity/F/package. Go may
check shallow route/count/name encoding bounds but cannot become class authority.

Start(packageRoot,entryAt uint8,entry string,args []int32,jvm uint64,internal uint32,gas);
Resume(packageRoot,epoch uint64,checkpointRoot,checkpoint []byte,jvm uint64,internal uint32,gas).
These return JavaResult{Slice vfs0a.SliceResult,Checkpoint []byte,StateRoot,GasUsed,
RevertData []byte}; no emitted logs permitted. Decode outer bytes then exact engine
result, validate schema/counters/lifecycle and nonempty<=1MiB checkpoint hash for
ALL successful lifecycle outcomes, including terminal. Java exceptions are genuine
engine outcomes, not EVM errors. Publish before returning slice/checkpoint/root.
EVM failure: gas+revert only. Publication failure: gas ONLY, zero slice/root/checkpoint.

Head(gas) -> composite StateRoot,GasUsed,AS0 as0.Head,Index zi0.IndexHead,
Decoders []di0.DI0Head in creation order,Coordinator CoordinatorHead,Java vfs0a.Head.
CoordinatorHead contains Address,RuntimeCodeHash,seven typed getter values and
ordered Classes([]{Decoder,RawName,ResourceRoot,ClassSize}),GasUsed. Absent coordinator/
Java fields zero; Java owner must equal coordinator, absent engine anchor epoch0.
ResourceRead(slot uint8,offset,length uint32,gas),ResourcePage(slot,at uint8,gas) reuseDI0
Read/Page result types. InputRead/InputPage/Entry/Lookup as DI0 opaque view signatures.
ReadCheckpoint(root) returns a defensive copy ONLY for the latest published Java
head, including terminal; stale root rejected. No host class array or InspectFile
raw-class bypass API. Future VFS inspection/seed or lazy-loading APIs are separate.

Disk publishes trie+code sync, opaque content-addressed checkpoint file fsync and
its directory sync when Java produced a blob, unique regular manifest temp fsync,
rename and rootdir fsync before success. Memory retains only latest published blob;
disk may preserve older/orphan diagnostics but may not adopt them. Beforepublication
restore old root/routes/current blob; afterrename ambiguity poison all APIs until
exact reopen. No postrename rollback to an older routable root. No metadata-only
stage writes or inferred/lifetime diagnostic counter reconstruction in production.
On reopen validate bounded regular metadata/context/owner/length/all code pins/routes
BEFORE DB, reject empty trie root and internal/nested links. Re-read EVM identity/
phase/cursors/package/instance/anchor and verify current blob<=1MiB/hash againstEVM.
Owner nonces: AS00,ZI01,decoder2..(1+n),coordinator2+n; expected creator nonce2+n
before coordinator/3+n after, subject to absent-index initial nonce1. AS0/DI0 page
creator nonces independent. Existing genuine stored-DEFLATE pendingLEN65535/distance0
is not a Huffman258 match; retain accepted DI0 validation fix. No reopening creates.

## Ownership and final parent gates

At most TWO default-Terra/high workers. Sole runtime writer owns
jvmevm/localcontinuation/cb0/runtime/** and evidence/java-evm/cb0/runtime-candidate/**.
Transport writer owns cb0/** EXCEPT runtime/** and parent*.go, plus
 evidence/java-evm/cb0/transport-candidate/**. Parent owns root docs/Make/gitignore/
independent tests/integration/acceptance. No additional spawning/peerwrites/push.
No stub-only compile delivery: real committed runtime artifacts and actual EVM
behavior required; temporary ignored read-only overlays must be labeled.

Parent gates: exactartifact/ABI/rebuild/maxargs/LOCALinstall+ordinaryCREATE identity;
constructor/package/order/name/bindings; true cross-class Java init/calls and input
sensitivity; direct/q1/q7 equality;1..4/65536/+1 paging; exact coded refusal versus
OOG/Java; terminal checkpoint; complete memory+per-call disk receipts and actualIO;
new/relocated processes at input/index/decode/ready/Java-running/terminal; wrongCAS/
owner/namespace/metadata/code/head/blob shapes; direct changed-state EVM rollback;
actual post-sync and temp/rename/dirsync failures/oldroot/retry/poison; closed/copied/
concurrent behavior; finalwholewatchdog+vet/repro/accepteddependency regressions and
protected core hashes. Completion is not acceptance. No original Java execution,
EULA, listener, world, Done or new push follows from this freeze.
