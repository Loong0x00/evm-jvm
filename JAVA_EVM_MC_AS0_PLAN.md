# MC-AS0 frozen implementation contract

Status: **implementation authorized, NOT accepted**. Latest accepted JVM profile is
VFS0a72aa13f15; AS0 is a separate immutable EVM byte-store prerequisite, not a new
JVM or filesystem implementation. No ZIP/inflate/ClassLoader/main/MC/EULA/listener/
Done claim. No server artifact redistribution or automatic GitHub push.

## Parent verification and correction of preflight

Preflight87f5850e9 integratedfc7d3ef56. Parent rebuilt the original source in its own
ignored directory and reran all4096 pages/32MiB through actual EVM CREATE/Call.
Input transport SHA256feb39150a2d007512e7e638b4278f5f007f5cb2db4348a1ecd4de8972e81975e,
ordered/content roots and final trie root matched the preflight exactly. Parent
watchdog0.739s/100311040B observed groupRSS; new-process reopened code/trie and read
correct bytes. Log /tmp/mc-as0-parent-full.{log,json}; data/code-deposit gas dominates,
so cumulative7.232B gas is not7.232B computational instructions or one-call usage.

Parent found a missed boundary: after all declared bytes were uploaded but before
seal, append(cursor,empty,correct-empty-Pi) succeeded, created a STOP-only page and
changed chain/count/nonce without advancing bytes. One-byte artifact became two
pages at116074gas. This is NOT an accepted artifact shape. Preserve
/tmp/mc-as0-parent-empty-page-before.log and the original ignored prototype.

Frozen corrections: reject remaining==0 and raw.length==0 before CREATE; seal must
also require pageCount==ceil(declaredLength/8192). Require nonzero constructor owner.
Use STORAGE-backed owner/declaredLength, assigned ONLY by constructor, rather than
Solidity immutable substitutions: the deployed controller code hash is then a fixed
pinned artifact for every owner/length, simplifying durable code identity checks.
This does not expose any owner/length setter or make artifact bytes mutable.

Parent applied these to a separate ignored prototype and reran the full control:
2962B measurement-controller runtime SHA27c2ebaa23bc11b35d9f263672cca698353e14ce80cd0fb88397735749bbdab7,
ordinary CREATE637899gas, append1765718..1825418gas, seal31415gas,
new-process cross-page read24857gas. Cumulative append7232650628gas; full0.747s/
100462592B observed RSS. Root remained the same because addresses/owner/bytes/order
and domains stayed the same. The measurement SHA/comparator functions remain in that
prototype but MUST be excluded from production; its artifact is not the final pin.

## Production ownership and exact EVM API

`AS0ArtifactStore` under `jvmevm/artifactstore/as0/runtime/`. One controller per
artifact/session. Constructor is executed by ordinary unmodified runtime.Create;
child data pages are created ONLY by the controller's EVM CREATE, never Go SetCode.
No CREATE/opcode/precompile/gas/accounting changes or special trusted child address.
Controller runtime<=24576B, init<=49152B; pages STOP||raw<=8193B. This establishes
only this component's bounded CREATE path, not whole-JVM signed deployment.

Freeze the following ABI (visibility public/external as appropriate):

```
constructor(uint32 length)
append(uint32 expectedCursor,bytes raw,bytes32 expectedPageCommitment)
seal(uint32 expectedCursor,bytes32 expectedChain)
read(uint32 offset,uint32 length) view returns(bytes)
pageCount() view returns(uint256)
page(uint256 index) view returns(address,bytes32,bytes32)
owner() view returns(address)
declaredLength(),cursor() view returns(uint32)
isSealed() view returns(bool)
chainCommitment(),contentCommitment() view returns(bytes32)
PAGE_SIZE(),MAX_PAGES(),MAX_LENGTH() view returns(uint32)
```

