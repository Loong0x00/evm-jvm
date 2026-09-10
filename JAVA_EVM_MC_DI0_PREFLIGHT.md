# MC-DI0 preflight — bounded EVM inflation over accepted ZI0

Status: **PREFLIGHT MEASUREMENT ONLY; no DI0 freeze or acceptance**. Baseline is
`cfa093d94`; accepted ZI0 is `0936b7ebd`, accepted AS0 is `64ea6b62f`, and VFS0a
remains the latest JVM/filesystem profile. Nothing here inflated the official JAR,
loaded/executed Java, ran Minecraft, accepted an EULA, opened a listener, or reached
Done. All executed archives and plaintext are generated fixtures.

## Authority and framing read before implementation

Authoritative inputs were RFC 1951 sections 3.1.1/3.2.3-3.2.7 and PKWARE APPNOTE
6.3.10 sections 4.4.4-4.4.9. URLs and downloaded SHA256 values are durable in
`evidence/java-evm/di0/preflight/authoritative-sources.txt`.

- ZIP method 0 is stored bytes, not a DEFLATE stream. Method 8 contains **raw
  DEFLATE**, with neither zlib nor gzip wrapper/checksum.
- Elements enter bytes at increasing bit positions; non-Huffman values are LSB
  first, while canonical Huffman codes are emitted MSB first. BFINAL is one bit,
  BTYPE 00/01/10 means stored/fixed/dynamic, and 11 is an error.
- Stored blocks discard bits to the next byte boundary, then require little-endian
  LEN and one's-complement NLEN. Compressed blocks require literal/length EOB 256.
  Fixed 286/287 and distance 30/31 participate in code construction but may not occur.
- Dynamic order is `16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15`.
  Repeat 16 requires a predecessor and repeats 3..6; 17 repeats zero 3..10; 18
  repeats zero 11..138. Repeats may cross the literal/distance boundary.
- Length is 3..258 and backward distance 1..32768. A source may cross blocks and
  may overlap its destination; it may not precede output start. One used distance
  code has length one; RFC1951 also permits zero distance codes for all-literal data.
- ZIP CRC-32 starts `0xffffffff`, uses reflected polynomial `0xedb88320`, and is
  complemented at the end. The CEN CRC and declared plaintext length remain
  assertions until recomputed from EVM output.

Prototype tree policy rejects oversubscription; requires a complete code-length tree;
accepts complete literal/distance trees, a one-symbol length-1 degenerate tree, and
an empty distance tree only. EOB must be present. This is a measured bounded subset,
not yet a Java8/general-DEFLATE compatibility claim. The prototype additionally
requires the final EOB to consume exactly the indexed compressed byte range and all
unused high bits in its last byte to be zero. It rejects trailing full bytes and
nonzero terminal padding. RFC ignores alignment bits for stored blocks and does not
make this final zero-padding restriction a ZIP compatibility promise; Java8 policy
must be tested/frozen separately rather than guessed.

## Actually executed authority path

`DI0Inflate.sol` checks ZI0 runtime Keccak
`0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77`,
requires ZI0 phase FINAL and the caller-asserted final root, and calls EVM ZI0
`lookup(rawName)`. It unpacks dataStart/compressed/plain/CRC/method itself, obtains
and code-pins the bound AS0, and reads only that indexed compressed range through
AS0 `read` calls of at most 4096 bytes. The host supplies no offset, tree, decoded
map, output bytes, native inflater, or CRC result.

The replay built one 53,638-byte synthetic ZIP, uploaded it via ordinary accepted
AS0 CREATE and seven EVM-created pages, sealed it, then created/discovered/scanned/
finished accepted ZI0 before ordinary DI CREATE/calls. Every successful mutation was
committed and reloaded in the in-memory trie. Go `compress/flate` and `hash/crc32`
checked only trusted generated fixtures; EVM remained execution authority.
Fixture ZIP SHA256 is
`e68bc2cfae4e9b0c238f901c6b876a3c72e44d661b7927c6da8652ddef22fd3a`.

Proven valid EVM paths:

- method0 904B;
- method8 stored 9000B whose indexed range/read windows cross 4096-byte positions
  and 8192-byte AS0 page boundaries;
- fixed Huffman 33,457B from 295B, using distance-1 overlapping copies;
- Go-generated dynamic Huffman 11,864B from 89B;
- handcrafted valid dynamic trees using repeats 16/17/18, empty output, singleton
  distance, and a separate literal-only zero-distance tree;
- nonfinal stored block followed by final fixed block, with separate EOBs;
- exact distance 32768 after 32768 output bytes, then a real back-reference.

Real EVM rejections cover bad CRC; declared length too short and too long; reserved
BTYPE, literal 286, and distance 30; distance before output; trailing byte; nonzero
terminal padding; over- and under-subscribed code-length trees; repeat-16 without a
predecessor; and declared plaintext 65,537 over the constructor cap. Reads reject
before FINAL. A direct 5,000-gas OOG consumed its allowance, returned no bytes, left work/output/root
unchanged, and a normal-gas retry succeeded; no trace/OOG state was harvested.

## Resumption and measurements

One work action is: one method0/stored chunk of at most 32 output bytes; one block
header (dynamic header currently includes at most 286+32 code lengths); one Huffman
symbol plus bounded extra bits; or at most 32 bytes of a pending match. Thus no unit
means “whole block”, long matches cannot evade the counter, and malformed dynamic
headers are finitely bounded. Persisted state includes absolute input byte+bit,
block mode/BFINAL/fixed flag, 288+32 dynamic lengths, 32KiB-addressable output
history, pending length/distance, output count, running CRC, output rolling root,
and monotonic work CAS. The whole completed output is stored only under a finite
64KiB prototype cap; this is not an archive allocation or VFS/Java quota increase.

