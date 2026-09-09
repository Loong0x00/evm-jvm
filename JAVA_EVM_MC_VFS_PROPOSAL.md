# LOCAL Minecraft VFS/platform dependency proposal

Status: **documentation-only preflight; not frozen, not implemented, and not an
acceptance claim**. The parent is reviewing frozen MC-LC0 separately. This document
proposes a bounded successor only if LC0's actual resume, rollback, anchored-head,
and durable-reopen gates are accepted. It does not authorize a worker, a write set,
a budget change, Minecraft execution, EULA acceptance, a listener, or use of Codex
Fast/priority.

The target remains the unchanged official vanilla Minecraft server **1.12.2** on a
Java 8 compatibility profile. The first Minecraft milestone remains the genuine
guest-produced `Done (<digits>.<three digits>s)! For help, type "help" or "?"`
message after world preparation. A filesystem microtest, an EULA stop, main return,
or an early banner is not that milestone.

No Minecraft code was executed for this preflight. No `eula.txt` was created,
seeded, modified, or accepted; no server process or JVM main was launched; no
socket/listener was opened; and no artifact was downloaded or redistributed. The
already-present ignored official JAR was hash-checked first and then read only by
bounded ZIP/classfile/`javap` tooling.

## Recommendation: a small MC-VFS0, not “all platform”

After LC0 acceptance and the bridge prerequisites below, the smallest useful
filesystem slice is **MC-VFS0: one-instance regular-file byte VFS plus a narrow
`java.io` bridge**. It should prove that unchanged trusted guest bytecode can create,
open, read, overwrite, seek, extend with zero bytes, truncate, close, checkpoint,
retry, and reopen exact file bytes whose state was decided and committed by EVM
code. It should retain one LC0 execution stack and add no scheduler, Java main, JAR
loader, NIO provider, ZIP/DEFLATE, Properties, logging, network, or Minecraft run.

The important split is:

1. **Generic VFS mechanism:** paths, directories, inodes, byte contents, handles,
   cursors, seek, write/truncate, quotas, roots, and checkpoint durability.
2. **Java bridge:** guest `File`, `FileInputStream`, `FileOutputStream`, and the
   narrow `RandomAccessFile` methods listed below translate guest objects and Java
   calls to that mechanism inside EVM.
3. **Server readiness:** `Properties`, readers/writers and charsets; JAR resource
   URLs/NIO traversal; compression and NBT; atomic save rename/delete; logging;
   clocks; scheduling; virtual bind; and world generation. MC-VFS0 proves neither
   this layer nor the `Done` path.

Do not fold layers 1--3 into one stage. Conversely, do not call a host directory,
Go map, ABI-returned canned bytes, or no-op stream a VFS. “EVM-backed” here means
that EVM bytecode validates every path and operation, owns inode/handle allocation,
mutates the bytes, canonically encodes and hashes the VFS, and advances the anchored
head. A host may durably carry an opaque EVM-issued checkpoint/blob; it does not
perform filesystem or Java logic.

## Hash-gated targeted static evidence

The read-only file inspected was:

`/home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar`

