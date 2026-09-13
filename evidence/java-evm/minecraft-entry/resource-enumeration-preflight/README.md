# Resource enumeration preflight evidence

Unaccepted work on the bounded EVM-only resource presence bridge. The engine has
binding7 for the exact private static `ClassLoader.resourceExists(String):boolean`,
converts a bounded ASCII guest `String`, and staticcalls the calling coordinator.
The coordinator permits only its fixed engine and revalidates ZI0 code/phase/root/
owner before forwarding the original bytes to `lookup(bytes)`. `ClassLoader` was
replaced at the existing bootstrap position and `Enumeration`, `URL`, and
`VMResourceEnumeration` append after image 61.

The generated archive contains `probe/resource.txt`, a real non-class ZIP entry.
The first direct EVM probe did **not** reach a resource result: it was rejected by
`LC0StateError(7,0)` during startup. The refusal, source, pinned compiled artifacts,
and generated fixture are preserved here. It is not an accepted result and no
original archive, original class, Minecraft world, or host lookup was used.