Two independently reconstructed identical AS0+ZI0 states proved semantic and exact
state-root equality across call grouping:

| case | q1 calls/work | q128 calls/work | summed step gas q1/q128 | max call q128 |
|---|---:|---:|---:|---:|
| fixed overlap 33457B |1300/1300|11/1300|231760842 / 214874733|21503434|
| dynamic 11864B |498/498|4/498|90397744 / 83367176|27980039|

The fixed pair shares final root `c650cfcb...3e19a4` and state root
`a8bce703...e86b7c2`; dynamic shares final `c7fd56df...5c4a64` and state
`59b3f784...703f8f`. Full roots and bindings are in the report. The distance-32768
case used 32,772 actions/257 q128 calls, summed 19,697,151,706 gas, max 77,854,624;
this sum is not one-call gas or an instruction count. Other maxima were 17,162,795
(dynamic), 16,049,843 (cross-page stored), and 10,702,351 (fixed overlap), all under
the unchanged ordinary 100M call allowance. DI CREATE was about 2.24M gas.

Pinned solc 0.8.30, optimizer200, viaIR, Cancun, metadata-off produced init 11,768B
and runtime 9,699B, below the starting 49,152/24,576-byte gates. Runtime SHA256 is
`5413f94287c0f73cca32b602223489483c795c57b10c016e6fc38930427325a5`;
Keccak is `9d089315...76b3cc`; source SHA256 is `67125224...476666`.
Final replay was 23.357s with process max RSS 46,224KiB and a 1200s watchdog.
No durable LevelDB/output-page publication was measured; in-memory commit/reload is
not disk durability. No 1B call was needed and AS0/ZI0 caps were unchanged.

## Candidate production contract for a later freeze

Tentative phases: BOUND/STAGING/VERIFIED/PUBLISHING/FINAL. Constructor
`(address finalZI0,bytes32 assertedIndexRoot,bytes rawName,uint32 outputLimit)` must
pin ZI0/AS0 code, FINAL root/content/address, perform EVM lookup/unpack, and reject
`outputLimit != declaredPlain` or over-cap before decoding. Proposed mutators are
owner-only and CAS-bound:

```
step(bytes32 expectedBinding,uint32 expectedWork,uint16 units)
publish(uint32 expectedPage,uint16 units)
finish(uint32 expectedCount,uint32 expectedCRC,bytes32 expectedRolling)
```

Proposed views are `head()`, `page(uint32)`, and final-only
`read(uint32 offset,uint32 length<=4096)`. `head` must expose binding, phase, indexed
record, byte+bit cursor, tree/header progress, window position, pending match,
count/CRC/rolling/work, page cursor and final root. Errors should preserve prototype
classes 1 owner; 2/3 dependency/root; 4 lookup; 5 record/method/cap; 6 phase; 7 CAS;
8 units; 9 unpublished; 10 view bounds; 11 input; 12 stored-range; 13 BTYPE;
14 LEN; 15/16 reserved symbols; 17 distance; 18 repeats; 19 EOB; 20 over-tree;
21 under/tree shape; 22 code decode; 23 exact-end/padding; 24 length; 25 CRC;
26 output limit. Exact precedence remains for freeze review.

Recommended *pre-freeze test caps*, not accepted workload limits: 64KiB one entry,
4096-byte AS0 reads, 32KiB history, 32-byte copy action, 128 actions/call, packed
320-byte Huffman lengths, 8192-byte final pages (at most eight), and 4096-byte final
reads. Decode staging may use bounded EVM storage, but after length+CRC verification
only EVM ordinary CREATE should issue `STOP||plaintext` pages owned/recorded by the
controller. No caller-provided code/bytes installer is allowed. Page code hash and
ordered output commitment enter FINAL root. Empty verified output publishes zero
pages and a nonzero domain-separated FINAL root. Failed CREATE/publication must
rollback and expose gas/revert data only; public raw staging is not confidential.

Suggested roots, all `abi.encode` with `H=keccak256`:

```
binding=H(H("MC-DI0/binding/v1"),this,owner,ZI0,ZI0_CODE,indexRoot,
          AS0,AS0_CODE,content,index,H(rawName),packed,outputLimit)
stepRoot=H(H("MC-DI0/output/v1"),prior,uint32(offset),uint8(byte))
pageRoot=H(H("MC-DI0/page/v1"),prior,uint32(page),address,codeHash,
          uint32(length),H(STOP||plaintext))
finalRoot=H(H("MC-DI0/final/v1"),binding,plainSize,computedCRC,stepRoot,pageRoot)
```

## Blockers and non-claims

Before freeze: split/persist partially decoded dynamic-header tokens (the prototype
atomically parses a bounded whole header); independently test all legal tree-shape
corners and Java8 ZIP/Inflater behavior; decide terminal padding compatibility;
measure worst dynamic malformed/header and expansion gas; inventory the official
CEN **sizes only** to justify an output cap beyond the four early 904/1124/11864/
33457B entries; implement ordinary-CREATE immutable output pages, exact rollback,
per-call disk publication/new-process reopen, corruption recovery and stale-owner
probes. Measure disk bytes and publication latency. The 64KiB cap is therefore a
proposal, not permission to omit larger workload entries or enlarge VFS/Java heap.

Evidence and exact reproduction commands are under
`evidence/java-evm/di0/preflight/`. No official bytes or extracted runtime catalogue
are present. This proves only the generated subset above, not general DEFLATE, DI0
acceptance, ClassLoader/inflate integration, Java main, or Minecraft readiness.