It matched the program pins before inspection: 30,222,121 bytes, SHA-1
`886945bfb2b978778c3a0288fd7fab09d315b25f`, SHA-256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`.
The manifest names `net.minecraft.server.MinecraftServer`.

These are direct bytecode edges on the already-identified startup/world-preparation
path, not whole-JAR counts and not proof of runtime reachability under the current
interpreter:

* `nz.j()` constructs `File("server.properties")` at PCs 76--85 and `nw`; `nw` uses
  `File.exists`, `FileInputStream`, `Properties.load`, and `FileOutputStream` plus
  `Properties.store`. The one-argument `FileOutputStream` is a create-or-truncate
  dependency, not append.
* `nz.j()` constructs `File("eula.txt")` at PCs 96--105 and `nn`; `nn` reads it via
  `FileInputStream` and `Properties.load`, and on the not-accepted path writes an
  `eula=false` file via `FileOutputStream`/`Properties.store`. This is static
  evidence only. An affirmative virtual EULA file remains unauthorized pending
  separate explicit user approval.
* At PC 950, `nz.j()` calls
  `MinecraftServer.a(String,String,long,amz,String)`. The server constructor has
  already installed `bez` as `bfg` at PCs 160--169. World setup asks it for `bfe`;
  `bez.a(String,boolean)` constructs `bey`, whose `bfb` base creates the world,
  `playerdata`, `data`, and optional `structures` paths with `mkdirs`.
* `bfb` writes `session.lock` through `FileOutputStream` and
  `DataOutputStream.writeLong`, then later reopens it with `FileInputStream` and
  `DataInputStream.readLong`. It loads `level.dat` or `level.dat_old`. Its save path
  writes `level.dat_new`, deletes the old backup, and performs two `File.renameTo`
  transitions. Therefore timestamps/session lock and rename/delete are real later
  world-save dependencies; MC-VFS0 deliberately does not claim them.
* `MinecraftServer.a(...)` creates each `oo` world and calls `oo.b()`. That method
  constructs `ns` for `world/data/advancements`; the `ns` constructor immediately
  invokes its load routine. It also calls `Class.getResource` for
  `/assets/.mcassetsroot`, converts a JAR URL/URI, uses
  `FileSystems.newFileSystem`, `Files.walk`, `Path.relativize`, and
  `Files.newBufferedReader` for built-in advancements. The pinned JAR contains 488
  files under `assets/minecraft/advancements/` (320,962 uncompressed bytes, maximum
  8,066 bytes) and the zero-byte `assets/.mcassetsroot`. Thus immutable JAR paging,
  resource URLs, a narrow JAR/NIO provider, iteration, UTF-8, JSON, and class mirrors
  are hard pre-`Done` dependencies, but they are not generic writable-VFS0 scope.
* Spawn preparation calls `oo.r().c(chunkX,chunkZ)`. The Anvil path `aye -> ayk ->
  ayj` creates `region/r.<x>.<z>.mca`; `ayj` opens `RandomAccessFile(...,"rw")`,
  checks length, extends to sector boundaries, seeks, reads/writes integer headers
  and byte regions, and wraps compressed chunk payloads. This is direct evidence
  for real offset/seek/write semantics. It is not evidence that MC-VFS0's tiny file
  and per-call quotas can generate a world or that ZIP/NBT/DEFLATE is implemented.

Targeted class hashes and static outputs are under ignored
`build/java-diff-mc-vfs-preflight/`; notably
`targeted-evidence.json` has SHA-256
`9a2142f1c091afd06ef0bc70a835ca41466de739ac0517f41b04990b78301333`.
Obfuscated names and static inspection leave conditional branches unresolved. Only
future actual EVM traces can establish the exact dynamic file set/order.

## Proposed MC-VFS0 profile

The values below are a reviewable candidate, not authorized/frozen limits.

### Namespace and path rules

* One private namespace has fixed root `/`, fixed directories `/ro` and `/work`,
  and working directory `/work`. It is not a host mount or POSIX passthrough.
* VFS keys are exact bytes. MC-VFS0 accepts printable ASCII bytes `0x20..0x7e` only;
  `/` is the sole separator, matching is case-sensitive, and `\` has no separator
  meaning. This intentionally narrow path profile covers the proposed fixtures and
  observed literal server filenames; it is not general Java filename/charset
  support.
* A guest `File` retains its lexical guest `String`. At an operation, EVM converts
  supported ASCII UTF-16 code units to bytes, prepends `/work` for a relative path,
  removes repeated separators and `.` components, and resolves `..`. Empty
  components are discarded; an attempt to escape `/`, an empty final component
  where a file is required, non-ASCII/control input, or a quota violation is a hard
  profile error. No host string/path conversion is consulted.
* The canonical result begins with `/`; root has no name. Component length is at
  most 64 bytes, canonical path length at most 256 bytes, and depth at most 16.
* Only directories and regular files exist. There are no symlinks, hard links,
  devices, drive letters, permissions/owners, host locks, watch service, mmap, or
  current-host-directory behavior. Directory iteration, delete, and rename are
  deferred from MC-VFS0.

### Inodes, contents, and handles

* Inode 1 is `/`; 2 and 3 are fixed `/ro` and `/work`. New inode and descriptor IDs
  are strictly monotonic nonzero `u32` values and are never recycled in this slice.
* Every non-root inode has exactly one `(parentInode,nameBytes)` and therefore one
  canonical path. EVM checks the full name bytes after any hashed lookup, so a hash
  collision cannot alias entries. A parent must be a lower-ID directory; this
  makes cycles and forward-parent ambiguity invalid in schema 1.
* A file has an exact `u64` logical length. Contents are canonical contiguous
  4,096-byte chunks: all non-final chunks have 4,096 bytes; the final chunk has the
  remaining 1..4,096 bytes; a zero-length file has no chunks. There is no sparse
  encoding in VFS0. Extension explicitly materializes zero bytes; shrink removes
  suffix bytes/chunks. This favors a small unambiguous proof over scale.
* A descriptor is `(id,inode,ownerJavaRef,flags,cursor,closed)`. Flags are exactly
  `READ=1`, `WRITE=2`, `APPEND=4`; invalid combinations fail. `cursor` is `u64`.
  Closed records remain canonical because the associated Java object may remain in
  the no-GC LC0 heap.
* Opening an input stream requires an existing regular file and starts at cursor 0.
  Opening one-argument `FileOutputStream(File)` creates a missing file or truncates
  an existing writable regular file to zero, then starts at cursor 0. A proposed
  `FileOutputStream(File,boolean)` supports `false` identically and `true` as
  append; each append write chooses the current EOF atomically, not the stale
  cursor.
* `RandomAccessFile(File,"r")` requires an existing regular file. Mode `"rw"`
  creates if absent but **does not truncate** and starts at cursor 0. Other modes
  (`rws`, `rwd`) are explicit unsupported-profile outcomes until a sync policy is
  designed.
* A read of requested length zero returns zero. Otherwise it copies at most the
  available bytes and advances by the copied count; at EOF Java `read` returns
  `-1`. A write overwrites at the cursor and advances it; writing past EOF fills
  the exact gap with zero bytes. All arithmetic is checked before mutation.
* Generic `seek(SET|CUR|END,signedDelta)` computes a checked nonnegative `u64`
  cursor. The Java VFS0 bridge exposes `RandomAccessFile.seek(long)` as `SET` only
  and permits a cursor beyond EOF without extending the file.
  `RandomAccessFile.setLength(long)` shrinks or zero-extends; if the old cursor is
  beyond the new length, it becomes the new length. `length` and
  `getFilePointer` are exact `long` results.
* `close` marks the descriptor closed and is idempotent. A later operation on it is
  an I/O error. `flush` does not claim host durability: data is already in the
  candidate child machine state, and only successful checkpoint publication makes
  it durable. `FileDescriptor.sync`, fsync equivalence, advisory locks, and crash
  ordering between guest file operations are deferred.
* One JVM platform-binding invocation is one LC0 JVM dispatch unit. Read/write/
  zero-fill/truncate work per invocation is capped at 4,096 bytes, checked before
  mutation. The driver yields before the invocation if commit reserve is
  insufficient; it never checkpoints a half-completed Java call. A genuine EVM
  OOG/revert rolls back the whole call.

### Minimal Java bridge, and what it does not include

Proposed exact bridge surface for trusted VFS0 fixtures:

* `java/io/File`: constructors `(String)`, `(File,String)`, `(String,String)`;
  `exists`, `isFile`, `isDirectory`, `mkdir`, `mkdirs`, and `length`.
* `java/io/FileInputStream`: constructor `(File)`; `read()`, `read(byte[])`,
  `read(byte[],int,int)`, and `close`.
* `java/io/FileOutputStream`: constructors `(File)` and `(File,boolean)`;
  `write(int)`, `write(byte[])`, `write(byte[],int,int)`, and `close`.
* `java/io/RandomAccessFile`: constructors `(File,String)`; `read`, `read(byte[])`,
  `read(byte[],int,int)`, `write` variants, `readInt`, `writeInt`, `writeByte`,
  `length`, `getFilePointer`, `seek`, `setLength`, and `close`. Integer encoding is
  Java `DataInput`/`DataOutput` big-endian.

Bindings are selected only by reserved bootstrap class identity plus exact
name/descriptor/staticness and execute inside EVM. File/stream objects are ordinary
guest heap objects: a `File` retains its guest path `String`; a live stream retains
its descriptor ID; descriptor records retain the owner object reference. Checkpoint
validation requires those references and open/closed states to agree. A user class,
lookalike method, changed bootstrap image, wrong descriptor, or host request cannot
select a binding.

The profile requires pinned bootstrap images/interfaces for `File`, `Closeable`,
`AutoCloseable`, `Flushable`, `InputStream`, `OutputStream`, `FileInputStream`,
`FileOutputStream`, `DataInput`, `DataOutput`, and `RandomAccessFile`, plus their
exact superclass/interface graph (including the already present
`Serializable`/`Comparable` relations where applicable). It must not silently use
host JDK classes. `Buffered*`, `DataInputStream`, `DataOutputStream`,
`Reader`/`Writer`, `Properties`, charsets, URI/URL, NIO,
ZIP/GZIP/Inflater/Deflater, JAR providers, and NBT are deferred even though static
evidence shows that later Minecraft stages need them.

Ordinary absent-file/closed-stream/negative-seek/read-only errors must eventually
be catchable guest `FileNotFoundException`/`IOException`; short `readInt` requires
`EOFException`, and invalid bulk-array slices require the Java 8
`IndexOutOfBoundsException` behavior. They cannot become arbitrary EVM reverts or
host OS errors. This is a hard ordering dependency on fresh Throwable construction,
initialization, hierarchy, and handler-visible identity. Exact Java 8
message/cause/precedence behavior is still an unknown to pin with small Java 8
oracles before freeze; until then a bridge freeze is premature. Resource ceilings
and unsupported profile features remain hard EVM control/profile errors, clearly
distinct from Java exceptions.

## LC0-derived API and commitment proposal

Use a new versioned LOCAL contract/artifact, provisionally `VFS0Interpreter`; do
not alter or relabel the accepted LB0 monolith or frozen LC0 artifact. There is no
public host file mutator. All post-start file effects arise from guest instructions.

Proposed Solidity ABI additions relative to LC0 are:

```solidity
struct SeedFile { bytes path; bytes data; bool readOnly; }
struct VFS0SliceResult {
    uint32 schema; uint8 lifecycle; uint64 epoch;
    bytes32 checkpointRoot; bytes32 machineStateRoot; bytes32 vfsStateRoot;
    uint64 totalJvmSteps; uint64 totalInternalSteps;
    uint64 executedJvmSteps; uint32 executedInternalSteps;
    int32 result; uint8 javaKind; uint32 javaRef;
    uint32 inodeCount; uint32 descriptorCount; uint64 logicalFileBytes;
}

