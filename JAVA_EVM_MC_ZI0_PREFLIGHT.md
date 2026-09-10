# MC-ZI0 EVM ZIP index preflight

Status: **measurement/preflight only; not an implementation freeze or acceptance**.
Base `3e1dedbe6`; accepted AS0 is `64ea6b62f`. VFS0a remains the latest accepted
JVM/filesystem. ZI0 identifies ZIP directory metadata and committed compressed byte
ranges only: it is not DEFLATE, CRC verification of plain bytes, ZipFile/ClassLoader,
class parsing, `main`, Minecraft execution, EULA/listener, or Done evidence.

## Evidence boundary and format reference

The official artifact was only read as static bytes at the exact preparation path:
`/home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar`.
It was not executed or copied into a fixture. Rechecked size `30222121`, SHA-1
`886945bfb2b978778c3a0288fd7fab09d315b25f`, and SHA-256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`.
The host SHA is input/static evidence, not proved by AS0's instance-bound roots.

Format decisions below use PKWARE APPNOTE 6.3.10 (2022-11-01), especially 4.3.7,
4.3.8, 4.3.12, 4.3.14--16 and 4.4.4, fetched from
`https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT` (local transport SHA-256
`0b993022a7d320a0bf704e6980bea36fafd17a6066ab994db0a0c16278a50cd6`).
Static commands were:

```sh
sha256sum <exact-JAR>; sha1sum <exact-JAR>; stat -c '%s' <exact-JAR>
python3 build/java-diff-mc-zi0-preflight/inventory.py <exact-JAR> \
  > build/java-diff-mc-zi0-preflight/inventory.json
zipinfo -h <exact-JAR>
```

The raw inventory walks EOCD/CEN/LOC framing itself; Python `zipfile` was not an
input to its results and no extracted catalogue is supplied to EVM production. An
ancillary host `unzip -t` integrity command was run but was not used by the inventory
or prototype and persisted no extracted bytes; it is not EVM inflation evidence.

## Target static inventory (facts, not EVM execution)

| item | measured value |
|---|---:|
| classic EOCD offset / comment / valid ending candidates |30222099 / 0 / 1|
| disk / CD disk / entries-on-disk / total |0 / 0 / 20554 / 20554|
| central-directory offset / bytes |28121303 / 2100796|
| total / maximum raw name bytes |1155312 / 137|
| directory-suffix names / empty / invalid UTF-8 |261 / 0 / 0|
| central extra / local extra / entry-comment bytes |0 / 0 / 0|
| exact duplicate-name sets / entries |0 / 0|
| methods |20554 method-8; 0 other|
| general-purpose flags |20554 exactly `0x0800` (UTF-8)|
| data-descriptor forms |20554 none|
| ZIP64 sentinel/extra, encrypted/strong, patched |all 0|
| multidisk entries / overlapping ranges |0 / 0|

All CEN records frame exactly to the EOCD; CEN order equals strictly increasing LOC
order. Every local name/method/flag agrees with CEN, non-descriptor CRC/sizes agree,
and the last local compressed range ends exactly at central offset `28121303`.
There are no absolute-slash, backslash, or `..`-component names; these are observations,
not proposed path rules. ZI0 keys remain opaque full byte strings.

The earliest named frontier entries are all method 8, flag `0x0800`, no descriptor:

| raw key | LOC / compressed-data offset | compressed / declared plain |
|---|---:|---:|
| `log4j2.xml` |2972204 / 2972244|459 / 1124|
| `net/minecraft/server/MinecraftServer.class` |3026184 / 3026256|15798 / 33457|
| `org/apache/logging/log4j/LogManager.class` |6860135 / 6860206|4282 / 11864|
| `META-INF/log4j-provider.properties` |7060413 / 7060477|520 / 904|

These offsets only size/check the candidate. A future index must rediscover them by
EVM parsing; they must never be embedded as an authoritative target catalogue.

## Actually executed EVM prototype

Ignored source builds a 6519-byte runtime/6564-byte init with pinned
solc `0.8.30+commit.73712a01`, optimizer 200, viaIR, Cancun, metadata off. Source SHA-256
is `26575cac482b05946796aa60b6c712e53560c114b0eea1e9456a92498d485254`;
runtime Keccak is `cd87f5d718297eaeabea224797f041120eb43a8b4e7b90aeb81a580ebc934c29`.
This is disposable measurement code, not a production artifact.

For every case Go generated raw trusted ZIP bytes, ordinarily CREATEd accepted AS0,
appended pages through AS0, sealed them in EVM, obtained AS0's EVM-produced content
commitment, ordinarily CREATEd the prototype, then called it. The prototype pins AS0
runtime Keccak `c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896`
and calls `AS0.read`; it receives no host offsets, names, index, or extracted bytes.
It validates sealed root/code binding, bounded EOCD search, classic CEN framing,
LOC/name/method/flag/size consistency, extras, descriptors and ranges.

All **25** expected outcomes passed. Positive controls cover empty archive, methods
0/8, signed and unsigned classic descriptors, false ZIP signatures in comments,
records crossing an 8KiB AS0 page, a >4096-byte read sequence, 128 entries, and the
full 65557-byte EOCD search window. Negative controls cover wrong code/root/unsealed
AS0, ambiguous valid-looking EOCD in a comment, truncation, bad/empty records,
local-name/signature/range mismatch, duplicate names, reordered CEN, overlap, ZIP64
extra, multidisk, encryption, and unsupported method.

| generated control | EVM scan gas | relevant result |
|---|---:|---|
| empty 22-byte ZIP |37947|0 entries accepted|
| method0+8, 2 entries |292111|98-byte CD accepted|
| 128 entries / 7680-byte CD |24607595|accepted|
| 8KiB-page crossing |14156278|accepted|
| 4096-read sequence |9842828|accepted|
| maximal EOCD window |69109777|accepted under 100M|

Prototype CREATE used `1305210` gas. Accepted AS0 per-fixture controller CREATE was
`611673`, seal `31394`, and append max `1825326`; these transport costs are separate
from scan gas. Final 25-case binary run took 0.193s shell wall / 190ms self report,
25884KiB self max RSS, below the 20min/4GiB watchdog. The final report SHA-256 is
`2a7fd4ae11f5e4470fd2b4ff3cf9558d4e62d3e6ed5c985569c236e062b7d934`.
The view-only prototype does not pretend to measure production SSTORE/trie cost.

## Candidate production contract for parent freeze

Exact proposed API (names may be frozen only after parent replay):

```solidity
constructor(address sealedAS0, bytes32 assertedContentCommitment)
discover()                         // owner-only; EOCD -> staged header
scan(uint32 expectedEntry, uint16 maxEntries) // owner-only, maxEntries 1..64
finish(uint32 expectedCount, bytes32 assertedIndexCommitment) // owner-only
head() view returns(address owner,address store,bytes32 content,uint8 phase,
 uint32 length,uint32 eocd,uint32 cdOffset,uint32 cdSize,uint32 count,
 uint32 nextEntry,uint32 cdCursor,bytes32 rolling)
