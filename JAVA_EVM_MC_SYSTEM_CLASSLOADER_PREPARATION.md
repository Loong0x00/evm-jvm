# Next measured member: ClassLoader.getSystemClassLoader

Parent defining-loader profile commits original22 to1799J/16I. Exact next failure
is CallError(3,31) at LoaderUtil.findUrlResources PC31:
`ClassLoader.getSystemClassLoader()Ljava/lang/ClassLoader;`.

Implement this one VM-provided static getter, returning the same canonical
VMClassLoader object already stored in raw Class mirrors. Prefer an exact native
declaration in owned ClassLoader plus a narrowly validated EVM native binding:
zero arguments, exact reference return descriptor, normal active-use class
initialization, stack-capacity checks, and canonical loader heap scan. Missing,
duplicate or malformed loader state must reject; never synthesize a second object.
No host callbacks/side table.

Do not implement getResources/loadClass, URL/Enumeration/Collection/LinkedHashSet,
ClassLoader installation, AccessController or an empty resource result. The original
third loader-array slot should receive the same nonnull canonical identity. Next
resource API/class failure remains honest.

Preserve defining-loader Class fields/mirror validation and quota repair, both
ClassLoader/VMClassLoader reservation, prior51 other images and all Thread/
PrivilegedAction/System/Properties/arraycopy semantics. Only ClassLoader image may
change for this method. New engine/address/all nine domains/store/pins; new worlds.

The repaired engine is327266B with414B headroom. First compile under320KiB and
preserve an actual cap failure if the correct native path exceeds it. The user has
explicitly chosen LOCAL execution over mainnet constraints; after a measured
failure, continue automatically as separately labeled **LOCAL384KiB**. Accepted
320KiB remains unchanged; no validation removal/minification trick.

Authorized LOCAL1B/30s/25Mreserve/20min4GiB and24/262144,128frames,CP4096/
Code65535/heap/VFS/1MiBCP/32768BHead otherwise unchanged. Oversized engine is
LOCAL initial-state only, all controllers/resources ordinary CREATE.

Generated raw mirror loader == repeated system getter, bootstrap mirrors null,
normal class initialization, malformed/unsupported getResources refusal, previous
controls and q1/q7/direct/reopen/canonical equality. Include reserve/canonical
loader state negatives where public paths permit; no private Session. Worker no
original artifacts. Parent independently rebuilds then NEW original22 q7+q1.
No failed trace recovery, original substitution, accepted/core/ABI/Makefile/
settings/push/Done. DefaultTerra/high, one semantic writer, absolute fresh TMPDIR,
true whole-group peak without resets/session escape.
