# MC-ZI0 preparation — EVM ZIP directory indexing over accepted AS0

Status: bounded preflight authorization, NOT implementation freeze/acceptance.
AS0 accepted64ea6b62f is an immutable byte-store component; VFS0a72aa13f15 remains
latest accepted JVM/filesystem. No MC/EULA/listener/Done or new GitHub push.

Next dependency is ZIP/JAR structure, not another unrelated library or fake logger.
ZI0 means directory/index/entry-range identification only. DEFLATE, CRC of inflated
content, Java ZipFile/ClassLoader, lazy class state and main launch remain separate.
Do not call a metadata pointer a decoded class or a verified uncompressed resource.

Use EVM reads against an actual sealed AS0ArtifactStore. Bind the accepted AS0
controller code hash/address and its EVM-produced sealed content commitment; a
caller-supplied catalogue, offset/name/hash list or extracted payload is not authority.
AS0's page/content roots are NOT official whole-JAR SHA256 verification. Host may
hash raw input for transport/static evidence, never resolve production resource names.

One Sol/high worker (no Fast/priority) owns ONLY JAVA_EVM_MC_ZI0_PREFLIGHT.md
(aim<=200lines) and ignored build/java-diff-mc-zi0-preflight/. No production/peer/
accepted-artifact/core/settings writes, spawning/push, Minecraft/JAR execution,
EULA files, sockets/listeners, or copyrighted server bytes in public fixtures.

Required preparation:
1. Recheck official1.12.2 raw JAR hash before STATIC ZIP metadata inventory. Count
   entries/directory bytes/name and extra lengths/methods/flags, ZIP64/encryption,
   duplicate names/local offsets and relevant descriptor forms. Compare with the
   earliest Log4j resources already identified. Static host ZIP analysis is TEST/
   planning evidence, not data supplied to the EVM parser.
2. Design and genuinely execute a SMALL standalone EVM prototype consuming sealed
   AS0 bytes: bounded EOCD discovery, classic single-disk central-directory framing,
   local-header/name/method/size consistency and bounded compressed-entry ranges.
   Use generated trusted ZIP fixtures only for execution. No host-preparsed indexes.
   Cross-AS0-page records and signatures inside comments must have real controls.
3. Measure gas/code/state size and resumable scan units if directory work cannot fit
   one call. Recommend finite limits from actual target metadata, not guesses. Keep
   accepted32MiB/8KiB AS0 pages,4096B reads,100M/30s ordinary,1B/120s boundary and
   20min/4GiB watchdog unchanged. Do not dump whole JAR into one EVM memory buffer.
4. Specify exact unsupported/profile cases (e.g. ZIP64/multidisk/encryption), duplicate
   name/order/overlap decisions, data-descriptor treatment, empty archives, corrupt
   records/truncation and index publication/ownership/AS0-binding guarantees. Avoid
   importing VFS filesystem traversal rules into raw ZIP name keys. Name equality
   needs full bytes, not hashes alone.
5. State what method0/stored versus method8/deflated results mean. It is acceptable
   for ZI0 to expose verified metadata/COMPRESSED byte ranges without inflation,
   but no plain-content CRC or Java resource success may be fabricated. Future EVM
   inflation must operate on exactly the committed compressed bytes.

Read current AS0/VFS plans/reviews and JAVA_EVM_MC_NEXT_ENTRY_FRONTIER.md. The pinned
server JAR is at /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar,
30222121B/SHA256fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e.
Do not execute it or distribute it. Use local format documentation or official ZIP
specification lookup when uncertain; report facts separately from design proposals.
Commit only the note. Parent independently replays then freezes ZI0's exact ABI,
wire/state/limits, proof boundary and disjoint implementation tasks.
