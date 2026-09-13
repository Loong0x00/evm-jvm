# Next measured System.getProperty preflight

Parent EVM-ZI0 resource enumeration advances unchanged original22 to2082J/20I.
Exact next refusal is `CallError(3,3)` in raw PropertiesUtil method11,
`getStringProperty(String)`, PC3: `System.getProperty(String)String`. Caller is
LoaderUtil.isIgnoreTccl via PropertiesUtil overload and current literal is
`log4j.ignoreTCL`; vanilla invocation supplies no override, so correct result is null.
This is after genuine ZI0 absence of log4j2.component.properties, not a fake empty
resource branch.

Modify only the existing guest java/lang/System image: retain private nullable
SecurityManager and native arraycopy; add private static initialized
`java.util.Properties` state and exact public static getProperty(String). It must
validate Java8 null key=>NPE and empty key=>IllegalArgumentException, then perform
real `properties.getProperty(key)`. The table is initially empty because this local
launch profile has no `-D` input channel; do not hard-code key names or fabricate
host/java/os values. No setter/getProperties/clearProperty/security-manager changes.

System now has a genuine clinit constructing Properties, which may legitimately
shift earlier LoaderUtil initialization steps. Preserve all existing bootstrap image
positions/order except replacing System in its pinned slot; append nothing. Preserve
native1..7,64 boots, resource coordinator/ZI0 bridge, corrected incoming-key HashSet,
canonical loader and all prior semantics/reservations.

New engine/address/owner/store/all-nine domains/pins/worlds under existing LOCAL384;
record size/headroom, no >384 absent failure. Accepted320 unchanged. LOCAL1B/30s/
25Mreserve/20min4GiB,24/262144,128frames,CP4096Code65535,heap/VFS1MiB,1MiBCP,
32768BHead fixed.

Generated q1/q7/direct/reopen/canonical: missing/repeated property null, null-key NPE,
empty-key IAE, System clinit identity, getSecurityManager null, arraycopy, independent
Properties; retain positive/missing EVM-index resource+URL, ordered-set asymmetry and
prior controls. Unsupported getProperties/setProperty remain honest; raw System
replacement rejects. Worker no original artifacts. Parent independently source-builds
then NEW original22 q7+q1. Expected later String/API/class blocker explanatory only.
No host property injection, broad Java SE, fake output, failed checkpoint recovery,
core/ABI/Makefile/settings/push/main-body/world/Done. Terra/high, one semantic writer,
fresh absolute TMPDIR and true whole process-tree peak.
