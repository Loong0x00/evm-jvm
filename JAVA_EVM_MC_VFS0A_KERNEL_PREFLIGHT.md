# MC-VFS0a EVM-kernel/codec implementation preflight

Status: **MEASURED STANDALONE PROTOTYPE; NOT A PRODUCTION FREEZE OR
ACCEPTANCE**. Base is `b5f2c5b`; accepted IOE0 remains 233,286 bytes,
SHA256 `507ed54d56d4cbe5e559013fbf5a3e598d75a28c0ffe33735573f646eac659a0`.
This worker changed no production/runtime/core/peer/settings/accepted artifact.
No Minecraft/JAR/EULA/listener execution occurred.

## What actually ran

Ignored `build/java-diff-mc-vfs0a-kernel/` contains a Solidity 0.8.30 contract
and an opaque ABI/action driver. Geth's unchanged EVM executes all path lookup,
inode/descriptor allocation, cursor changes, byte reads/writes, quotas, codec
validation, roots and owner-head CAS. Contract memory plus its returned canonical
blob is the sole filesystem; Go has no VFS map, host directory, path resolver or
Java evaluator. Go only encodes trusted raw seeds/actions, transports blobs, and
checks fixed returned bytes/statuses. Persistent StateDB storage contains only
`(epoch,root)` heads.

The mechanism initializes `/`=inode1, `/work`=2 and read-only `/ro`=3. IDs are
monotonic u32. It supports ordered raw seeds, mkdir/mkdirs, input/output open,
create, truncate, append, bind, read, write and close. Descriptor cursors are
independent u64 values; closed records remain quota-visible. Data is contiguous;
extension beyond EOF allocates zero bytes. Effective read-only walks ancestors.
Input of a read-only file succeeds; output fails before mutation.

The prototype deliberately calls two distinct EVM routines: `_lexical` validates
printable ASCII and collapses repeated `/`/one trailing `/`, while `_canonical`
then applies relative `/work`, `.` removal and `..` resolution. Thus
`logs//./sub/` first remains lexically dotted and only the VFS operation resolves
the dot. **Production must instead execute lexical slash normalization in ordinary
`File(String)` Java Code and store that normalized lexical String; only the native
VFS operation performs canonical dot resolution.** Error prefixes use that stored
lexical String and deterministic English/C-locale suffixes, not canonical or raw
host text.

## Production codec/root recommendation (parent must freeze)

All integers below are unsigned, big-endian, with no alignment or padding. Bytes
are exact; bool is exactly 0/1. Reject overflow, non-minimal values, malformed
order, bad roots, trailing bytes and any decode/re-encode difference.

The proposed 280-byte envelope header is exactly:

```text
0 magic[8]="JVMVF0A1"; 8 schema:u32=1; 12 instanceId:bytes32;
44 epoch:u64; 52 parentCheckpointRoot:bytes32;
84 runtimeCodeHash:bytes32; 116 artifactRoot:bytes32;
148 configRoot:bytes32; 180 machineStateRoot:bytes32;
212 seedRoot:bytes32; 244 vfsStateRoot:bytes32;
276 machineLength:u32; 280 machineBytes[machineLength]
```

The terminal canonical VFS section in `machineBytes` should be:

```text
nextInode:u32, nextDescriptor:u32, inodeCount:u32,
descriptorCount:u32, logicalFileBytes:u64;
inode[id order]: id:u32, kind:u8, readOnly:u8, parent:u32,
                 nameLength:u8, dataLength:u32, name, data;
descriptor[id order]: id:u32, inode:u32, ownerRef:u32, flags:u8,
                      cursor:u64, phase:u8, bindDepth:u16, bindPC:u32
```

