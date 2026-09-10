# MC-DI0 output-page and persistence preflight

Status: **PREFLIGHT EVIDENCE ONLY — NOT FROZEN / NOT ACCEPTED** at
`094c51dbc`. Accepted ZI0 `0936b7ebd`, AS0 `64ea6b62f`, and VFS0a
`72aa13f15` are unchanged. No official JAR bytes were uploaded or inflated; no
ClassLoader, Java/Minecraft execution, EULA, listener, world, or Done marker exists.

## Starting point and scope

The disposable source starts from the parent's corrected DI0 source SHA256
`6a11700d...f349bead`: HLIT<=286/HDIST<=30 rejects with DI0 error 27,
terminal unused high bits are ignored, and the entire ZI0-indexed compressed byte
range must still be consumed. The Java8 oracle remains exactly the parent result:
raw Inflater/ZipFile permit a trailing byte while ZipInputStream rejects its size;
DI0 deliberately retains the stricter full-range policy. This run does not retarget
or rewrite that oracle.

The only new cap tested is an explicit **unaccepted DI0-only 262144-byte plaintext
per entry**. Static CEN sizing already retained in
`evidence/java-evm/di0/parent-db1bea2b1/static-sizes.json` motivates it:
AbstractLogger 90309B, BinIO 73635B, en_us 158794B, and no declared entry above
256KiB. It grants no AS0/ZI0/VFS/Java heap/checkpoint quota increase.

## Measured prototype authority and policy

Constructor input is only `(FINAL ZI0 address, asserted ZI0 root, raw name)`.
The EVM checks accepted ZI0 code Keccak `0c22eca7...ad5a77`, FINAL root, performs
ZI0 lookup, decodes its packed record, checks accepted AS0 code
`c8cec283...0f896`, and reads only the resulting compressed range with AS0.read.
No host offset, Huffman tree, decoded-byte map, page code, CRC, or zlib result is
supplied. Caller roots/names are assertions and queries, not catalogues.

Method 0 is raw stored ZIP data with compressed size equal to plain size. Method 8
is raw RFC1951 DEFLATE, not zlib/gzip framing: LSB-packed bits, stored/fixed/dynamic
blocks, canonical Huffman decoding, EOB/BFINAL, 32KiB distances and overlapping
copies. Reserved blocks/symbols, bad LEN/NLEN, bad repeats, over/incomplete trees,
missing EOB, bad distance, output overrun, length and CRC reject. Empty distance
alphabet is allowed when unused; a one-symbol length-1 tree is the only incomplete
literal/distance exception. Stored alignment bits and terminal unused bits may be
nonzero. A whole trailing byte rejects error 23.

Actual persisted decode state is byte+bit input cursor, block/final/mode, fixed flag,
288+32 code lengths, pending length/distance, work CAS, output count/CRC/rolling
root, and plaintext staging words. A repeat unit copies at most 32 bytes; a step call
accepts 1..128 units. This measurement implementation has **no separate 32KiB ring**:
history reads the staged output, at most 8192 32-byte storage words at the cap.
It never allocates declared plaintext as one EVM memory buffer. That full staging
shape is evidence, not a frozen production layout.

The atomic dynamic-header action has finite bounded arrays (286+30 symbols). A legal
max-count/all-nonzero generated header measured 10,945,625 gas, below ordinary 100M;
there is no measured reason to split it in this profile. The highest observed valid
single step was 87,731,815 gas for distance 32768, also below 100M.

## Output ownership, states and roots

Phases are 1 DECODING, 2 VERIFIED, 3 PUBLISHING, 4 FINAL. CRC and declared length
must both pass before phase 2 and before any page CREATE. `publish` issues exactly
one 8192-byte-or-smaller page per call using controller-owned ordinary EVM CREATE;
runtime code is exactly `STOP || plaintext`. It verifies EXTCODEHASH and commits
ordered address/code/page roots. At most 32 pages exist. `page` and `read` reject
until FINAL; reads use checked EXTCODEHASH+EXTCODECOPY, not staging. Empty output
uses zero pages and a nonzero final root. Staging is public EVM state, not secret.

With H=keccak256 and ABI encoding (not packed), the exact measured roots are:

```
B  = H(D("MC-DI0/binding/preflight/v1"), this, owner, ZI0, ZI0_CODE,
       ziRoot, AS0, AS0_CODE, content, entryIndex, H(name), packed, uint32(262144))
O0 = H(D("MC-DI0/output/preflight/v1"), B)
Oi = H(D("MC-DI0/byte/preflight/v1"), Oprev, uint32(outputIndex), uint8(byte))
P0 = H(D("MC-DI0/publication/preflight/v2"), B, uint32(length), uint32(crc),
       Ofinal, uint32(8192))
PCi= H(D("MC-DI0/page/preflight/v2"), B, uint8(i), uint32(pageLen), H(raw))
Pi = H(D("MC-DI0/published/preflight/v2"), Pprev, uint8(i), uint32(pageLen),
       pageAddress, H(STOP||raw), PCi)
F  = H(D("MC-DI0/final/preflight/v2"), B, uint32(length), uint32(crc),
       Ofinal, uint8(pageCount), Pfinal)
```

