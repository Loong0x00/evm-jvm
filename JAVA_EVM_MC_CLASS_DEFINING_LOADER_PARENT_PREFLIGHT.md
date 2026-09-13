# Parent Class defining-loader review

**In progress; worker result is not acceptance.** Worker bfa06755f/102911980
integrated locally. Parent evidence/recipes:
`evidence/java-evm/minecraft-entry/parent-102911980/`.

Worker candidate fits the old320KiB cap by22B, but did not run its required
dynamic negatives or a whole-group RSS monitor. Parent source review found a
real quota hole in first raw-mirror creation: if the class-name String is already
interned and no canonical loader exists, code creates loader+mirror but only
checks space for one object/handle. Parent repair computes reserveObjects=2 for
that case before any allocation. `_internStringUnits` already reserves loader+
mirror correctly on String misses; the fix covers pool hits.

The appended VMClassLoader was also not included in caller replacement guards.
Parent extends the existing ClassLoader reservation to both ClassLoader and
VMClassLoader. It restores unrelated `_classNameUnits` formatting changed by the
worker. No loader method/resource result is added.

`rebuild.py` independently compiles Class/ClassLoader/VMClassLoader images, rebuilds
and matches the exact worker320 candidate, then first applies the repaired source
to the existing320KiB builder. If that measured build fails, it preserves the
failure and recompiles the same source under the separately labelled user-authorized
LOCAL384KiB initial-state cap. Accepted320KiB remains unchanged. New domain
`MC-CLASS-DEFINING-LOADER-PARENT1`, addresses/store and code pins prevent reuse.

Generated parent fixture combines three raw mirrors sharing one nonnull loader,
bootstrap mirror null loaders, non-initializing literals, Thread/PrivilegedAction/
System/Properties/arraycopy controls and a Java8 host oracle. It explicitly tries
caller VMClassLoader replacement and unsupported getSystemClassLoader. q1/q7/direct,
reopen and canonical receipts are required before a NEW original22 q7+q1 world.
No failed-state authority, fake empty resources, original payload archive,
accepted/core/ABI/Makefile/push/main-body/Done claim.
