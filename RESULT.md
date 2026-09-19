# Result

Generated-only bounded directly-created Java 8 `ThreadLocal.get` stage completed
from accepted raw37 parent `parent-24250cb9d`.

- Replaced only bootstrap image89 (`java/lang/ThreadLocal`) with final direct
  constructor plus `Object get()` default-null behavior (193 bytes, SHA-256
  `cc0a43a9627fd7f6a1ec1b85711e4cb1ba3d988dab06e3fd5fbe795e175b1289`).
- Raw37/282358, 90-image order, diagnostic127, native13, resource pipeline,
  gas policy and all fixed limits remain pinned. `set`, `remove`, `withInitial`,
  initialValue override, and multithread behavior refuse atomically.
- Exact 90-image root is runtime-derived as `keccak256(abi.encode(DBOOT,h))`.
  A single-sited runtime Object hash helper recovers 332 bytes from the
  393291-byte unshared layout: 392959 / 393216 engine bytes, coordinator 5394.
- Default-null get q1/q7/direct/reopen agrees at 51 Java/2 internal steps,
  epochs 51/8/1, with identical terminal machine and opaque payload roots.
- Corrected focused-plus-retained gate: 111 rows, 390 commands, 4683 canonical
  receipts, 356.741 seconds (cap1200).

No original artifact/JAR/class/resource, provider/factory/world, or Done claim.
Parent alone reruns unchanged original37. Evidence:
`evidence/java-evm/minecraft-entry/thread-local-get-preflight/`.