start(bytes32 instanceId, bytes[] rawClasses, string entryClass, string entry,
      int32[] args, SeedFile[] seeds,
      uint64 maxJvmSteps, uint32 maxInternalSteps)
  external returns (VFS0SliceResult result, bytes checkpoint);
resume(bytes32 instanceId, uint64 expectedEpoch, bytes32 expectedCheckpointRoot,
       bytes[] rawClasses, bytes checkpoint,
       uint64 maxJvmSteps, uint32 maxInternalSteps)
  external returns (VFS0SliceResult result, bytes childCheckpoint);
head(bytes32 instanceId) external view returns
  (address owner, uint64 epoch, bytes32 checkpointRoot,
   bytes32 machineStateRoot, bytes32 vfsStateRoot, bytes32 seedRoot,
   bytes32 artifactRoot, bytes32 configRoot, bytes32 runtimeCodeHash,
   uint8 lifecycle);
validateCheckpoint(bytes[] rawClasses, bytes checkpoint) external view
  returns (bytes32 machineStateRoot, bytes32 vfsStateRoot);
inspectFile(bytes[] rawClasses, bytes checkpoint, bytes path,
            uint64 offset, uint32 maxBytes) external view
  returns (uint8 kind, uint64 length, bytes data, bytes32 fileRoot);
