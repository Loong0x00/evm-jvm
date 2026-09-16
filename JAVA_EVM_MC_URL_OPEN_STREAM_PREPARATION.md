# Java-on-EVM Minecraft bounded immutable `URL.openStream()` preparation

Accepted `parent-f7e2ad683` runs unchanged original32 to12773J/42I and1829 canonical receipts, then q7/q1 atomically stop in `ProviderUtil.loadProvider` PC1 on genuine `java/net/URL.openStream()Ljava/io/InputStream;` (`CallError(3,1)`). The measured indexed resource is `META-INF/log4j-provider.properties`,904 uncompressed bytes, SHA-256 `9ac82b18bbb602d06a4b9c93cfef1a64d1d0170e52ab81a7d959fbe83c983319`.

## Scope

1. Replace only existing bootstrap `java/net/URL` with ordinary Java8 guest `openStream()` that opens its immutable resource name through the accepted guest File/FileInputStream/VFS path. Preserve existing URL constructor/equals/hashCode/toString.
2. Extend Program/coordinator/driver packaging with at most one explicitly selected immutable ZIP resource, max4096 uncompressed bytes/name256. Resolve and inflate it only through genuine EVM AS0/ZI0/DI0, commit decoder/name/root/size into the package root, and seed the exact decoded bytes read-only into initial VFS. No host ZIP parsing/decompression/content injection/catalogue and no resource bytes embedded in engine/bootstrap.
3. Keep raw classes32/262144,86 bootstraps, global natives13, diagnostic118 and all other limits/toolchain/outlined tail; engine runtime<=393216. Resume uses the checkpointed VFS only.
4. Generated gates use generated ZIP resources and prove enumeration->URL->openStream exact bytes/EOF/close, direct/q1/q7/reopen equivalence, absent resource, read-only preservation, resource count/4096/4097 boundaries, root/address tamper refusals, and all retained Object.getClass/cap32/lock/TreeMap/String/EnumSet/queue/OOM/canonical receipt gates.
5. Parent alone selects the measured genuine resource from the unchanged original JAR and resumes original32. No Properties.load, provider, factory, world or Done claim until reached.
