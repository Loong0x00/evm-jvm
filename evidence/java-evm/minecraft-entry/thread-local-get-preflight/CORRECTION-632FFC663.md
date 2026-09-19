# Correction to `632ffc663`: retain runtime-derived bootstrap root

`632ffc663` is retained as the immediate historical parent but is not an
acceptable integration artifact. Its `_bootstrapRoot()` returned the full
precomputed commitment
`1aa769a912931967ca44cec129ff505741409aecaee7536a85a586213deb4a7b`.
Although that value matched the 90 image bytes, it removed the required runtime
derivation from `DBOOT` and the ordered image hashes.

This correction restores the accepted raw37 form:

```solidity
bytes32[] memory h = new bytes32[](90);
// ordered h[0]..h[89] exact image hashes
return keccak256(abi.encode(DBOOT, h));
```

All non-isolated slots derive `keccak256` from their exact bootstrap bytes at
runtime. Slot 0 uses `_objectImageHash()`, which itself returns
`keccak256(_bootstrapObject())` at runtime; it is a single-sited literal layout
recovery, not a precomputed image/root commitment. The pre-existing isolated
`DBOOT_ENUMSET`, `DBOOT_ITERABLE`, and `DBOOT_MATH` image commitments remain
unchanged. `verify_source.py` asserts the full ordered assignment sequence,
rejects a full precomputed root return, recompiles the ThreadLocal image,
compares all other image literals to raw37, and independently recomputes the
root with local pinned Keccak.

The unshared fully dynamic layout measured 393291 bytes, 75 bytes over the
393216-byte cap. The Object-hash helper recovers 332 bytes without changing
package roots, image bytes/order, checks, bindings, or limits. The corrected
engine is 392959 bytes (257 headroom), SHA-256
`94bd54ce277258129466e80252f7599b0fdd6666ca086385f5ba06b881e97993`,
Keccak-256 `e615effd0d7ab46e1657cd8657ad39387ed36e23895ec54e1610d787b58027b5`.
The coordinator remains 5394 bytes.

Reproduction used only the generated fixture corpus:

- source/build verification with pinned local solc and Java 8;
- 111 focused/retained rows, 390 commands, 4683 canonical receipts;
- q1/q7/direct/reopen agreement, including `ThreadLocal.get()` default-null;
- 356.741 seconds under the fixed 1200-second gate.

No original artifact, network input, review, provider/factory, world, or Done
path was opened or claimed. The prior invalid run remains available through
Git commit `632ffc663`; this correction records why it must not be integrated.