`kind` is DIR=1/FILE=2; flags are READ=1, WRITE=2, APPEND=4; phases are
PENDING_BIND=1, BOUND=2, CLOSED=3. Directory data is absent; file data is exact
contiguous bytes. Names are 1..64 bytes except root's empty name. Parents are
lower-ID directories; sibling names are unique by full bytes, never hash alone.
`logicalFileBytes` is recomputed over **all** regular-file data, including seeds,
mutable and read-only files. Cursors need not be <= current EOF. Bound/closed bind
metadata is zero; at most one pending record exists on the accepted single stack.

With `H=keccak256`, use the proposal's exact domains and formulas:

```text
seedRoot = H(abi.encode(DSEED, ordered exact SeedFile[]))
vfsStateRoot = H(abi.encode(DVFS,uint32(1),seedRoot,H(vfsSection)))
machineStateRoot = H(abi.encode(DMACH,uint32(1),artifactRoot,configRoot,
                                H(machineBytes),vfsStateRoot))
checkpointRoot = H(exact envelope)
```

`configRoot` must bind all limits, bootstrap/runtime/artifact/entry/args and
`seedRoot`. Proposed `head(instanceId)` returns exactly `(owner,epoch,
checkpointRoot,machineStateRoot,vfsStateRoot,seedRoot,artifactRoot,configRoot,
runtimeCodeHash,lifecycle)`. Proposed read-only `inspectFile(rawClasses,
checkpoint,path,offset:u32,maxBytes:u32)` returns `(kind:u8,effectiveReadOnly:bool,
inode:u32,data:bytes,fileRoot:bytes32)`, requires `maxBytes<=4096`, validates and
canonically re-encodes the whole blob in EVM, and neither executes nor writes a
head. It cannot authorize resume; only owner+live epoch+exact checkpoint root can.
Offset beyond EOF returns empty without changing any descriptor.

The prototype codec uses the same record widths/order but a smaller standalone
68-byte `JVMVF0A1` header and root `H(abi.encode(DVFS,H(blob)))`. Its measured roots
are mechanism evidence, **not** the production root/schema freeze.

## Constructor/bind corridor recommendation

Support honest default/escaped File/stream receivers rather than introducing a
new no-callback Object shortcut: before native open, `handle:I==0` and there is no
descriptor. A successful native input open, or output create/truncate, first checks
path, type, effective read-only, inode/file/aggregate/descriptor quotas and owner.
Only then, in one EVM unit, it performs create/truncate and allocates one descriptor
as PENDING_BIND. Failure changes no inode, descriptor, content, head or log.

PENDING_BIND serializes the stream `ownerRef`, exact constructor frame depth and
post-native bind PC. Validation must re-derive the reserved declaring image and its
`handle:I` field; require an active post-super constructor frame at that depth,
receiver==ownerRef, field==0, and descriptor ID in the one pinned stack/local
corridor from native return through the exact `putfield`. A generic integer,
foreign constructor or wrong field cannot satisfy it. The matching `putfield`
updates the Java field and phase BOUND atomically and zeros bind metadata. Resume
of a pending checkpoint continues at the corridor; it must not reopen/retruncate.
A later throwing user subclass leaves the already-bound descriptor open under the
explicit no-GC/no-finalizer profile. This prototype proves persisted owner/depth/PC
matching and truncate-before-bind, but has no Java frame/heap and therefore does
**not** prove the production field-corridor validator.

## EVM observations

All gas numbers are actual Cancun EVM `runtime.Call` gas (no transaction intrinsic).
Every observed use is below the unchanged 100M ordinary cap; boundary calls were
configured at finite 1B. Selected exact results from `run.json`:

| EVM operation | gas | blob bytes | observed result |
|---|---:|---:|---|
| seed+mkdir+RO read+create/write | 514,421 | 303 | read `READ` |
| writer B truncate, writer A writes at cursor3 | 499,221 | 332 | `00 00 00 44` |
| reader cursor4, truncate, EOF, append | 716,333 | 414 | EOF twice; file `XY` |
| read-only output attempt | 571,380 | 414 | denied; identical VFS root |
| pending truncate then resume bind/write | 218,132 | 164 | empty before bind, then `N` |
| canonical validate | 123,201 | 164 | trailing=StateError; tamper=Stale |
| 65,536-byte read-only seed | 17,552,648 | 65,674 | succeeds |
| aggregate +1 with full seed | 34,077,274 | — | Quota; head unchanged |
| per-file 65,536 +1 append | 34,063,282 | — | Quota code 4 |
| 64 inodes / attempted 65th | 7,542,187 / 2,921,198 | 1,217 | success / Quota |
| 32 closed descriptors / 33rd | 2,291,183 / 802,484 | 1,032 | success / Quota |
| 4,096 write / 4,097 write | 2,540,412 / 2,244,961 | 4,259 | success / Profile |
| retry exact parent after 100,000-gas OOG | 6,789,615 | 8,355 | commit; old parent Stale |

Sixteen seeds succeed (1,049,950 gas,407-byte blob), seventeenth reverts Quota.
Root escape and `inspectFile(maxBytes=4097)` revert Profile. A valid data-byte
change remains canonically decodable but changes its root and is rejected against
the live head; malformed/trailing encoding fails structural validation. The low-gas
resume consumed exactly 100,000, returned no child, and left epoch/root unchanged;
retry used the identical parent blob/actions. No host recovery fabricated a head.

## Size, resources and limits

Pinned compiler/settings: solc `0.8.30+commit.73712a01`, optimizer 200, viaIR,
Cancun, metadata disabled. Standalone runtime is **16,241 bytes**, SHA256
`90a4f5e0d106cd9fb77c65a03aeaeb61e8109f1f27dbb4d3dd0224ae71985c43`,
Keccak code hash `df1e9777d58e7e64eeaefdfa45862c588a8af6252f413a350961dfb6ee1e55ff`.
Solidity source is 22,343 bytes, SHA256
`f810f199d2d3e8c5e5df387e42963c37b112d7e7d5e387224c33fd8ff2b26ab3`.
Largest measured blob is 65,674 bytes. Final driver run: 215ms, observed max VmRSS
20,276KiB; compile: 2,997ms/267,224KiB. Both exit0, machine-specific, below the
20min/4GiB watchdog.

IOE0's 28,858-byte arithmetic headroom minus this standalone runtime is 12,617
bytes (233,286+16,241=249,527). This is **not integrated size proof**: wrappers,
bootstrap images, native identity gates, Java field/frame validation, full machine
codec and commit event are absent, while compiler linking/dead-code effects are
non-additive. No <=256KiB production claim follows.

Hard limits present are 16 seeds/65,536 seed bytes, 64 inodes, 32 descriptors
including closed, 65,536 per file and aggregate all-file bytes, depth16,
component64/path256, transfer/inspect4096 and checkpoint1,048,576. The standalone
VFS quotas make a 1MiB blob unreachable; exact 1MiB/+1 combined Java+VFS checkpoint
tests remain required at integration.

## Reproduction and remaining gaps

```sh
cd build/java-diff-mc-vfs0a-kernel
npm ci --ignore-scripts
node build.js
go build -o driver .
timeout 1200s ./driver >run.json 2>run.err
sha256sum VFS0aKernelPrototype.sol runtime.hex abi.json main.go run.json
```

Final `run.json` SHA256 is
`1eafceafc8aa303a4f0ffb1b5c713abb7be941f334fdb8eec276a7936d11b104`.
Not implemented/proved: eight wrapper/bootstrap images, Java Code/native identity
binding, actual heap field/frame corridor, IOE/FNFE construction, combined 280-byte
LC0 machine codec, 1MiB boundary, commit reserve/event, durable blob/trie/manifest
reopen/failure injection, integrated runtime size, or whole-VM continuation. This
is not Java wrapper execution, a host filesystem, Minecraft startup, or acceptance.
Production freeze must wait for wrapper evidence and parent integration/review.
