# Catchable immutable-Program ClassNotFoundException

This is a LOCAL384/LOCAL1B preflight evidence package.  It appends only
`java/lang/ReflectiveOperationException` (66) and
`java/lang/ClassNotFoundException` (67), and maps immutable Program lookup
binding 8's missing or malformed dotted name to guest exception kind 13.
Valid lookup keeps canonical mirror/no-init behavior; OOM remains kind 7.

`engine/` and `coordinator/` are reproducible Solidity source with pinned
solc 0.8.30 optimizer-200/viaIR/Cancun/metadata-off builders. `bootstrap/`
contains Java source plus the length-preserving generated-source recipe used
for its minimal owned raw classfiles. `artifacts/` contains generated contract
artifacts and generated fixture classes. `receipts/` contains durable heads,
opaque checkpoints, and full report receipts only--no LevelDB, Go binary,
original JAR, original class, or page payload is archived.

Generated exact present lookup terminates normally with equal q1/q7/direct
machine roots.  Exact CNFE and superclass catches terminate normally for
missing/malformed names; uncaught CNFE terminates lifecycle 3 with kind 13.
This does not load archive classes, implement `Class.forName`, execute original
JAR classes, execute Minecraft main/world logic, or claim Done.
