# Next measured ClassLoader resource-enumeration bridge

Parent corrected LinkedHashSet reaches unchanged original22 at1850J/19I. Exact next
q1 is `CallError(3,74)` for
`java/lang/ClassLoader.getResources(Ljava/lang/String;)Ljava/util/Enumeration;`
in LoaderUtil.findUrlResources, with canonical loader and resource-name String on
stack. No result has been returned. Parent host inventory says current requested
`log4j2.component.properties` is absent from the pinned JAR, but execution must
establish that from genuine EVM ZI0 state, never hard-code/fake empty.

Implement only a bounded one-archive ClassLoader enumeration bridge:

1. Modify guest ClassLoader with exact public instance getResources(String)
   throws IOException. Prefer ordinary Java that calls one narrow private static
   native presence primitive and constructs a guest enumeration.
2. Add genuine guest `java/util/Enumeration<E>`, `java/net/URL`, and a reserved
   VM-owned enumeration helper. Empty and single-entry enumerations must have real
   independent cursor state; exhausted nextElement throws existing NSEE.
3. URL stores immutable archive resource name; exact equals/hashCode/toString needed
   so LoaderUtil duplicate UrlResource values from two identical loader slots
   deduplicate. `openStream` and content decode remain unsupported until measured.
4. Add native binding7 only (preserve1..6). Validate exact declaring class/name/
   descriptor/access/static one-reference-arg/int-return/initialization/stack and
   convert genuine guest String to bounded ASCII resource bytes. Null/malformed/
   non-ASCII/oversize state rejects honestly.
5. Binding7 must perform an actual EVM staticcall to its calling coordinator under
   bounded gas that preserves25M commit reserve. Add coordinator view method guarded
   to the exact engine; it revalidates fixed ZI0 code/finalRoot/owner and invokes
   finalIndex.lookup(rawName). Validate exact ABI return. No host catalogue.

One JAR can yield at most one URL for a unique ZIP name, so false=>empty and
true=>one is genuine for this profile. Positive generated ZIP MUST contain a
non-class resource and prove EVM lookup true, exactly-one Enumeration, URL equality/
hash/toString and duplicate loader-query behavior; absent name proves empty. Also
retain prior collection/asymmetric equals/system loader/thread/PA/System/Properties/
arraycopy controls, q1/q7/direct/reopen/canonical. Coordinator wrong caller/index/
engine controls and raw replacement for all changed/added classes/helpers reject.
`URL.openStream` remains honest unsupported.

Append new images after prior61, replace ClassLoader image in pinned position49,
reserve all new VM names, preserve other60 image bytes/order, native1..6 and all
prior semantics. New engine/address/owner/store/all-nine domains/pins/worlds.
Existing LOCAL384 only; first record runtime/headroom and do not exceed384 absent
actual failure. Accepted320 unchanged. LOCAL1B/30s/25Mreserve/20min4GiB,
24/262144,128frames,CP4096Code65535,heap/VFS1MiB,1MiBCP,32768BHead fixed.

Worker reads no original artifact/classes/worlds. Parent independently source-builds,
replays generated controls, then starts NEW original22 q7 and q1. Failed states are
never reused. Expected later System.getProperty or URL.openStream is explanatory,
not permission to implement either. No broad network URL/protocols, duplicate JARs,
full ClassLoader, fake output, core/ABI/Makefile/settings/push/main-body/world/Done.
DefaultTerra/high, one semantic writer, fresh absolute TMPDIR and one true persistent
whole process-tree peak.
