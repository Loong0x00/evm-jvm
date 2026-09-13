# System.getProperty preflight

This unaccepted LOCAL384 preflight follows the genuine EVM-ZI0 resource lookup
frontier. It replaces only fixed bootstrap slot 44 (`java/lang/System`) from
`parent-fdc55a341`, preserving all 63 other bytes/order and the 64-image root.

The guest System retains private nullable `SecurityManager`,
`getSecurityManager()`, and native `arraycopy`. It now has private initialized
`java.util.Properties` state and public `getProperty(String)`: `key.length()`
creates ordinary null dereference/NPE, zero length throws default-constructed
`IllegalArgumentException`, and all other keys call real guest
`Properties.getProperty`. State begins empty: this LOCAL profile has no `-D` or
host property source. No property names are hard-coded and no set/clear/
getProperties/security APIs are added.

The generated empty-key branch has a fixture-local Java 8
`IllegalArgumentException` implementation because that class is not one of the
fixed 64 bootstrap images. It is ordinary raw input solely for branch coverage,
not an appended/bootstrap image. The original path does not take this branch.

All output will be archived under
`evidence/java-evm/minecraft-entry/system-property-preflight/`; disposable
fresh runs use ignored `build/java-diff-mc-system-property-*`. LOCAL384 and
LOCAL1B are authorized; accepted320 and all accepted/core limits remain
unchanged. No original-JAR input, Minecraft/world execution, host property
injection, push, or completion claim is part of this work.
