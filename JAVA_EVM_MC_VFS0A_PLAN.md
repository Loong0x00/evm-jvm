# MC-VFS0a: frozen bounded LOCAL implementation contract

Status: **implementation authorized, NOT accepted**. Dependency: accepted IOE0
`8f29f8c` (233286B, SHA256 `507ed54d56d4cbe5e559013fbf5a3e598d75a28c0ffe33735573f646eac659a0`).
This plan supersedes conflicting candidate recommendations in the three VFS0a
preflights. Parent owns freeze/integration/acceptance. Exactly two Sol/high workers,
no Fast/priority, spawning, peer writes, pushes or settings changes.

Goal: genuine guest File/FIS/FOS Code invoking an EVM-owned byte filesystem, persisted
with the Java continuation under one head. Host transports opaque class/seed/blob
bytes and drives ordinary EVM execution; it never evaluates Java, paths, files or
heap state. No Minecraft/JAR execution, EULA file/acceptance, listener, scheduler,
world fallback or genuine Done claim is part of this gate. No full SE/OS or standard
CREATE/signed-transaction deployment claim. Preserve all accepted profiles and core.

## Parent preflight disposition and new images

Parent replayed the standalone kernel driver in its own directory: run.json SHA256
`1eafceafc8aa303a4f0ffb1b5c713abb7be941f334fdb8eec276a7936d11b104` matched. The
16241B kernel/34077274gas maximum/65674B blob are NOT integrated size/gas evidence.
The kernel's arbitrary escaped-default-state recommendation is rejected in favor of
an explicit constructor restriction below. Its standalone host-supplied bind metadata
is TEST-only and cannot become production execution metadata.

Parent corrected three wrapper images before freezing: File retains Comparable<File>
and ordinary case-sensitive lexical `path.compareTo(other.path)` plus compiler bridge.
Input/OutputStream bulk and close are not falsely abstract. Their generic bulk loops
execute real Java Code; InputStream catches later IOException after a successful first
byte but propagates a first-read exception. Base close and OutputStream.flush execute
the actual Java8 empty default Code. These precisely scoped standard defaults do not
skip File* close (overridden, real EVM descriptor mutation), perform fsync, or turn
arbitrary I/O into no-ops. The candidate unsupported0 hook is removed.

Java8/21 parent host oracles agree: Comparable=true, normalized compare=0, partial
bulk=1/65, first-read IOException propagated, generic OutputStream receives signed -1
for byte255, base defaults leave a custom stream writable. Logs are
`/tmp/mc-vfs0a-parent-base{8,21}.log`. These are not candidate execution on the EVM.

Append eight images to IOE0's thirty, preserving ALL thirty identities/slot order.
New slot order: AutoCloseable, Closeable, Flushable, File, InputStream, OutputStream,
FileInputStream, FileOutputStream. Parent-frozen inputs live in the new profile's
`jvmevm/runtime/local/vfs0a/bootstrap/java/`; javac8u504 -source8 -target8 -g:none.

| class (java/) | bytes | class SHA256 |
|---|---:|---|
| lang/AutoCloseable |145|cafa160ddd47f90df802399cbd3ea0f4a62dc0d382c77fde7917b8b84fa51ea8|
| io/Closeable |170|79fae4d62aee6a6f46bd7483265bb3a19ba9fcc89c3f6dc8a14d5814a10ed86f|
| io/Flushable |139|b5679864201f2fe3eb8e7fad6a7121790281ad1ca87391d928ca9c1bc9277513|
| io/File |1267|aee6861b45213674f41d257a87a0508b3b9ca1d900ec995234bd51d129b83bc4|
| io/InputStream |595|224fd0acae8f99ca75c2cba79902dca8408fe91fa839599a96377a31a687ba72|
| io/OutputStream |601|2698b53831772935d798d8739ffe77b786f343e30f7bc5d7b1d1ae5c8efeb4c2|
| io/FileInputStream |1478|68fd8bf1cdb48a5309b60a28ec9573dd68b5cc96318487b82f93cfce058e4545|
| io/FileOutputStream |1581|4e5175528984798d6da3ef9c3cd58395e0f66788be9e11ed1a2a35fb2015f6a8|

