# Class.forName(String) LOCAL preflight

Bounded generated-only LOCAL384 result from `e90909eae`; evidence is at
`evidence/java-evm/minecraft-entry/class-for-name-preflight/`.

Bootstrap39 `java/lang/Class` alone is replaced (770B Java8 image). It retains the
private name/definingLoader fields, private constructor, getName and getClassLoader,
and adds ordinary `public static forName(String):Class`, which calls exact
private-static-native binding9 `forName0(String):Class`. Bindings1..8, the other67
images, 68 total images, and 14 exception kinds remain pinned.

Binding9 consumes missing/malformed arguments and guest-raises CNFE kind13. It returns
a canonical mirror only for an already initialized target (`initializationState==2`);
a present uninitialized target raises `ClassForNameInitializationError(target,pc)`
without allocating a mirror or pretending initialization occurred. There is no
three-argument overload, host/classpath lookup, lazy archive loading, or fake init.

Generated direct/reopen receipts cover CNFE exact/super/malformed, initialized raw and
Boolean mirrors/loaders, uninitialized refusal, uncaught lifecycle3/kind13, raw Class
replacement and overload refusal. q1/q7/direct terminal machine roots agree for the
relevant missing/present/uncaught cases. Engine is359004B (<384KiB by34212B), with the
new engine/address/owner and all nine commitment domains; accepted320 is unchanged.
LOCAL1B/30s/25M reserve, 24/262144,128 frames, CP4096/Code65535, heap/VFS/CP1MiB and
Head32768 remain fixed.

This remains a narrow preflight, not original-JAR or Minecraft execution, a world,
main-body progress, or Done. Further names/lazy loading/dynamic initialization remain
explanatory only.
