# Next measured member: Class.getClassLoader with real defining identity

Parent Thread profile commits original22 to1773J/16I. Exact next failure is
CallError(3,16) at original ThreadContextClassLoaderGetter.run:
`LoaderUtil.class.getClassLoader()Ljava/lang/ClassLoader;`.

A null-for-everything stub would make original resource search falsely empty and
is forbidden. Implement the exact Class member with VM-maintained defining-loader
identity:

* extend owned Class guest image with private ClassLoader field and ordinary
  getter; retain name/getName and private constructor;
* raw input/JAR class mirrors receive one canonical VM-owned defining-loader
  reference; mirrors for VM bootstrap classes return null, matching bootstrap
  loading semantics;
* preserve identity: repeated mirrors/raw classes use the same loader object;
* use a minimal reserved concrete VM loader subtype only if needed to avoid
  representing an instance of abstract ClassLoader. VM may create this canonical
  loader during its own class/mirror boot state (analogous to Class mirrors and
  root String[]), but must track it in ordinary guest heap/checkpoints, enforce
  quotas and validate it on restore. Do not run or fake arbitrary guest constructors.
* derive raw class count immutably from the supplied package rather than host
  class names/catalogues. No host callbacks or decoded-page injection.

Do **not** implement ClassLoader.getSystemClassLoader/getResources/loadClass,
URL/Enumeration/Collection, AccessController, reflection or empty-resource
fallback. Unsupported paths remain honest. This stage establishes identity and
the one getter only; original nonnull branch should later expose genuine
getResources requirements.

Existing Class bootstrap index/order may change only its own byte image; all other
50 images remain exact. If a private field changes mirror layout, update canonical
mirror creation/restoration/validation and generated alias/tamper checks, not a
host side table. New engine/address/all nine domains/store/pins and NEW worlds.
No old-code CP reuse.

Start with existing320KiB engine cap and preserve the exact over-cap artifact/failure
if this correct implementation exceeds the remaining1628B. Because the user has
explicitly prioritized LOCAL execution and authorized relaxing non-mainnet limits,
a subsequent separately labeled LOCAL384KiB COPY is permitted **only after** that
measured320KiB failure; accepted/production caps remain unchanged. Do not minify
away validation or silently change the cap.

LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,128frames,CP4096Code65535heap/VFS/
1MiBCP/32768BHead otherwise unchanged. Exact oversized engine remains LOCAL initial
state, not standard deployment; controllers/resources ordinary CREATE.

Generated raw-vs-bootstrap mirrors, repeated defining-loader identity, null bootstrap
loader, Class name preservation and all prior Thread/ClassLoader/PrivilegedAction/
System/Properties/arraycopy controls. q1/q7/direct/reopen, real terminal sentinels,
canonical ABI/events/CP/read ranges/opaque equivalence, corrupt loader/mirror restore
negatives and unsupported loader method refusal. Runtime worker generated-only;
parent independently rebuilds and starts NEW original22 q7+q1. No failed-trace
state, original substitution, accepted/core/ABI/Makefile/settings/push/Done.
DefaultTerra/high, one semantic writer, absolute fresh TMPDIR/no group escape.