entry(uint32 index) view returns(bytes rawName,bytes32 packedRecord)
lookup(bytes rawName) view returns(bool found,uint32 index,bytes32 packedRecord)
```

Constructor fixes nonzero `owner=msg.sender`, store address, accepted AS0 code hash,
sealed EVM content commitment and declared length; no rebinding/reset/import/upgrade.
`discover/scan/finish` take value 0 and use expected cursors/count/root as CAS-style
assertions. `entry/lookup` revert until FINAL. A failed batch reverts only that batch;
prior staging cannot be published, skipped, rebound, or used through the API.

State is the binding/header/progress/rolling root, one packed 256-bit record and one
`keccak256(rawName)->index+1` slot per entry. The packed record contains CEN-name
position, LOC/data positions, compressed/plain sizes, stated CRC, raw-name length,
flags, method and descriptor form. On an occupied hash slot EVM rereads both complete
names from AS0: equal bytes are a duplicate rejection; unequal bytes are an explicit
unsupported hash-collision rejection. Lookup likewise compares every supplied byte,
never hash alone. At 20554 target entries this is 41108 record/map slots, a
`1315456`-byte slot-payload lower bound excluding trie/account overhead; production
must measure actual state/RSS and restart durability before freeze.

Let `H=keccak256`, `D0=H("MC-ZI0/index/v1")`, `DE=H("MC-ZI0/entry/v1")`:

```
I0=H(abi.encode(D0,address(this),owner,store,AS0_CODEHASH,content,length,
                eocd,cdOffset,cdSize,count))
Ii+1=H(abi.encode(DE,Ii,uint32(i),H(rawName),uint16(nameLen),flags,method,
                  statedCRC,compressedSize,plainSize,localOffset,dataStart,
                  dataEnd,recordEnd))
```

Only EVM-computed `Icount` becomes public after `finish` checks the assertion, exact
count/CD cursor, and final non-overlap. This index root binds EVM-parsed metadata to
one accepted AS0 instance/root; it is not whole-JAR SHA-256 or plain-content proof.

Proposed finite caps are accepted AS0 32MiB/8KiB pages/4096-byte reads, EOCD tail
65557 bytes, classic single-disk only, 32768 entries, 4MiB CD, raw name 256 bytes,
central/local extra 1024 each, entry comment 1024, methods 0/8, and 64 entries/call.
The target uses 20554 entries, so exactly 322 scan batches at 64 (last 10), plus
constructor/discover/finish. Discovery's measured worst-window 69.11M fits the
unchanged 100M/30s ordinary call. The 24.61M 128-entry view control supplies headroom,
but persistent 64-entry gas/state must be measured rather than inferred; 1B/120s is
boundary testing only. The 20min/4GiB gate and all AS0/VFS/stock limits stay unchanged.

## Exact profile decisions and nonclaims

Accept one unambiguous classic EOCD ending at artifact end, CEN ending at EOCD,
single disk, strictly increasing LOC order, nonoverlapping local record/range ends,
and either empty archive or exact nonempty count/CD framing. Reject ZIP64 records,
locators/sentinels/extra ID 1, multidisk, encryption/masking/patched data, empty names,
malformed extras/comments/headers, duplicate names, hash collisions, reordered CEN,
overlaps, unsupported flags/methods, truncation, trailing records and ambiguity.
Allow only raw flag bits 1--3 and 11 (bits 1--2 only for deflate); target uses bit 11.
Classic bit-3 descriptors may be 12-byte unsigned or 16-byte signature form and must
repeat CEN CRC/sizes; LOC values must be zero. Otherwise LOC CRC/sizes equal CEN.

No slash normalization, `.`/`..` collapse, UTF normalization, directory inheritance,
or VFS lookup semantics apply to opaque ZIP keys. Extra fields and comments are
framed/skipped within caps, never searched as names. Method 0 additionally requires
compressed size equals plain size and yields only a committed stored-byte range.
Method 8 yields only the exact committed **compressed** range. Stated CRC is metadata:
ZI0 computes neither plain CRC nor inflation and cannot report Java resource/class
success. Future EVM inflation must consume exactly `[dataStart,dataEnd)` from the same
AS0 binding and independently validate output bounds and CRC.
