# MC-VFS0a focused preflight

Status: **PROPOSAL ONLY**. This is one bounded successor candidate conditional on parent acceptance of
MC-IOE0; IOE0 is frozen but is not accepted at this revision. Nothing here freezes an interface, authorizes
implementation, accepts EULA terms, or claims Minecraft execution, a listener, a world-capable filesystem,
Java SE, or standard deployment. No Minecraft/JAR/EULA file was created, read, or executed.

## Decision: the smallest genuine slice

Choose **MC-VFS0a**, an EVM-owned byte filesystem exercised only through reserved standard guest
`java.io.File`, `FileInputStream`, and `FileOutputStream` objects:

* `File(String)`; `exists`, `isFile`, `isDirectory`, `mkdir`, and `mkdirs`;
* `FileInputStream(File)`; `read()`, `read(byte[])`, `read(byte[],int,int)`, `close`;
* `FileOutputStream(File)` and `(File,boolean)`; the three corresponding `write` methods and `close`.

Defer `File` parent constructors, length/delete/rename/listing/canonical APIs, String stream constructors,
RAF/Data*/Buffered*, readers/writers, Properties, NIO, ZIP/JAR resources, timestamps, sync, locks, scheduler,
main and all world behavior. EOF is represented by `read` returning -1; this slice has no operation that
throws `EOFException`. IOE0's EOF class remains unchanged. No `initCause`; VM-origin AE message getters retain
IOE0's hard-unsupported profile.

This is not a host directory or Go map. EVM code normalizes every path, resolves and allocates every
inode/descriptor, checks read-only state, advances cursors, copies or mutates every byte, validates/re-encodes
state and atomically publishes the one head. The host may submit bounded raw seed bytes once and durably
transport an opaque EVM-issued checkpoint. It never resolves paths or performs filesystem/Java logic. Owned
host files below are TEST-oracle inputs only and never seed production VFS.

## Exact VFS profile recommendation

The namespace has inode 1 `/`, inode 2 `/work` (working directory), and read-only inode 3 `/ro`. Only
directories and regular files exist. IDs are monotonic nonzero u32 and never reused. A non-root inode has one
lower-ID directory parent and one name, so there are no links/cycles. Lookup hashes never replace full-byte
equality.

