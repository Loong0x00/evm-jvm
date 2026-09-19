# Result: bounded directly-created `ThreadLocal.get`

- Exact raw37 basis: `parent-24250cb9d` / `classcount37-byte282358-preflight`.
  Only bootstrap slot 88/image 89 changes: final direct `ThreadLocal` with
  public constructor and `Object get()` returning null; 193 bytes, SHA-256
  `cc0a43a9627fd7f6a1ec1b85711e4cb1ba3d988dab06e3fd5fbe795e175b1289`.
- Raw37/282358, all 90 image positions, diagnostic127, native13, resource
  pipeline, gas policy and fixed limits stay pinned. The exact full bootstrap
  commitment is independently reconstructed from all image bytes.
- Runtime-derived root layout recovery keeps `keccak256(abi.encode(DBOOT,h))`
  over all 90 ordered image hashes. A single-sited Object runtime hash helper
  recovers 332 bytes from the 393291-byte unshared layout: 392959 / 393216
  bytes (257 headroom); coordinator remains 5394 bytes.
- Default-null get q1/q7/direct/reopen agrees at 51 Java/2 internal steps and
  epochs 51/8/1. Constructor identity remains 34/2 and 34/5/1.
- `set`, `remove`, `withInitial`, and multithread construction are atomic
  `CallError(3,pc)` refusals. Both `initialValue` subclass/override controls
  are atomic `HierarchyError(3,1)` refusals; no Head or value map exists.
- Corrected generated focused-plus-retained gate: 111 rows, 390 commands,
  4683 canonical receipts, 356.741 seconds (cap1200).

No original artifact/JAR/class/resource, provider/factory/world, or Done claim.
Parent alone reruns unchanged original37.
