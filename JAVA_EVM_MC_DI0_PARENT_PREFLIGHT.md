# DI0 parent preflight: Java8 compatibility, header counts and real size frontier

Status: **NOT FROZEN / NOT ACCEPTED**. Workerdb1bea2b1 integrated28ffe5ec4. Accepted
ZI00936b7ebd/AS064ea6b62f/VFS72aa13f15 unchanged. No official-JAR inflation or Java/
Minecraft execution, EULA/listener/world/Done. Parent oracles execute only generated
fixtures and are never runtime inflater/CRC/lookup authority.

## Independent baseline

Parent reconstructed a fresh disposable workspace from committed source/compiler/
driver and independently obtained the exact artifact SHA
35d2c876ccc15e4caa4c398f05b5ead2b715e0b4a49e7728c90060957e09baa8.
Original21 cases and q1/q128/OOG report fields reproduced identically (excluding
wall/RSS):22.575s external/44314624B sampled groupRSS, exit0/no20min4GiB limit.
This proves the measured in-memory subset, not disk/output-page publication.
The5000-gas test uses a wrapper snapshot rollback and is not a demonstrated
post-output-write direct-EVM rollback test; stronger tests are needed later.

Evidence: `evidence/java-evm/di0/parent-db1bea2b1/`. All source, generated streams/
ZIP fixtures, Java8 oracle and reports are tracked/reproducible, not /tmp-only.

## Reproduced EVM/Java8 differences

Parent built10 short raw streams with original compressed bytes preserved inside
ZIP fixtures, and ran the EVM prototype plus Go flate and OpenJDK8u504
Inflater(true), ZipFile and ZipInputStream. No server input was inflated.

| generated shape | original EVM | Java8 oracle |
|---|---|---|
|HLIT257/HDIST1, singleton EOB/empty distance|verified empty output|all3 APIs succeed|
|HLIT286/HDIST30, same empty output|verified empty output|all3 succeed|
|HLIT287 or288, HDIST1|INCORRECTLY accepted|all3 reject too many length/distance symbols|
|HLIT257, HDIST31 or32, unused distances|accepted|all3 reject too many length/distance symbols|
|fixed final unused high bit nonzero|error23|all3 succeed|
|fixed final byte followed by a full trailing byte|error23|Inflater/ZipFile succeed; Inflater reports1 remaining; ZipInputStream rejects compressed-size mismatch|
|stored-block discarded alignment bits nonzero|verified output|all3 succeed|

HLIT>286 exceeds RFC literal-count range. HDIST31/32 rejection is explicitly our
Java8-compatible profile choice; RFC's header count wording permits1..32, so do not
mislabel every such unused header as universally invalid RFC data. Terminal unused
bits are not a justified zero-padding requirement. Exact consumption of full indexed
compressed bytes is a separate conservative policy: it matches the measured
ZipInputStream size check but is stricter than raw Inflater/ZipFile. Keep that
difference visible; never change the authoritative Java8 result to match EVM.

Parent corrected ONLY a disposable source copy:
- Reject HLIT>286 or HDIST>30 with preflight error27 (count profile).
- Ignore unused high bits of the final byte, while retaining exact whole-byte range
  consumption and length/CRC checks.
- Tighten the Go oracle: only a nonzero expected code with the exact DI0 selector can
  count as semantic rejection. No accidental positive-case OOG/error0 acceptance,
  and no unexpectedly valid negative fixture counted as success.

Corrected sourceSHA6a11700d7a99de500311d058658530f0fb81705e190e0886a371b8a1f349bead;
runtime9697B SHAde60dcd5948327366d430346cf7f6c7556c352e1653b75bb1dfd92d5c8a44eb0;
init11766B SHA390222ba5036b4486b4ab735749f13c1b9dfd31b704aca4d5b257f0ad0a01e87;
artifactSHA896d541b0ce8c6d8b1200950371256aa5eafd5b2ee0d3a9faddf5c6b190522c0.
Corrected21-case replay passes22.622s/44290048B sampledRSS. Nonzero-padding is now an
actual successful output (policy correction), not a renamed rejection. Corrected10
compatibility cases pass0.106s/19316736B; four count cases reject27, padding succeeds,
trailing full byte still rejects23. q1/q128 exact equality remains tested.

## 64KiB output cap is not sufficient for this workload

Parent rehashed the official raw JAR and inspected CEN SIZES ONLY, without inflating
or extracting entries:20554 total entries,19007 .class entries. Total declared
plaintext65995526B, classes64620541B. Exactly3 entries exceed65536B, including2 classes:

| entry | compressed | declared plain |
|---|---:|---:|
|assets/minecraft/lang/en_us.lang|35477|158794|
|org/apache/logging/log4j/spi/AbstractLogger.class|17425|90309|
|it/unimi/dsi/fastutil/io/BinIO.class|18748|73635|