A `File` stores the exact lexical guest String. Its constructor throws a genuine NPE with null message for null
and otherwise has no VFS side effect. At each operation, EVM converts printable ASCII UTF-16 units
`0x20..0x7e`, treats only `/` as separator, prepends `/work` to relative paths, removes repeated separators
and `.`, and resolves `..`. Matching is case-sensitive and `\` is ordinary. Empty paths, root escape,
non-ASCII/control units, depth >16, a component >64 bytes, or canonical path >256 bytes are hard profile
errors, not host behavior or invented Java exceptions.

`exists/isFile/isDirectory` return false/typed truth without allocation. `mkdir` requires an existing writable
directory parent; `mkdirs` creates all missing components in order. Existing targets, a file parent, or any
read-only ancestor return false with no mutation. Seeds are regular files only; EVM normalizes them, creates
required seed-parent directories, rejects canonical collisions, assigns IDs, and applies their read-only bits.
`/ro` and descendants cannot be changed.

A file is canonical `length:u32 + exact contiguous bytes`; no sparse/chunk/host-file encoding. An input open
requires an existing readable regular file and cursor 0. Output append=false atomically creates a missing leaf
under an existing writable parent or truncates a writable regular file, then cursor 0. Append=true creates if
missing, never truncates, and each write chooses current EOF atomically. Opening a directory or read-only file
fails before mutation. Single write keeps the low 8 bits. Bulk transfer is at most 4,096 bytes; reads copy
available bytes and advance by the copy count, EOF is -1, and writes atomically copy all requested bytes and
advance. No seek/hole exists. Close is idempotent. A descriptor records id, inode, owner Java ref, READ or
WRITE(+APPEND), u64 cursor and PENDING_BIND/BOUND/CLOSED phase.

## Guest Code and private native status boundary

Pin ordinary Java Code for every public method above. Add only identity-gated private native primitives:
`File.stat0()I`, `File.mkdir0(Z)I`; `FileInputStream.open0(File)I/readOne0()I/read0([BII)I/close0()I`; and
`FileOutputStream.open0(File,Z)I/writeOne0(I)I/write0([BII)I/close0()I`. Binding requires the reserved
bootstrap image, declaring owner, private/native flags, exact name/descriptor/staticness and invocation mode.
A replacement, lookalike, wrong descriptor or public native call retains normal link/call failure.

Primitives return status only; they never mint a Java object, throw a canned Java outcome, or expose a host
callback. Open uses positive descriptor IDs and negative MISSING/DIRECTORY/DENIED statuses. Read uses 0..255
or count, -1 EOF and -2 CLOSED; write uses 0 success and -2 CLOSED. Wrapper Code branches on status. It
schedules real `new`, `invokespecial` and field stores for `FileNotFoundException`/`IOException`.
Missing/directory/denied messages are built by ordinary char-array loops and genuine `String(char[])` Code
from the exact lexical path plus the pinned suffix; closed uses the genuine literal String and
IOException(String) Code. No ABI exception/message payload and no direct heap minting substitutes for this
execution.

Ordinary wrapper Code performs arraylength/null and overflow-safe slice bounds checks before a native
transfer. Thus Java8-primary NPE/IOOBE construction and precedence are genuine bytecode/implicit-fault
effects. `len==0` returns before checking closed. No status primitive is invoked for a rejected
null/bounds/zero-length request.

## Constructor/checkpoint phases and atomic publication

A successful open/truncate/create is one native invoke unit, but its descriptor ID is returned before pinned
constructor Code stores the Java `handle:I` field. Keep the real gap: the descriptor is PENDING_BIND and owns
the stream ref while its field is still zero. Serialize descriptor ID, owner, constructor-frame depth and bind
PC. Validation re-derives the exact reserved owner field and pinned constructor Code and requires the ID in
the permitted success corridor (initialized local/stack), with an active post-super constructor frame. At the
exact putfield it becomes BOUND and the field/owner/descriptor must agree. After close it is CLOSED; the field
may retain ID. No generic int or arbitrary constructor can satisfy this phase. At most one pending bind exists
under the accepted single stack.

Failure status creates no inode/descriptor/content change; all read-only/path/quota checks precede successful
open effects. A checkpoint may validly occur after truncate but before handle putfield: restart resumes the
wrapper and must not reopen/truncate. Likewise a completed read/write is never repeated at a quantum edge.
Child machine and VFS validation/encoding/hash happen before one owner/epoch/head CAS publication and one
event. EVM revert/OOG rolls back bytes, descriptors, head and logs. Retry of the old blob equals control;
retry after commit is stale. Disk order remains IOE0's opaque blob fsync, trie commit, manifest-last
publication; new-process reopen uses existing code/state/blob and never installs or reconstructs file state.

## Proposed ABI, commitments and schema 1

Use separate LOCAL `VFS0aInterpreter`, paths `runtime/local/vfs0a`, package `localvfs/vfs0a`. Exact ABI:

```text
SeedFile {bytes path;bytes data;bool readOnly}
VFS0aSliceResult {uint32 schema;uint8 lifecycle;uint64 epoch;bytes32 checkpointRoot;
 bytes32 machineStateRoot;uint64 totalJvmSteps;uint64 totalInternalSteps;uint64 executedJvmSteps;
 uint32 executedInternalSteps;int32 result;uint8 javaKind;uint32 javaRef;bytes javaClass;
 bytes32 vfsStateRoot;uint32 inodeCount;uint32 descriptorCount;uint64 logicalFileBytes}
start(bytes32,bytes[],string,string,int32[],SeedFile[],uint64,uint32) -> (VFS0aSliceResult,bytes)
resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32) -> (VFS0aSliceResult,bytes) // no seeds
head(bytes32) -> (address,uint64,bytes32,bytes32,bytes32,bytes32,bytes32,bytes32,bytes32,uint8)
validateCheckpoint(bytes[],bytes) -> (bytes32 machineStateRoot,bytes32 vfsStateRoot)
inspectFile(bytes[],bytes,bytes,uint32,uint32) -> (uint8,bool,uint32,bytes,bytes32) // maxBytes<=4096
CheckpointCommitted(bytes32,uint64,bytes32,bytes32,bytes32,uint8,uint64,uint64)
```

There is no public mutator/import/upgrade/fork. `inspectFile` validates and normalizes in EVM, does no
execution/write, and does not authorize resume.

Domains are exactly `JVMEVM:MC:VFS0A:{ARTIFACT,BOOTSTRAP,CONFIG,MACHINE,SEED,VFS}:1`. Envelope magic is
`JVMVF0A1`, machine magic `VFA1`; old blobs are not upgraded. The 280-byte big-endian header is IOE0's 216
bytes plus `seedRoot,vfsStateRoot` before machine length/data. `seedRoot=H(abi.encode(DSEED,ordered exact
seeds))`; `vfsStateRoot=H(abi.encode(DVFS,uint32(1),seedRoot,H(canonicalVfsSection)))`; config binds
runtime/bootstrap/artifact/entry/args/all VFS constants/seedRoot; machine root additionally binds
`H(machineBytes)` and vfsStateRoot. Exact re-encode, no trailing bytes, and live owner/epoch/root/config/code
checks are mandatory.

Append one terminal VFS section: counters; increasing inode records
`id,kind,readOnly,parent,nameLen,name,dataLen,data`; then increasing descriptor records
`id,inode,ownerRef,flags,cursor,phase,bindDepth,bindPC`. Directories require no data; bound/closed records
require zero bind metadata. Recompute paths, uniqueness, totals, owner type/field, constructor phase and all
roots in EVM; serialize no cache/offset.

New hard errors are exact and never decoded as Java outcomes:

```text
VFS0aProfileError(code,pc): 1 path/encoding, 2 unsupported primitive/mode,
 3 transfer bound, 4 illegal constructor-bind phase
VFS0aQuotaError(code,requested,limit): 1 seeds, 2 inodes, 3 descriptors,
 4 per-file bytes, 5 aggregate bytes, 6 checkpoint bytes
VFS0aStateError(code,offset): 1 framing, 2 inode/order/parent/name,
 3 file bytes/totals, 4 descriptor/flags/cursor, 5 owner/field/pending,
 6 seed/VFS/machine root or canonical re-encode
```

Absent bootstrap methods (including deferred constructors/APIs) retain exact normal link/call errors.
Quota/profile failures revert before mutation rather than becoming fake disk-full Java exceptions.

## Exact bootstrap and finite quotas

If IOE0 is accepted, retain its exact 30 images and append, in this order: `java/lang/AutoCloseable`,
`java/io/Closeable`, `java/io/Flushable`, `java/io/File`, `java/io/InputStream`, `java/io/OutputStream`,
`java/io/FileInputStream`, `java/io/FileOutputStream` (38 total). Pin sources, class bytes/hashes, class graph,
fields, wrapper Code and private primitives at freeze. No host JDK class loading. The IOE0 images and all accepted-profile artifacts remain byte-identical; raw replacement is denied.

Ceilings: 16 seeds/65,536 seed bytes; 64 inodes; 32 descriptors; 65,536 bytes per file and **65,536 aggregate
mutable VFS bytes**; path/component/depth 256/64/16; 4,096 bytes per transfer; combined checkpoint 1,048,576;
<=4 raw guest classes and 65,536 bytes; call units 1..4,096 each, <=256 slices/case. Preserve 100M gas/30s
ordinary, 1B/120s dedicated boundary and 25M commit reserve. Whole new gate is 20 minutes/4 GiB RSS. These are
small LOCAL experiment limits, not world capacity, infinite gas, a budget raise, block compatibility, EIP-170
or CREATE proof.

## Oracle result and proposed EVM corpus

Owned-tempdir probes compiled with OpenJDK8 `-source 8 -target 8 -g:none`; Java8 1.8.0_504 is primary and
Java21.0.9 secondary. All 42 rows agreed except Java21's enhanced NPE text for four null-array rows; primary
Java8 message is null. Exact shared behavior: null File/path -> NPE(null); missing -> FNFE `<lexical> (No such
file or directory)`; directory open -> FNFE `<lexical> (Is a directory)`; read-only output -> FNFE `<lexical>
(Permission denied)`; closed nonzero transfer -> IOException `Stream Closed`; null beats closed; bounds beats
closed; zero length beats closed and returns 0/no-op; EOF single/bulk is -1, repeated EOF stays -1; close
twice succeeds; append preserves bytes and `write(258)` writes 2; nonappend truncates on constructor. `mkdir`
missing-parent/file-parent is false; `mkdirs` creates parents; repeats false.

Evidence is ignored under `build/java-diff-mc-vfs0a-preflight/`; `SHA256SUMS` has full hashes. Source hashes
are `9c5061907c617fc7e8e2df2ef527067882334bcdf63fbed75895e4b783bd1701` and
`e9962a98e12d42cba8011bec7d088b27968e36513d46b26f74369f683360b5d0`; Java8/21 main-output hashes are
`0bb813a86d89262720e3453f2d7fe753908b2e1fbdcd117e1baf8547d331cbfe` and
`a1f08fd1af5b01aa8753244310d55aaee06e4f9cd3d8e26fc84d987f613ec7f4`; both relative outputs are
`eca7d67e8faa26c6b9ca1322b3758b125653f8ba3523f4a8752754a9cac073db`. Every javac/JVM call had a 30s
timeout and 4GiB address-space cap;
observed maxima were 130252/67980 KiB compilers and 31344/41848/29340/38316 KiB JVMs, all exit 0; whole probe
was far below 20m. Commands/versions/metrics are preserved beside outputs.

Freeze exactly 24 Java8-primary roots, each expected int 1: `fileNull,basicKinds,
mkdirLeaf,mkdirNoParent,mkdirsNested,mkdirExisting,mkdirUnderFile,mkdirReadOnly`;
`fisNullFile,fisMissingMessage,fisDirectoryMessage,fisSingleEOF,fisBulkEOFZero,
fisBulkSlice,fisClosedPrecedence,fisCloseTwice`; `fosNullFile,fosMissingParentMessage,
fosDirectoryMessage,fosReadonlyMessage,fosTruncateOnOpen,fosAppendMask,
fosBulkSliceZero,fosClosedPrecedenceClose`. Run all one-call; q1 and q7 for mkdirsNested, fisMissingMessage,
fisBulkEOFZero, fisBulkSlice, fisClosedPrecedence, fosReadonlyMessage, fosTruncateOnOpen, fosAppendMask,
fosBulkSliceZero and fosClosedPrecedenceClose (20 chains), comparing outcome/counters/final machine/VFS roots
and inspected bytes.

Add exactly 32 parent-independent groups: 01-08 bootstrap identity/link/status and null/bounds/message
precedence; 09-16 normalization/collision/mkdir/read-only and inode/descriptor/file/aggregate exact-plus-one;
17-24 pending-bind/owner/field, truncate/append/cursor/closed, malformed canonical state and 1MiB
exact-plus-one; 25-32 reserve, genuine OOG rollback/retry/stale CAS, blob/trie/manifest failures and
new-process reopen at pending-bind/post-truncate/post-read/post-write. Poison host cwd and deny unrelated
directories; VFS results must not change. Retain unchanged IOE0, SC0/TL0/LC0/LB0, 2231, stock and repository
gates; counts remain separate.

## Measurement, write set and blockers

At unaccepted IOE0 review head `e6ec570`, decoded runtime is 233,286 bytes, SHA256 `507ed54d...59a0`,
leaving 28,858 bytes below the candidate 256KiB LOCAL build ceiling. That is only a read-only size
measurement: VFS Solidity size, checkpoint gas and 64KiB validation/commit gas are **unmeasured**. Overflow is
a blocker or a reason to modularize the new target, not permission to raise budgets or edit core.

If frozen, authorize only `jvmevm/runtime/local/vfs0a/**` (one Solidity writer), `jvmevm/localvfs/vfs0a/**`,
`jvmevm/testdata/local/vfs0a/**`, ignored role evidence, and parent-owned plan/Make/integration tests. Do not
edit production peer/network, core/vm/state/types, consensus, params, precompiles, gas accounting, settings,
any accepted artifact/profile, Minecraft/JAR/EULA files, or listener code. This document is the complete
one-stage recommendation, not another platform roadmap.
