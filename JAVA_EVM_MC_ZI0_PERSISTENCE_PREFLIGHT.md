# MC-ZI0 bounded persistent-index preflight

Status: **measurement only; NOT frozen or accepted**. Base `10ed2c5ef`; accepted
AS0 remains the immutable byte store and VFS0a remains the latest JVM/filesystem.
This proves no DEFLATE/plain CRC, ZipFile/ClassLoader, class parsing, Minecraft run,
EULA/listener, or Done marker. No official JAR was uploaded, copied, or executed.

## Disposable implementation and authority boundary

I copied the parent's corrected prototype, adversarial driver, corrected-gaps driver,
and originals into ignored `build/java-diff-mc-zi0-persistence-preflight/parent/`.
The new ignored prototype consumes only an ordinary-CREATEd, EVM-filled and sealed
accepted AS0 controller. Go generates trusted ZIP/flate fixture bytes and ABI calls,
commits/reopens opaque StateDB state, and displays EVM results; it supplies no page,
ZIP catalogue, name, offset, parsed record, index, or SetCode installation authority.
The 20554/2100796/name-total dimensions below come only from prior static inventory.

Pinned solc `0.8.30+commit.73712a01`, optimizer 200, viaIR, Cancun, metadata off
produced 9752-byte init and 9102-byte runtime. Owner/store/content are constructor-only
storage bindings (no immutable substitutions, setters, upgrade, reset, import, fallback,
or host installer), so runtime Keccak is fixed across measured owners/stores. Every
mutator and final consumer rechecks accepted AS0 runtime Keccak
`c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896`,
address, sealed state and EVM content commitment.

Candidate measurement ABI:

```
constructor(address sealedAS0, bytes32 assertedContent)
discover()
scan(uint32 expectedEntry,uint32 expectedCursor,bytes32 expectedRolling,uint16 units)
finish(uint32 expectedCount,uint32 expectedCursor,bytes32 expectedRolling)
entry(uint32) -> (bytes rawName,bytes32 packedRecord)
lookup(bytes rawName) -> (bool,uint32 index,bytes32 packedRecord)
```

Public scalar getters expose binding/header/progress, `rolling`, and `finalRoot`.
Phase 0 is BOUND, 1 STAGING, 2 FINAL. `rolling` is explicitly only a staging/CAS
 diagnostic; `finalRoot` remains zero and `entry/lookup` reject until successful
finish. Private mappings cannot publish partial records. Finish requires exact count,
CD end and rolling root. Failed calls are reloaded from the prior committed root.

Each entry uses exactly two nonzero logical storage slots: `records[index]` and
`nameIndex[keccak256(rawName)]=index+1`. Packed-record bits (LSB first) are:

| bits | width | field |
|---|---:|---|
|0..24|25|CEN raw-name position|
|25..49|25|local-header position|
|50..74|25|compressed-data start|
|75..99|25|compressed size|
|100..131|32|declared plain size|
|132..163|32|stated CRC32|
|164..172|9|raw-name length|
|173..188|16|flags|
|189..192|4|method|
|193..194|2|descriptor: 0 none, 1 unsigned-12, 2 signed-16|
|195..255|61|must remain zero|

`dataEnd=dataStart+compressedSize`; descriptor form derives `recordEnd`. The rolling
step additionally binds dataEnd, recordEnd and CEN-record end, so omitted derived
values are not lost. Five byte positions/sizes are below the 32MiB AS0 bound; plain
size retains all 32 bits. On occupied hash slots, duplicate/collision handling rereads
both complete names from the same AS0. Entry and lookup likewise compare every byte;
a one-byte-changed lookup is measured not-found, never hash-only success.

With `H=keccak256`, Solidity `abi.encode`, `D0=H("MC-ZI0/index/v1")` and
`DE=H("MC-ZI0/entry/v1")`:

```
I0=H(encode(D0,this,owner,store,AS0_CODEHASH,content,length,
             eocd,cdOffset,cdSize,count))
Ii+1=H(encode(DE,Ii,i,H(name),nameLen,flags,method,crc,comp,plain,
                local,dataStart,dataEnd,recordEnd,cenRecordEnd))
```

Only `Icount` copied by finish is final index authority. AS0 caller roots remain
transport assertions and instance-bound commitments, not official whole-JAR SHA256.

## Persistent execution measurements

Every successful memory mutation was `StateDB.Commit`, trie/code commit, sync and
reload. The disk run additionally did LevelDB trie/code sync, manifest-temp write+
fsync, atomic rename and directory fsync **after every mutation**; it never batched
scan calls. The manifest binds context, owner, AS0/index addresses, length/content,
both fixed code hashes and state root. Mutable cursors are read back from EVM, not
accepted from the manifest. A real fresh executable reopened at entry 10277, resumed,
finished, then a second fresh executable reopened FINAL and checked first/last
entry/full-byte lookup and the final root.