The largest class is in the logging family of the early startup frontier; this is
not a proven dynamic reachability trace, but it rules out calling64KiB a justified
whole-JAR entry cap. No entries exceed256KiB by this static metadata inventory.
`inventory-sizes.py` and `static-sizes.json` retain reproducible size evidence;
this table is NOT supplied to EVM lookup/inflation as authority.

**Explicit next-preflight proposal: DI0-only256KiB plaintext/entry**, rather than the
unaccepted prototype's64KiB. This is NOT a frozen/accepted runtime cap increase and
does NOT change AS0/ZI0/VFS/Java heap/checkpoint budgets. It needs actual EVM/disk
measurements. Lazy resource consumption remains necessary; do not allocate the
whole ~66MB declared uncompressed JAR or silently ignore larger entries.

## Authorized next bounded output/persistence preflight

Up to TWO disjoint workers. The Sol/high EVM/output/persistence worker owns ONLY
JAVA_EVM_MC_DI0_PERSISTENCE_PREFLIGHT.md (aim<=220lines),
`evidence/java-evm/di0/persistence-preflight/` and ignored
`build/java-diff-mc-di0-persistence-preflight/`. A separate Terra/high pure Go/Java
fixture-oracle worker owns ONLY `evidence/java-evm/di0/tree-oracles/` and ignored
`build/java-diff-mc-di0-tree-oracles/`; it may READ/replay the pinned parent corrected
artifact but must NOT write Solidity. It expands generated legal/malformed tree,
repeat-cross-boundary and padding comparisons with Java8 as primary oracle; preserve
mismatches, exact EVM selectors, output/remaining counts and small reproducible inputs.
No provider/settings changes if Terra is unavailable; report that blocker honestly.
There is only ONE Solidity writer. No production/accepted/core/peer/
settings changes, Fast/priority, spawning, push, official-JAR upload/inflation,
Java server/EULA/listener or fabricated outcome. Key source/results in tracked
owned evidence, never solely temporary files. Parent is not concurrently writing
Solidity. Start from parent corrected source, preserve original failure evidence.

Required measurements before production freeze:
1. Actual EVM decoding from accepted FINAL ZI0/AS0 binding, caller name/index/root
   assertions only; generated fixture oracles may run on host, never decoding/tree/
   CRC/offset/byte-map authority. Cover stored/fixed/dynamic and all parent cases.
2. Explicit DI0-only256KiB output cap: generated90309/158794/262144 exact/+1 and empty
   cases; history boundary32768 and overwritten-history data that CHANGES across
   wraps (not only identical repeated B bytes). Recommend total/per-case resource
   bounds from observed results, not the four earliest small resources.
3. Issue immutable STOP||plaintext pages by actual ordinary EVM CREATE, preferably
  8192B/at most32 output pages with bounded publication units. Names/ranges/output
   bytes and page code/hash/root must remain EVM-derived. Final-only page/read after
   CRC+length and complete page publication; empty output zero pages/nonzero root.
   No caller-fed decoded page/code installer. Staging is not confidential.
4. Every memory mutation commits/reloads; every successful disk step/publication
   syncs trie+code and durable manifest independently, with real fresh-process
   mid-decode/verified/mid-publication/FINAL reopen. Record gas/output history/state/
   code/disk/RSS/time. No batching or speculative trace recovery.
5. Define bounded units for header, Huffman token, repeats/matches, CRC/output and
   publication. Atomic whole dynamic header may remain ONLY with a demonstrated
   finite worst-case ordinary-gas bound; otherwise split/persist header progress.
   Do not force unnecessary state machinery merely for general Java SE completeness.
   Quantums1/larger must preserve output/root/state for identical binding.
6. Owner/cursor/binding/stale-step/phase refusal; exact error selectors and strong
   positive/negative oracles; actual post-write direct OOG rollback before host
   restoration, then retry. Publication failure/CRC/length failure cannot yield
   final output. Prior-file corrupted VIEW probes are not live authority.
7. More Java8 legal tree corners, malformed count/repeat/oversubscription/incomplete
   trees, trailing bytes and padding policy; retain honest differences. Worst
   structural dynamic header and expansion gas must be measured, not inferred from
   highly compressible happy-path fixtures.

Keep AS0/ZI0 input32MiB,8192-page/4096 reads and all accepted profiles unchanged;
start controller ordinaryCREATE<=24576B/runtime and<=49152B completeinit,
100M30s ordinary/1B120s explicit boundary, whole gate20min4GiB. A measured violation
is a blocker/proposal, not permission to raise caps. Bound code init args and output
pages separately. Exact ABI/roots/errors/state and production disk hardening freeze
remain parent's next decision after independently replaying this evidence.