The disposable ABI is pinned in `artifact-summary.json`: constructor plus 33
functions, `DI0Error(uint256)`, no events/fallback/receive. Mutation surface is
`step(uint32 expectedWork,uint16 units)` and
`publish(uint8 expectedPage,bytes32 expectedRolling,uint8 units)`; final views are
`read(uint32,uint32)` and `page(uint8)`. The diagnostic getters are listed there.
This exact measured surface is a freeze candidate only; parent must still decide
which diagnostics survive production.

Errors preserve 1 owner, 2 ZI code, 3 ZI phase/root, 4 lookup, 5 record/method/cap,
6 phase, 7 work CAS, 8 step units, 9 unpublished view, 10 read bounds, 11 input,
12 method0 range, 13 reserved block, 14 stored length, 15 literal symbol,
16 distance symbol, 17 distance/range, 18 repeat, 19 EOB, 20 oversubscribed/length,
21 incomplete tree, 22 decode, 23 exact compressed range, 24 output length, 25 CRC,
26 output cap, 27 Java8 count profile, 28 publication CAS, 29 publication unit/range,
30 child CREATE, 31 child code, 32 page bound. Negative gates require selector
`DI0Error(uint256)` and the exact positive code; OOG/error0 never counts.

## Generated-fixture results

All 37 EVM cases passed: the corrected original 21 (with old 65537 cap case now a
positive current-cap expectation), all 10 parent compatibility shapes, and six new
header/history/size cases. Trusted Go raw-flate/CRC checks are fixture oracles only.
Stored/fixed/dynamic, method0, cross-4096 input reads, 8192 output boundaries,
distance-1 overlap, max distance 32768, and a different-byte 32768-byte history
wrap across stored/fixed blocks are exercised. Exact 90309/158794/262144 succeed;
262145 rejects in the constructor with exact code 5.

| generated case | calls (step/page) | max step | step sum | pages | page sum/max |
|---|---:|---:|---:|---:|---:|
| history-wrap-different 33768B |9/5|43,978,510|356,151,197|5|30,912,437 / 7,467,230|
| size-90309 |28/12|24,958,629|670,666,068|12|82,463,170 / 7,467,230|
| size-158794 |49/20|34,250,747|1,076,664,933|20|144,845,245 / 7,467,230|
| size-262144 |80/32|25,154,934|1,951,197,139|32|238,976,458 / 7,492,356|

Sums span calls and are not one-call gas. Every call stayed below ordinary 100M;
1B boundary gas was unnecessary. Fixed overlap q1/q128 used 1300/11 steps and
dynamic used 498/4; each pair has identical EVM output, rolling/final roots, page
addresses/code, work and final trie state for the same binding.

A direct 900,000-gas EVM call (no host snapshot/restore) completed the first
output-writing unit then OOGed later in the batch; EVM frame rollback was committed
and reloaded, leaving work/output unchanged, and retry cost 544,639 gas. A late
7.4M page attempt failed exact CREATE code 30, leaked no child/page/root, and retry
issued the same ordinary CREATE child. CRC failure 25 remains phase 1 with zero
pages/final root; publish/page reject 6/9. Owner, work/publication CAS, units, phase,
and page bounds all returned their exact selectors/codes.

## Real durable replay and resources

The 90309B case ran through a LevelDB/trie store. Every successful EVM mutation
committed and reloaded StateDB; disk additionally SyncKeyValue'd trie+code, fsync'd
a unique manifest, renamed it, and fsync'd the directory. There were 60 independent
durable publications: 18 accepted AS0/ZI0 setup mutations, DI0 CREATE, 29 decode
steps (including the initial header), and 12 page publications. No batching occurred.

Four distinct child processes reopened consecutively at mid-decode, VERIFIED,
mid-publication (one page), and FINAL. Root/sequence chains were 20->48->49->60;
FINAL reopened with 12 checked pages and 90309 exact bytes. Disk was 1,401,921B.
The whole final gate passed in 35.811s with 107,298,816B sampled peak process-group
RSS; no 20min/4GiB watchdog limit fired. Prototype runtime is 12,885B, init 15,094B,
and max complete init for a 256-byte name 15,478B; ordinary CREATE max 2,878,621 gas.
Thus the 24,576/49,152-byte start caps pass without a proposal to raise them.

Accepted AS0 32MiB/4096 pages/4096 reads, ZI0 limits, 100M/30s ordinary,
1B/120s boundary, and all older limits remain unchanged. The generated ZIP is only
92,890B; this run does not re-prove accepted AS0/ZI0 capacity gates.

## What remains before any freeze

This proves a generated bounded subset and persistence feasibility, not general ZIP/
DEFLATE, production DI0, Java loading, or workload reachability. Parent still must
freeze the ABI/diagnostic getters, root domains, errors, storage layout, and whether
full-output staging or a 32KiB ring is preferred. Production transport still needs
embedded artifact pins, strict manifest/namespace/metadata and nested-link checks,
concurrency serialization, pre/post-publication failure injection, ambiguous-rename
poison/reopen behavior, and independent parent replay. The disposable database is
ignored and reproducible; source, report, hashes, commands, and all key evidence are
Git-tracked under `evidence/java-evm/di0/persistence-preflight/`.