Constants8192/4096/33554432 respectively. Exactly AS0Error(uint256 code), plus
PageIssued(uint32 indexed index,address indexed page,uint32 length,bytes32 codeHash,
bytes32 pageCommitment,bytes32 chainCommitment) and
Sealed(uint32 length,uint32 pages,bytes32 contentCommitment).
No sha256Whole/comparator/fallback/receive/overwrite/upgrade/abort/import API.
No generic execution/native/host callbacks. Nonpayable calls, value0.

Constructor requires length1..33554432 and nonzero owner=msg.sender. State contains
owner/declaredLength/cursor/isSealed/chain/content and ordered page addresses/code
hashes/page commitments. Owner/length cannot be written after construction.
Append is owner-only before sealing, expectedCursor equals stored cursor, exact next
page length=min(8192,declaredLength-cursor), never zero, at most4096 total pages.
Construct actual child code in EVM with STOP prefix; check its EXTCODEHASH against
H(STOP||raw). A wrong caller Pi assertion is checked AFTER CREATE, exercising real
outer-call child/nonce/storage/log rollback. Only computed Pi enters the chain.
Seal is owner-only, once, only with exact full byte cursor, exact page count and
expectedChain==computed chain. No append after full length, even before seal.

Reads are public, only via read after seal, length<=4096 and offset+length<=declared
length using nonoverflowing arithmetic. Offset==end/length0 succeeds empty;
offset>end/length0 fails. Cross-page bytes are assembled by EVM EXTCODECOPY from
issued pages, excluding STOP, checking actual code hashes on every touched page.
page(index) is bounded metadata available before/after seal; sealing is completeness,
NOT confidentiality—EVM page code is public even before read() is enabled.

Errors:1length;2owner;3sealed;4append cursor;5page length/end/count;6CREATE failure;
7issued child code mismatch;8caller Pi assertion;9incomplete seal/cursor/page count;
10seal chain assertion;11page index;12unsealed read;13read bounds;14read code hash.
Preserve that precedence; constructor length precedes owner. Reverts produce no
success events/root/page publication. Do not change top-level EVM CREATE nonce/gas
semantics to simulate transactions; transport publication rollback is separate.

## Exact commitments (retain preflight domains)

H=keccak256, all encode=Solidity abi.encode, not packed. D(s)=H(ASCII(s)).

```
C0=H(encode(D("MC-AS0/chain/v1"),controller,owner,uint32(length),uint32(8192)))
Pi=H(encode(D("MC-AS0/page/v1"),controller,uint32(i),uint32(raw.length),H(raw)))
Hi=EXTCODEHASH(page)=H(STOP||raw)
Ci=H(encode(D("MC-AS0/ordered/v1"),Cprev,uint32(i),uint32(raw.length),page,Hi,Pi))
root=H(encode(D("MC-AS0/content/v1"),controller,owner,uint32(length),
              uint32(pageCount),uint32(8192),Cfinal))
```

The content commitment is instance-bound (includes controller/owner/issued addresses),
not a location-independent file digest. Later JVM mounting must bind controller code
identity/address AND sealed content commitment. Host Pi/chain values are checked
transport assertions, not accepted authority or a host catalogue. Host hashing of
opaque bytes is allowed for transport checks; EVM computes its actual commitments.
Whole-JAR official SHA256 is NOT proven by these roots. A32MiB one-shot SHA256 call
exceeded1B; do not substitute per-page SHA or host compression as whole-EVM proof.
ZIP/resource/class claims remain future EVM interpretation of committed raw bytes.

## Opaque Go transport and durable state

Package `jvmevm/artifactstore/as0`, embedded combined artifacts only, exact ABI/code
pin checks and no source-tree fallback. Expose Runtime/InitCode/ABI,
NewMemory(owner,length), Open(directory,owner,length), Session Append/Seal/Read/Page/
Head/Close. Append and Seal take the exact expected cursor/commitment arguments and
finite gas. Head returns EVM owner/length/cursor/sealed/pageCount/chain/content values;
reads/pages are EVM ABI results, never host byte-map/resource implementations.
Creation gas/address/code hash must be available to tests/reports, not silently
counted as zero. Reporting must distinguish operation gas from additional view calls.