```

`SeedFile` is an explicit platform input at `start` only. The host transports the
ordered raw path/data bytes and a read-only bit; EVM normalizes paths, rejects
collisions, creates directories/inodes, allocates IDs, and derives all roots. Seeds
are not Java objects or host-decoded properties/world metadata. VFS0 tests use only
small self-authored bytes and **no** Minecraft artifact, server config, world, or
EULA file. A later immutable artifact mount must use commitment-checked paging; the
30 MB JAR must not be copied into this 1 MiB checkpoint.

`validateCheckpoint` and `inspectFile` do no execution or anchor writes. They fully
validate/re-encode in EVM before returning data, are bounded to 4,096 returned bytes,
and do not attest provenance. Only exact equality with the live anchored head plus
owner/epoch/runtime/artifact/config checks authorizes resume.

### Domains and envelope

Let `H=keccak256` and use domain constants
`DSEED=H("JVMEVM:MC:VFS0:SEED:1")`,
`DVFS=H("JVMEVM:MC:VFS0:STATE:1")`,
`DCFG=H("JVMEVM:MC:VFS0:CONFIG:1")`, and
`DMACH=H("JVMEVM:MC:VFS0:MACHINE:1")`.

* `seedRoot = H(abi.encode(DSEED, ordered SeedFile[] exact input))`.
* `vfsStateRoot = H(abi.encode(DVFS,uint32(1),seedRoot,H(vfsBytes)))`.
* `configRoot` binds schema 1, current runtime code hash, exact bootstrap root,
  artifact root, entry class/method/args, fixed VFS profile constants, and
  `seedRoot`. It does not bind changing file contents.
* `machineStateRoot = H(abi.encode(DMACH,uint32(1),artifactRoot,configRoot,
  H(machineBytes),vfsStateRoot))`.
* `checkpointRoot = H(exact checkpoint bytes)`.

Proposed checkpoint magic is eight ASCII bytes `JVMELV01`. The big-endian header is
LC0's fields plus `seedRoot` and `vfsStateRoot`, followed by `machineByteLength:u32`
and exact machine bytes; its resulting fixed length is 280 bytes. No trailing bytes
or alternate encodings are accepted. VFS0 uses a new decoder and magic; LC0 schema
1 blobs are neither upgraded nor ambiguously accepted.

The machine stream begins with the LC0-derived execution/class/frame/heap/pending/
intern state in one newly versioned layout and contains exactly one terminal VFS
section:

```text
magic "VFS1"
nextInode:u32 nextDescriptor:u32 inodeCount:u16 descriptorCount:u16
logicalFileBytes:u64
inode records in strictly increasing id:
  id:u32 kind:u8 flags:u8 parent:u32 nameLen:u8 nameBytes
  length:u64 chunkCount:u16
  chunks in increasing zero-based index: index:u32 dataLen:u16 data
