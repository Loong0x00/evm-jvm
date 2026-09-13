# Next measured MC blocker: MarkerManager's platform map

Original ten-class unchanged-JAR execution now commits4 Java steps. Next EVM
failure is missing java/util/concurrent/ConcurrentHashMap, site4104/PC0 of
MarkerManager.<clinit>,36779158gas. JAR MarkerManager was genuinely added/read;
no fake logger or guest-class substitution. Its static TEST disassembly shows:
constructor()V at clinitPC4, stored as ConcurrentMap; getMarker uses get(Object)
and putIfAbsent(Object,Object), clear/exists use clear/containsKey. The next JAR
Marker/MarkerManager$Log4jMarker bindings are for parent EVM selection, NOT platform
stubs. This preparation authorizes only the needed map substrate.

NEW isolated derivative of4cf97854e, not accepted core/profile promotion:
- Real owned bootstrap Java interfaces java/util/Map and ConcurrentMap and minimal
  AbstractMap/ConcurrentHashMap class hierarchy as needed for correct assignability.
  Prefer genuine guest Java bytecodes over additional native/interpreter branches.
  No fake org/apache/logging class, marker registry on host, logger no-op or Done.
- No-arg constructor and get/putIfAbsent/containsKey/clear required. Fundamental
  put/size/isEmpty may be included with explicit measured tests, not an implied
  full Map implementation. Correct prior-value returns, no overwrite on existing
  putIfAbsent, reference-valued entries, equal-but-distinct String keys, absent
  lookup null and CHM null-key/null-value NPE behavior. Ordinary bounded guest
  arrays/fields, sensible growth within existing quotas; never silently drop data.
- A linear/equality-scanned representation is acceptable: algorithm need not copy
  JDK internals. Generic key equality must actually dispatch Java equals, not assume
  all keys are String. Minimal real Object.equals default identity is allowed if
  required; do not add broad Object/hashCode/reflection unless needed. Compare
  generated behavior against Java8 TEST oracle, including custom equal keys.
- Current VM has one guest thread. Specify this profile boundary; no claim of new
  Java threads/concurrent-map locking/linearizability under an unimplemented guest
  scheduler. Host calls remain ordinary EVM/CAS serialized, no state shared on host.
- No extra map-specific immutable checkpoint restrictions on mutable fields:
  constructors and resizing can legitimately checkpoint between field writes.
  Existing heap/reference/constructor validation remains. Prove q1/q7/direct
  constructor/mutation/growth/clear/alias/state continuity and Java exceptions.
- Preserve existing bootstrap indexes. While appending new bootstraps, handle the
  supplied-Runnable branch correctly: previousClass candidate's fixed +34 index
  can overrun a shortened tail. Derive actual appended Class slot in Program rather
  than globally weakening duplicate/binding checks; no gratuitous codec/cache rewrite.
- Keep16/262144COPY/CP4096/Code65535/heapVFSframes/CP1MiB,100M30s,320KiB runtime,
  whole20min4GiB. If a real bound is reached, record it and stop, no automatic raise.
  Source-only pinned compiler, new explicit pins/identity, ordinary controller
  CREATE and exact oversized LOCAL engine initial state, no standard-chain claim.

Worker only generated fixtures, no original JAR/class handling. Parent independently
rebuilds and resumes new worlds with original bindings. User goal is MC running,
not complete JVM, collections framework or generic Session/fault matrix.