Disk format1 marker `JVMEVM-MC-AS0-DISK-STORE-1\n`, separate directory from all previous
profiles. Persist EVM StateDB/trie/code, not host copies replacing page authority.
Manifest must bind format/context/owner/controller/declaredLength/pinned runtime hash/
committed state root. Validate metadata before opening LevelDB; verify restored
controller code hash and EVM getters. Reopen must never redeploy or install pages.
Use fixed Cancun dev context as existing transports, nonzero owner/value0. Requested
root aliases may resolve, internal symlinks refused, metadata reads regular/bounded.

Each successful Append/Seal in a disk session must publish its durable state, not
silently batch every256 calls as the preflight did. Commit/sync trie and code first,
then owned manifest-temp fsync, atomic rename and directory fsync. Prepublication
failure reloads old root; ambiguous postrename failure poisons session until reopen.
Failed publication returns diagnostic gas only: no page/root/success/log result.
EVM errors may retain their revert bytes for diagnosis. Preserve owned unpublished
temps; don't delete unrelated files. Read/Page/Head use copied/read-only state.
For an interrupted INITIAL store with no published manifest, fail closed and preserve
files for diagnosis; do not invent a root or wipe/recreate it. This is explicitly not
an existing committed store or a power-loss simulation.

## Verification and finite limits

Pinned solc0.8.30+commit.73712a01, optimizer200,viaIR,Cancun,metadataoff.100M/30s
ordinary calls;1B/120s explicit boundary only;20min/4GiB each full gate. No JVM unit
counter or1MiB blob is fabricated for this non-JVM byte-store component. Accepted
VFS0a/IOE0/stock/core/limits stay unchanged. Full32MiB synthetic control (4096append
calls+seal), partial8193B, read edges/cross-page/exact4096/+1, exact hash roots,
expected page code, wrong owner/cursor/length/commitment, duplicate/full-before-seal
empty append, post-CREATE failure/OOG rollback/retry same child/nonce/code/logs are
required. Clearly separate summed chain gas from max per-call gas.

Require actual new-process reopen mid-upload and after seal, resumed upload with no
recreation, byte-identical reads, copied-view nonmutation, code/state mismatch
refusal, disk failure injection/old-root retry/ambiguous poison, internal links/read
bounds and embedded relocatable executable. Full32MiB DISK per-append durability is
also measured under the gate; if it cannot fit, report the exact limitation instead
of silently batching publication or dropping the test.

Parent independently checks at least16 groups: artifact/ABI, constructor identity,
page code, commitments, ordering, lengths/end, seal, reads, metadata bounds, rollback,
32MiB limits, mid-upload process reopen, sealed reopen/code pins, publication failures,
namespace/filesystem transport hardening, final reproducibility/legacy preservation.
Worker completion or a stub compile is not acceptance. No Minecraft bytes in public
fixtures; only generated trusted opaque data/tiny trusted ZIP bytes, never executed.

## Disjoint writers

Runtime worker: ONLY `jvmevm/artifactstore/as0/runtime/**`, sole Solidity writer.
Harness worker: ONLY `jvmevm/artifactstore/as0/**` EXCLUDING runtime/** and parent_test.go
(parent reserved); can own ignored build/java-diff-mc-as0-harness/ for integration.
Parent: plan/guides/Make/gitignore/parent_test.go/review/integration/acceptance.
Use at most TWO Sol/high workers, no Fast/priority, spawning/push/settings/core/peer
writes. Read-only peer artifacts/byte-identical ignored test overlays are allowed,
not fake/placeholder assets. Keep all exact failures and actual final-artifact reruns.