handle records in strictly increasing id:
  id:u32 inode:u32 ownerJavaRef:u32 flags:u8 cursor:u64 closed:u8
```

`kind` is 1 directory or 2 regular file; `flags` currently only bit 0 read-only.
Directories require length/chunkCount zero. A regular file's chunks must exactly and
minimally cover its length under the contiguous rule. Root/fixed-mount IDs,
parent/name uniqueness, no cycles, aggregates, Java owner references, flags,
cursors, and all bounds are revalidated from bytes. Canonical byte-for-byte
re-encoding is mandatory. Derived path indexes and chunk lookup caches are omitted
and rebuilt in EVM; host-supplied offsets, maps, inodes, descriptors, or Java refs
are never accepted.

### Errors

Preserve LC0 `LC0ControlError` meanings for ownership/head/budget/reentrancy. Add
hard errors only for non-Java profile/state boundaries:

```text
VFS0ProfileError(code, pc)
  1 path encoding/normalization/depth
  2 unsupported class/method/mode/flag
  3 per-operation byte bound
  4 unsupported node/namespace feature
VFS0QuotaError(code, requested, limit)
  1 inode count  2 descriptor count  3 per-file bytes
  4 aggregate logical bytes  5 combined checkpoint bytes
VFS0StateError(code, byteOffset)
  1 section truncation/trailing/size
  2 inode/root/order/kind/flags
  3 parent/name/path collision/cycle
  4 length/chunk/index/data canonicality
  5 descriptor/order/flags/cursor/inode/owner
  6 aggregate or vfsStateRoot mismatch
  7 Java File/stream heap consistency
