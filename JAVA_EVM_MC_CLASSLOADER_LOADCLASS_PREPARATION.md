# Next measured ClassLoader.loadClass preflight

Parent Boolean commits original22 to2278J/24I. Exact next q1 is
`CallError(3,15)` in raw LoaderUtil method3 `loadClass(String)`, PC15:
`ClassLoader.loadClass(String)Class`. The current guest Thread context loader is the
previously pinned nullable default, so JVM linkage must first resolve this member,
then null-receiver NPE is catchable by LoaderUtil and its existing fallback reaches
Class.forName. Do not skip linkage or change Thread defaults now.

Modify existing abstract guest ClassLoader position49:

* exact public instance `loadClass(String)Class` declaring ClassNotFoundException;
* ordinary Java calls one exact private-static-native loaded-class primitive;
* native binding8 only, preserving1..7. Validate exact declaring class/name/
  descriptor/access, one reference argument, Class reference return, initialization,
  stack capacity and canonical state.

Implement genuine **already-present Program class lookup**, no host loader/catalogue:
validate guest String backing, compare dotted binary name against each immutable parsed
Program class name (MUTF-8 decoded slash->dot), require unique match, and return/create
the same canonical Class mirror used by ldc. Refactor mirror-by-target logic rather
than duplicating loader/quota checks. Raw target mirror has canonical VMClassLoader;
bootstrap target mirror has null. Repeated lookup identity must hold and loadClass must
not initialize target. Missing/malformed names reject honestly; do not fabricate null
or append broad classpath/JAR loading. ClassNotFoundException construction and
Class.forName are not implemented until measured.

Original current receiver is null, so expected next measured behavior is a genuine
guest NPE caught by LoaderUtil, followed later by exact Class.forName blocker. That
expectation is explanatory only, not permission to implement forName.

Replace ClassLoader image only; append no images, total66. Preserve other65 bytes/order,
all reservations, System/Boolean/resource/ZI0/HashSet/native1..7 semantics. New engine/
address/owner/store/all-nine domains/pins/worlds. Existing LOCAL384; record headroom,
no >384 absent failure. Accepted320 unchanged. LOCAL1B/30s/25Mreserve/20min4GiB,
24/262144,128frames,CP4096Code65535,heap/VFS1MiB,1MiBCP,32768BHead fixed.

Generated nonnull system loader loads raw nested class by dotted name without running
clinit, repeated mirror identity/getClassLoader canonical, and bootstrap Boolean mirror
null loader; missing name honest refusal. Retain Boolean/System/IAE, true/missing EVM
resource, URL/set/loader/thread/PA/arraycopy controls; q1/q7/direct/reopen/canonical.
Raw ClassLoader replacement and omitted overloads reject. Worker no original artifacts.
Parent independently source-builds then NEW original22 q7+q1. No Thread default change,
Class.forName, host loading, fake output, failed recovery, core/ABI/Makefile/settings/
push/main-body/world/Done. Terra/high, one semantic writer, fresh absolute TMPDIR and
persistent true whole process-tree peak.
