# System.getProperty preflight

**PARENT CORRECTION:** empty-key IAE depended on a raw test-only class absent
from original worlds. Parent appends/reserves the159B dependency as bootstrap65,
rebuilds without raw IAE, and reaches java/lang/Boolean in original22. See
JAVA_EVM_MC_SYSTEM_PROPERTY_PARENT_PREFLIGHT.md.


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

## Generated-only result

The reproducible source build uses Java8 `javac`, solc
`0.8.30+commit.73712a01` with optimizer200/viaIR/Cancun/metadata-off, and an
absolute fresh TMPDIR. It produces engine **347874B** (45342B below LOCAL384),
SHA256 `65084a081c66a9f5b5b395ffb3cdfa5551e8e61dc6d1ce1af6ab503be4787ad2`,
Keccak `b71c447885eb7081ab04b57e7d08e119872e2e7e891c5414e25a70df1fc9cd22`,
and ordinary-CREATE coordinator4146B, Keccak
`07432c3a6616caa2dfc89356fbcdb09b90d60d6642051dce98f284ea7f69e735`.
The new engine anchor is `0x4d432d53595354454d2d50524f50454e47310000`; all
nine engine domains are `MC-SYSTEM-PROPERTY-PREFLIGHT1`. The System image is
704B/SHA256 `6a5720789022cc778afa5c9d7606934d9a5988add0cd8dbc719cb495b1901689`.
A reverse-source assertion proves that, apart from the nine domain literals,
only the pinned System image changed.

Generated q1/q7/direct/reopen property worlds terminate genuine VOID at
419J/11I and epochs419/60/1 respectively, with equal machine root
`0x41017d054bba6f2f75cb84b06b55df0c4eae55ff0019b9d184ffb8803dbb5da5`
and opaque SHA256
`d2ecffc6549d7f110376ed213d38a0c28cc1a818087cecf61edbe4d15d7dc810`.
They cover absent/repeated property lookup, NPE, IAE, clinit, null security,
arraycopy, and an independent Properties table. `getProperties`, `setProperty`,
`clearProperty`, and raw System replacement retain honest refusals. Retained
EVM-ZI0 positive/missing resource, URL, ordered-set, loader/thread/PA,
openStream-refusal controls also pass q1/q7/direct/reopen (3035J/16I,
epochs3035/434/1). Full receipts/checkpoints, generated classes/resources,
artifacts, logs and hashes are archived below; no Go binary or LevelDB appears.

A process-tree monitor over the generated System control gate reports exit0,
22.999s, 59551744B peak RSS (1143 samples); it remains inside the LOCAL20min/
4GiB guard. LOCAL384 and LOCAL1B are authorized; accepted320 and all
accepted/core limits remain unchanged. No original-JAR input, Minecraft/world
execution, host property injection, push, or completion claim is part of this
work. Parent alone must independently source-build and run fresh original22
q7+q1; any next original blocker is not measured here.
