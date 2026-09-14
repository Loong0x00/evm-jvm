# Class.forName(String) LOCAL preflight

This bounded LOCAL384 preflight replaces bootstrap39 `java/lang/Class` only and adds
private-static-native binding9, `forName0(String): Class`.  It preserves bindings1..8,
all other 67 bootstrap images, 14 exception kinds, and the accepted320 profile.

A missing or malformed dotted name must consume the argument and raise catchable guest
`ClassNotFoundException` kind13.  A present result is legal only for a target already in
initialization state2; otherwise the engine rejects `ClassForNameInitializationError`.
No overload, archive loading, host lookup or fake initialization is introduced.

Evidence and reproducible source/artifacts are under
`evidence/java-evm/minecraft-entry/class-for-name-preflight/`.  This is not Minecraft
execution, a main-body claim, or Done.