Total5976B. Changed source hashes: File `8a7a73c9aa27481f585523b9e389aaae0018550fee33470f2cabbb880fc72378`,
InputStream `3468cf45fceaf0f720028330ae8ad41c895625235f37a655e3d8e55864fc2714`,
OutputStream `e9d18ab9aa2dafcbb2be033bf85a21e344346f16ccd9210f936cfc1808f8fbcb`.
The other five source/image pins match the wrapper preflight. No source-tree fallback
or host-provided offsets/classes/method metadata in production.

## Java surface and exact native boundary

Keep the original candidate File(String)/exists/isFile/isDirectory/mkdir/mkdirs,
FIS(File)/three reads/close, FOS(File)/(File,Z)/three writes/close, plus the parent
ordinary-Code additions above. File.private final path:String; FIS/FOS.private handle:I;
no other new fields. File.path0()String is package-private final Code. Generic base
methods dispatch ordinary guest overrides. Remaining File/stream APIs are absent and
hard-unsupported: no parent/String stream constructors, length/delete/rename/list,
RAF/Data*/Buffered*, readers/writers, Properties, NIO/ZIP/JAR, timestamps or sync.

Exactly ten private instance natives, entered only through invokespecial and exact
reserved image/declaring owner/name/descriptor/private-native flags/nonstatic mode:
File.stat0()I, mkdir0(Z)I; FIS.open0(File)I/readOne0()I/read0([BII)I/close0()I;
FOS.open0(File,Z)I/writeOne0(I)I/write0([BII)I/close0()I. Ordinary resolution/access/
receiver checks precede native dispatch. Replacements/lookalikes/foreign invocation
cannot gain native privileges. No public native, host callback, Java allocation,
exception payload, message minting or fabricated Java outcome in these primitives.
Each accepted native invoke is one JVM dispatch unit; bounded EVM byte work remains
fully gas-accounted. Start seeding/codec work has EVM gas, not fabricated JVM steps.

Returns: stat0 missing0/file1/dir2; mkdir0 false0/created1; open positive descriptor,
missing-1/directory-2, output-only denied-3; readOne byte0..255/EOF-1/closed-2;
nonzero bulk read count1..requested/EOF-1/closed-2; writes success0/closed-2;
close0 always0 including repeated close. Reject impossible statuses internally.
Wrapper arraylength/bounds/zero Code runs before native transfer; zero length returns
before closed check. For nonzero valid slices, transfer limit precedes descriptor
closed lookup. Single write masks low8 bits. All FNFE/IOException/NPE/IOOBE work,
message identity, cause fields, allocation quotas, OOM and unwind remain real Code or
inherited implicit-fault semantics. No EOFException operation or new implicit kind.

File constructor performs genuine slash-collapse/trailing-trim and String(char[])
copying; it does not perform VFS work or remove dots. Error prefix is that normalized
lexical field, not raw input/canonical path. Java loops append selected literal
English C/POSIX suffixes `(No such file or directory)`, `(Is a directory)`,
`(Permission denied)` with the leading space in the pinned images. Closed message
is the real literal `Stream Closed`. Host default locale is NOT a profile input.

## Filesystem and constructor state

Root1 `/`, work2 `/work`, read-only root3 `/ro`. Inodes DIR1/FILE2, monotonic nonzero
IDs, parents lower-ID directories, full-byte sibling uniqueness. Relative paths use
/work. Native EVM converts printable ASCII UTF16 0x20..0x7e; slash only separates,
backslash is ordinary, case matters, dots resolve lexically. Empty/control/non-ASCII,
root escape, component>64, traversal stack depth>16, normalized lexical OR canonical
path>256 hard-fail. Raw seed paths are also bounded to256 bytes before normalization. Raw seed paths also
normalize in EVM; seeds are regular files, ordered, create needed parents, reject
canonical collisions (including builtin directories), no host resolution.

Input allows read-only regular files; output denies effective read-only target or
ancestor. mkdir/mkdirs false for existing target, missing mkdir parent, file parent or
readonly ancestor, without mutation. Quota errors revert the entire operation/call.
Open failure statuses mutate nothing. Output create/truncate is atomic with descriptor
allocation; append never truncates and writes at CURRENT EOF. Each descriptor cursor
is independent and may exceed current EOF after another output truncates. Reads then
return EOF without resetting; nonappend writes extend with zero-filled gaps. No seek
API, sparse/host/chunk encoding or GC/finalizer/implicit close. Closed records persist. Each owner has at most one descriptor, including closed.
Builtin inode names/parents/kinds/readonly flags are fixed; all other directories
have readOnly=false (effective ancestor read-only still applies).

NEW dynamic File/InputStream/OutputStream-family classes require canonical no-callback
Object()V shape: max_stack0,max_locals1,no handlers,exact one-byte return. Execute the
Object frame, never skip it. Use VFS0aProfileError(5,newPC) for valid noncanonical
shape; malformed class/constructor retains ordinary error precedence. Preserve SC0's
String guard and unrelated IOE0 Object/Throwable constructor legality/inherited layouts.
Normal File null-path/default stream states during construction or unreachable after
failure remain valid heap states; do not require every initialized REF's constructor
to have returned. No native use of an escaped invalid/default stream is claimed.

Open success creates PENDING_BIND(ownerRef,1-based bindDepth,bindPC) while handle=0.
Derive corridor from actual parsed pinned constructor Code: FIS invoke18, next PCs
21/22/23/26/27/28, putfield28; FOS(File,Z) invoke19, next22/23/24/27/28/29, putfield29.
Require exact constructor/frame/post-super receiver and exact ID stack/local position
at each PC; serialized PCs/ints/host values are not authority. Exact handle putfield
makes BOUND atomically, clears bind metadata. Resume never reopens/retruncates. At
most one pending exists. FOS(File) delegates honestly. Later user subclass failure
leaves a bound descriptor/object, reachable or not. Validate both directions between
all descriptors and exact reserved handle fields on FIS/FOS-family heap objects;
ordinary Input/OutputStream subclasses have no native descriptor. Bound/closed handles
retain IDs. Fields/alias types/constructor privileges stay inherited and genuine.

## Namespace, ABI and codec

Runtime contract VFS0aInterpreter, package jvmevm/localcontinuation/vfs0a (not the
candidate localvfs path), runtime/local/vfs0a. Address
0x4a564d45564d564653304152554e54494d450001; store marker
`JVMEVM-MC-VFS0A-DISK-STORE-1\n`, disk format1. No old checkpoint reinterpretation.

SeedFile=(bytes path,bytes data,bool readOnly). Use the candidate exact external ABI:
start(bytes32,bytes[],string,string,int32[],SeedFile[],uint64,uint32);
resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32), no seeds;
both return (VFS0aSliceResult,bytes), with IOE0's13 result fields followed by
bytes32 vfsStateRoot,uint32 inodeCount,uint32 descriptorCount,uint64 logicalFileBytes.
head returns (owner,epoch,checkpointRoot,machineStateRoot,vfsStateRoot,seedRoot,
artifactRoot,configRoot,runtimeCodeHash,lifecycle). validateCheckpoint(bytes[],bytes)
returns (bytes32 machineStateRoot,bytes32 vfsStateRoot). inspectFile(bytes[],bytes,
bytes path,uint32 offset,uint32 maxBytes) returns (uint8 kind,bool effectiveReadOnly,
uint32 inode,bytes data,bytes32 fileRoot). Event CheckpointCommitted has indexed
instanceId/epoch, then checkpointRoot,machineStateRoot,vfsStateRoot,lifecycle,
totalJvmSteps,totalInternalSteps. No public filesystem mutator/import/upgrade/fork.

Domains H("JVMEVM:MC:VFS0A:{ARTIFACT,BOOTSTRAP,CONFIG,MACHINE,SEED,VFS,FILE}:1"),
H=keccak256. Keep IOE0 artifact/bootstrap formulas under new domains and38 images.
seedRoot=H(abi.encode(DSEED,ordered exact SeedFile[])). configRoot uses IOE0's formula
under DCONFIG, appending seedRoot and limitsHash; limitsHash=H(abi.encode(uint32[11]
[16,65536,64,32,65536,65536,16,64,256,4096,1048576])). Runtime hash also binds rules.
vfsStateRoot=H(abi.encode(DVFS,uint32(1),seedRoot,H(vfsSection)));
machineStateRoot=H(abi.encode(DMACHINE,uint32(1),artifactRoot,configRoot,
H(machineBytes),vfsStateRoot)); checkpointRoot=H(exact envelope).

280B big-endian header: magic[8] JVMVF0A1, schema:u32=1, instanceId[32],epoch:u64,
parentRoot[32],runtimeHash[32],artifactRoot[32],configRoot[32],machineRoot[32] at180,
seedRoot[32] at212,vfsRoot[32] at244,machineLength:u32 at276, machineBytes at280.
Machine VFA1 retains IOE0 IES1 field order/no cause table, appending terminal VFS:
nextInode:u32,nextDescriptor:u32,inodeCount:u32,descriptorCount:u32,logicalFileBytes:u64;
inodes in ID order: id:u32,kind:u8,readOnly:u8,parent:u32,nameLen:u8,dataLen:u32,name,data;
descriptors in ID order: id:u32,inode:u32,ownerRef:u32,flags:u8,cursor:u64,phase:u8,
bindDepth:u16,bindPC:u32. No padding/trailing data. Next IDs=count+1; initial4/1.
Directory data empty, root name empty, other names1..64; boolean0/1 only; flags READ1
or WRITE2 optionally APPEND4; phases pending1/bound2/closed3. Cursor<=65536, NOT <=EOF.
Bound/closed bind metadata zero. Recompute all counters/relationships/full-byte
uniqueness and roots; bounded decode then exact re-encode. View validation does not
prove issuance; live resume requires owner/epoch/exact head/artifact/config/code.

inspectFile validates the whole blob in EVM, never executes/publishes/moves cursors;
maxBytes<=4096, offset beyond EOF empty. Missing returns (0,false,0,empty,zeroRoot).
Existing entry fileRoot=H(abi.encode(DFILE,uint32(1),uint32(inode),uint8(kind),
bool(effectiveReadOnly),bytes(canonicalPath),H(fullData))); directory fullData empty.
Keep LC0ControlError1..8 and LC0StateError1..7 for existing control/Java/envelope rules.
VFS0aProfileError(uint256 code,uint256 pc):1path/seed collision,2mode/unsupported native,
3transfer/inspect bound,4invalid native constructor/bind use,5Object NEW profile.
VFS0aQuotaError(uint256 code,uint256 requested,uint256 limit):1seeds(count/bytes),
2inodes,3descriptors,4per-file bytes,5aggregate bytes. Whole1MiB cap retains
LC0StateError(1,...) rather than introducing a second checkpoint-size error.
VFS0aStateError(uint256 code,uint256 byteOffset):1framing/counts,2inode graph/names,
3file bytes/accounting,4descriptor/mode/cursor,5heap/frame/phase,6VFS commitments.
Start/view profile errors use pc0; real native/NEW errors use actual invoke/newPC.

## Finite limits and acceptance workload

Runtime<=256KiB, checkpoint<=1MiB; no silent ceiling increase. Initial production
candidate is one LOCAL runtime; if it does not fit, report exact measured blocker
for parent scope/module review. Standalone additive estimates do not satisfy this.
Pinned solc0.8.30/optimizer200/viaIR/Cancun/metadataoff, unchanged EVM accounting.
16seeds/65536seed bytes,64inodes,32descriptors including closed,65536per-file AND
aggregate ALL regular-file bytes (including seeds/RO), path limits above,4096transfer.
100M/30s ordinary,1B/120s explicit boundary,25M commit reserve; per-call1..4096 JVM
and internal units. Ordinary cases<=4096 total units; dedicated copy/quota<=65536.
**New VFS0a test-only slice allowance: <=4096 slices/case**, needed for full q1 Java
normalization/message-copy chains; old profiles retain256 slices. New gate20min/4GiB
external watchdog. Do not hide failed q1 chains or replace them with terminal replay.

Harness:24 Java8-primary roots in three8-root groups: Paths(existsMissing,seedFile,
seedDirectory,mkdirOnce,mkdirsNested,readonlyMkdir,lexicalAlias,comparablePaths);
Streams(readSingleEOF,readBulkSlice,createRoundtrip,truncate,append,twoWriterGap,
staleReadCursor,closeTwice); Errors(nullFileArg,missingInputMessage,
missingOutputParentMessage,directoryOpenMessage,readOnlyOutputMessage,
nullArrayBeforeClosed,boundsBeforeClosed,zeroLengthClosed). Use small owned C-locale
host tempdir oracles and opaque raw seed fixtures, never host files in production.
Full q1/q7 chains for mkdirsNested,lexicalAlias,readBulkSlice,createRoundtrip,truncate,
append,twoWriterGap,staleReadCursor,missingInputMessage,readOnlyOutputMessage; compare
one/control terminal machine/VFS roots, results and total counters within profile.
Record any Java21 differences explicitly, never alter Java8 expectations to match21.

Parent32 independent groups: (1)38pins/repro;(2)native identity/replacements;
(3)Comparable/base generic/default Code;(4)paths and bounds;(5)Object guard controls;
(6)File partial/failed construction;(7)real pending corridors/delegation;
(8)wrong owner/depth/PC/ID/field;(9)alias/local/foreign constructor privileges;
(10)truncate-before-bind resume;(11)failed open/quota no side effects;
(12)bound failing subclass/noGC;(13)byte/null/bounds/zero precedence;
(14)zero gaps/append/stale read;(15)exact message/cause Code;
(16)OOM during message/exception construction;(17)seed collisions/order/RO;
(18)64/65 inodes atomic mkdirs;(19)32/33 descriptors inclclosed;
(20)per-file/aggregate64KiB+1;(21)4096/4097 transfer;
(22)genuine combined exact1MiB/+1;(23)codec/root mutations;
(24)full-byte lookup/graph malformed;(25)owner/CAS/commitments;
(26)OOG/reserve/rollback/old-blob retry;(27)quantum/internal1 equality;
(28)inspect views/offsets/malformed/provenance;(29)cross-namespace/store;
(30)durable failure/no speculative outputs;(31)true new-process pending/write reopen;
(32)legacy/core preservation/final-artifact reruns. Keep concrete failures and controls.
Transport retains IOE0 bounded reads, internal symlink refusal, fsync ordering,
old-root recovery/ambiguous poison, embedded assets and no speculative failed output.

## Disjoint implementation writes

Runtime worker: ONLY jvmevm/runtime/local/vfs0a/**, including its source/assets/build/
README, append remaining unchanged30 bootstrap inputs, preserve frozen new8 pins.
Harness worker: ONLY jvmevm/localcontinuation/vfs0a/** (except parent_test.go and
validation_test.go reserved for parent) and jvmevm/testdata/local/vfs0a/**.
Parent: this plan/AGENTS/program/guides/Make/gitignore, independent tests/review,
integration and acceptance. Read-only peer artifacts permitted; no peer writes.
Do not accept stub compilation, missing-artifact skips or worker completion as proof.