| generated run | key result | gas |
|---|---|---:|
|target-shaped 20554, 4057736B, 496 AS0 pages, CD exactly2100796B|322 q64 batches; index root `d77e340054c70abdea5388ddec218812af50d189060545ddf961ed4a045f2759`|discover69091506; scans2383134028 sum / 7465246 max; finish45028|
|capacity 32768, 8159254B, 997 pages, CD exactly4194304B|512 q64 batches; 65536 entry slots|discover69091506; scans4459095973 sum / 8718707 max|
|64 simultaneous max records|name256, valid central+local extra1024, comment1024|one scan18535140|
|empty archive|FINAL zero-entry root|discover70900; finish45028|
|same 128-entry binding q1 / q64|identical index root `71c502e5d13f44ea440557daadde34b662a7f1f670c134f767a275a7b795cb3e` and state root|16735709 / 10802777 scan sums|
|dense 65532-byte EOCD-signature comment|accepted under ordinary cap|78054633 discovery|
|CD cap +1 byte|exact `ZI0Error(7)`, no OOG|69065247 discovery|

Target transport costs were AS0 CREATE611673, append881638867 aggregate over496
calls/1830926 max, seal34194, and index CREATE1920141. The target made exactly823
durable publications/reloads. Commit/publication time was4604ms total/9ms max;
maximum EVM call time was93ms; target end-to-end including both process reopens was
7670ms. Final combined state root was
`6584d08a063daeed008eb0762fa3ad4e321c1c0c26c993194fd75143c1654d35`.
The disk tree measured6187730B immediately before index CREATE and41449537B after
FINAL reopen (observed delta35261807B). This includes AS0/code/trie and LevelDB
layout/compaction, so it is actual transport disk use, not a canonical index encoding.
The capacity memory run made1514 commit/reloads and took6112ms. Entire final run was
18194ms with272364KiB process max RSS, below20min/4GiB. All semantic calls stayed
within100M/30s; no 1B boundary call or trace harvesting was needed.

The persistent scanner reproduced all **25 original** outcomes and all **12 definite
parent refusals** with exact selector `ZI0Error(uint256)` = `0x2cb107ad`; no arbitrary
error or empty OOG was accepted as semantic refusal. It also covered cross-batch
duplicate rejection, failed-CAS rollback then successful retry, owner/cursor/rolling/
finish-root/phase/early-entry/early-lookup controls, q1/q64 equality, cross-page ranges,
and final lookup. Error codes exercised/specify: 1 owner; 2 AS0 code; 3 sealed/content
binding; 4 phase; 5 short ZIP; 6 EOCD ambiguity/framing; 7 count/CD cap; 9 ZIP64
policy; 10 scan CAS; 11 units; 12 CEN signature; 13 lengths; 14 flags/disk/sentinels;
15 method/stored size; 16 bounds; 17 extra/ZIP64 extra; 18 duplicate; 19 hash collision;
20 LOC header; 21 LOC lengths; 22 LOC extra/name; 23 data range; 24 LOC sizes/CRC;
25 descriptor; 26 descriptor/CD intersection; 27 local order/overlap; 29 finish;
30 unpublished; 31 entry bound; 32 lookup length. Codes8/28 are unassigned.

ZIP64 policy measured here: reject locator signature `0x07064b50` only at the exact
20-byte structural prelude position of an otherwise empty classic archive. A nonempty
archive with material between framed CD and EOCD already fails classic CD framing.
Signatures in ordinary opaque names/payloads are accepted; no whole-payload signature
scan occurs. This precise policy remains a candidate for parent freeze, not acceptance.

## Reproduction, pins and remaining gaps

```sh
node build/java-diff-mc-zi0-persistence-preflight/build.js
# byte-identical rebuild against saved artifact
go build -o build/java-diff-mc-zi0-persistence-preflight/probe \
  build/java-diff-mc-zi0-persistence-preflight/main.go
timeout --signal=TERM --kill-after=15s 1200s \
  build/java-diff-mc-zi0-persistence-preflight/probe
build/java-diff-mc-zi0-persistence-preflight/probe verify \
  build/java-diff-mc-zi0-persistence-preflight/disk-target
```

Source SHA256 `ab85fdb4f8710c4d58c639de191c62873ee26f29fc87b92223f0e476700f8b85`; runtime SHA256
`808ef488ad768c3a5082db37bf6ec4735f4d2c2d2f74b43887a09069896ef974`; runtime Keccak
`50e118d99c52d2953f2aed608e37683d5bf136c6a63d9970ccb8f80dc0948dc6`; artifact JSON SHA256
`6885dd02ecb833360dc111cb8c6d9da2dc44d963bcfcd49541c456b798510894`; final report SHA256
`16c0380ee3fc2ec626c470fbd8e797cbac4b2ed4dd78060441fcf1f483e13a22`. Copied parent corrected25/corrected-gaps reruns also
passed25/14; their reports hash `d9f56729...c96c07d` / `4c43217d...bcd4b5`.

Remaining freeze work: parent independent replay and exact ABI/error/ZIP64-policy
choice; production transport hardening and publication-failure injection; practical
hash-collision generation is unavailable (the full-byte collision branch is code
review only). Disk delta is LevelDB-specific. No inflation, plain CRC proof, stored
byte consumer, Java resource/ClassLoader integration, official artifact EVM identity,
or Minecraft startup was attempted. A failure of the unchanged32MiB/8192/4096-read,
32768-entry/4MiB-CD/64-unit,100M/1B limits remains a blocker, not a cap raise.