```

The byte offset is absolute in the checkpoint or zero for aggregate invariants.
Hard errors revert and preserve head/logs. Java operational errors are successful
EVM calls with LC0's guest exception machinery still running or terminal
`UNCAUGHT_JAVA`; the host must not infer them from arbitrary revert text.

## Atomicity, retry, rollback, and restart

VFS bytes are part of `machineStateRoot`, and `vfsStateRoot` is also in the
EVM-anchored head. A successful slice performs this order inside EVM: validate old
head/blob/config; execute complete JVM units and complete VFS bindings; validate and
canonically encode the child; hash it; compare the old head again; update the one
head; emit exactly one commit event. Java return/output cannot become visible under
a child root that omits its preceding file effect.

If a call reverts or OOGs before head commit, all EVM storage/log changes roll back
and the old opaque checkpoint remains the only resumable state. No tracer, Go code,
or partial blob may reconstruct the attempted file. Retrying the identical old
checkpoint/input must produce the same child bytes/root; retrying after that child
commits must fail stale epoch/root, so a truncate or append cannot occur twice.

The local durable driver should reuse LC0's order: write and fsync the exact opaque
checkpoint blob by EVM-issued hash, commit StateDB/trie, then atomically publish and
fsync the manifest last. Before publication failure, reload the old durable
StateDB/root rather than pretending a consumed journal snapshot is live. An
ambiguous failure after publication reports unknown commit and requires reopen.
Reopen loads existing code and StateDB head, verifies code/root/blob, and resumes;
it never calls `SetCode`, injects file storage, scans a host directory into the VFS,
or silently starts fresh. Missing/corrupt blobs are hard availability failures.
This is LOCAL anchored-checkpoint durability, not on-chain byte availability,
portable import, POSIX fsync, or standard CREATE/deployment proof.

## Candidate finite ceilings

| Resource | Proposed MC-VFS0 ceiling |
|---|---:|
| ordinary LOCAL start/resume | LC0's 100,000,000 gas / 30 s |
| dedicated boundary/malformed call | LC0's 1,000,000,000 gas / 120 s |
| pre-commit reserve | LC0's 25,000,000 gas |
| JVM/internal units per call | LC0's 1..4,096 / 1..4,096 |
| successful slices per case | 256 |
| raw user classes / aggregate bytes | LC0's 4 / 65,536 |
| combined canonical checkpoint | LC0's 1,048,576 bytes |
| seed files / aggregate seed data | 16 / 65,536 bytes |
| all inodes / descriptors | 64 / 32 |
| one file / aggregate logical bytes | 131,072 / 262,144 bytes |
| one read/write/zero-fill/truncate binding | 4,096 bytes |
| path / component / depth | 256 / 64 bytes / 16 |
| whole gate watchdog / RSS | 20 min / 4 GiB |

These are intentionally tiny compared with a world, region files, or the 320,962
bytes of built-in advancement JSON alone. They retain LC0 call/checkpoint budgets
rather than silently raising them. Measurement may show even these bounds do not
fit; that is a blocker/report, not permission to change a frozen LC0 budget. All
calls remain LOCAL `runtime.Call` evidence with ordinary EVM charging and are not
signed-transaction, block-gas, EIP-170, or standard deployment claims.

## Required acceptance tests for any later freeze

A freeze should name exact generated class hashes and expected roots/results. At
minimum it should include:

1. **Exact bytes:** seed all 256 byte values, read at offsets/EOF, overwrite across a
   4,096-byte boundary, and compare EVM-returned bytes and `fileRoot` to fixed
   hashes. Include embedded zero bytes; no text transcoding.
2. **Independent cursors:** two input handles and one `rw` handle to one inode;
   prove seeks and reads advance only their owner, append resolves current EOF, and
   close survives checkpoint.
3. **Truncate semantics:** prove one-argument `FileOutputStream` truncates on open,
   `RandomAccessFile("rw")` does not, `setLength` shrink removes bytes and clamps a
   far cursor, growth creates exact zeros, and a failed oversized growth changes
   nothing.
4. **Paths/directories:** relative/absolute aliases resolve identically; case stays
   distinct; full-byte collision checks, `mkdir` versus `mkdirs`, file-as-parent,
   duplicate creation, root escape, component/depth/path limits, and read-only
   behavior match the pinned profile.
5. **Java bridge:** small trusted Java 8/21 oracle fixtures exercise every listed
   descriptor and big-endian int operation. JVM and EVM compare values, exception
   class identity, cursor, and bytes. No host oracle output feeds execution.
6. **Every checkpoint quantum:** run the mutation fixture one-call and with actual
   q1/q7 resume chains. Final machine/VFS roots and counters match where history is
   semantically irrelevant; no completed write/open/truncate repeats.
7. **Rollback/retry:** force reserve stop before a VFS invocation and genuine OOG
   during an attempted large mutation; old head/root/blob/logs remain. Retry from
   old state equals control; stale retry after success is rejected.
8. **Durable restart:** close the driver after open-handle, seek-past-EOF,
   post-overwrite, and post-truncate checkpoints; reopen in a new process and finish
   with identical bytes/cursors/roots. Inject failure after blob write and after
   trie commit but before manifest publication.
9. **Integrity negatives:** flip path, inode, chunk byte/length/index, cursor,
   ownerJavaRef, counts, roots, and trailing bytes with test-recomputed outer hashes.
   Standalone validation rejects semantic corruption; any host-changed canonical
   state also fails live-head binding.
10. **Quota boundaries:** exact/plus-one path, component, depth, inode, descriptor,
    file, aggregate byte, operation, and checkpoint limits. Failures are the exact
    hard error and offset/code, never Java OOM, partial file data, or raised budget.
11. **No fallback:** poison host cwd/files and run with inaccessible/random host
    directories; results remain identical. Trace no host file open except owned
    checkpoint/database files and trusted test inputs. No class/path/file metadata
    is injected through `StateDB`.
12. **Regression separation:** all LC0 acceptance chains and accepted LB0/2231/
    stock/bootstrap/artifact/CLI/Python/demo/AOT gates remain unchanged. VFS counts
    are reported separately and make no Minecraft or Java SE claim.

No VFS0 fixture or seed may be named `eula.txt` or contain an affirmative EULA
setting. Any later EULA-stop or startup execution requires separate explicit user
approval and a separately pinned VFS/config root.

## Hard dependencies and bounded order toward Minecraft

MC-VFS0 should not be mistaken for the immediately executable next commit. The
parent should order bounded stages by accepted evidence:

1. **Accept LC0 first.** VFS work depends on proven actual resume, canonical
   validation, stale-head CAS, OOG rollback, and disk/new-process reopen. Do not
   design file durability atop the extraction-only preflight result.
2. **Bridge prerequisites:** fresh guest Throwable construction for
   `IOException`/`FileNotFoundException`/`EOFException`, exact reference/void/long
   bridge descriptors, ordinary File/stream object layouts, byte-array bulk access,
   and supported construction of non-literal path/mode Strings. Keep this bounded;
   it is not all Java I/O or Throwable.
3. **MC-VFS0 mechanism + narrow bridge:** accept only the profile and microtests in
   this document. This is the first actual EVM-backed file-byte claim.
4. **VFS1 namespace/durability operations:** add deterministic directory listing,
   delete, same-namespace rename/replace, virtual timestamps, session-lock behavior,
   larger resumable multi-chunk service operations, and exact Java exceptions.
   These are required by `level.dat_new -> level.dat` and Anvil paths.
5. **Immutable artifact/resource layer:** commitment-checked raw JAR pages, EVM ZIP
   central-directory parsing and DEFLATE, manifests/resources, then only the
   workload-needed URL/URI/NIO JAR traversal (`Class.getResource`, `FileSystem`,
   `Path`, `Files.walk/newBufferedReader`). Artifact bytes stay outside mutable
   world-file contents but both roots enter config/checkpoints.
6. **Java data I/O:** buffering, DataInput/DataOutput streams, Properties syntax,
   UTF-8/readers, GZIP/Inflater/Deflater and NBT. Prove a generic properties file,
   session-lock, level metadata, and a tiny region-file fixture independently.
   Do not add or exercise EULA-specific content without separate user approval.
7. **Other platform prerequisites:** class mirrors/resource lookup, collections/
   JSON, guest logging/outbox, deterministic clocks/entropy, cooperative tasks and
   only used monitor/atomic behavior, then a virtual bind namespace. None may be a
   blanket no-op.
8. **Only after separate EULA/config approval:** unchanged pinned server checkpoints
   through its real path, eventually the world-preparation return and exact guest
   `Done` event, atomically committed with all VFS/world/output effects.

Main/String-array launch, scalable class/JAR loading, String builders/formatting,
Class mirrors, collections, Throwable APIs, scheduler, time, logging, and virtual
network bind are all still blockers. MC-VFS0 does not promise them. Full threads,
parallelism, POSIX, Java SE/NIO provider conformance, a host listener, client
connectivity, and standard deployment remain outside the first artistic LOCAL
startup goal.

## Proposed later write sets (not authorized)

If the parent freezes MC-VFS0, keep it isolated in new paths:

* runtime: `jvmevm/runtime/local/vfs0/**` (one Solidity writer; new versioned
  contract/artifact only);
* harness/durable transport: `jvmevm/localvfs/vfs0/**`;
* trusted fixtures: `jvmevm/testdata/local/vfs0/**`;
* worker evidence: ignored `build/java-diff-mc-vfs0-ROLE/**`;
* parent-only integration: Make targets, guides, the frozen plan/review, and shared
  gate wiring.

Do not edit `jvmevm/runtime/JVMSubsetInterpreter.sol`, any LC0 artifact/source,
accepted stock modules/fixtures/budgets, peer/network code, `core/vm`, `core/state`,
consensus, params, precompiles, gas accounting, global settings, or the pinned
Minecraft JAR. No code/account injection may be presented as standard deployment;
LOCAL one-time harness installation remains labeled as such.

## Unknowns that block a freeze or readiness claim

* LC0 actual resume/durability acceptance is pending parent review.
* Exact Java 8 file-exception messages/cause/close corner cases and bootstrap-image
  hashes are not pinned yet.
* The proposed checkpoint/commit reserve and validation cost are unmeasured for VFS
  bytes; contiguous chunks may make even the tiny quota too expensive.
* No dynamic startup trace establishes all files, operation order, maximum region
  write, descriptor concurrency, or which error branches occur before `Done`.
* Built-in advancement JAR traversal is visibly on world construction, but the
  minimal URL/URI/NIO/JAR subset and deterministic iteration order are not frozen.
* Fresh-world generation size, gas, storage, checkpoint count, and compressed region
  behavior remain unknown and are expected to exceed VFS0.
* Rename/delete replacement behavior, virtual timestamps/session locks, Java file
  equality/canonicalization, non-ASCII names, sync/durability, and multi-fiber handle
  interactions are deferred.
* No affirmative EULA input or Minecraft execution is authorized. No statement here
  is legal acceptance or server-readiness evidence.
