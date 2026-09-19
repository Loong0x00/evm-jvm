# Correction to `615afb767`: preserve the exact raw37 ordered root

`615afb767` correctly rejected the full literal `_bootstrapRoot`, but recovered
size by routing slot 0 through a private Object-hash helper. This correction
keeps the required runtime derivation in the exact raw37 ordered form instead:

```solidity
bytes32[] memory h = new bytes32[](90);
h[0] = keccak256(_bootstrapObject());
// exact ordered h[1] through h[89]
return keccak256(abi.encode(DBOOT, h));
```

The full literal root remains ineligible. Every non-isolated image hash is
again derived in its ordered root assignment; the pre-existing isolated
`DBOOT_ENUMSET`, `DBOOT_ITERABLE`, and `DBOOT_MATH` commitments remain pinned.
`verify_source.py` compares the complete 90 assignments with raw37, rejects a
full precomputed root return, recompiles the sole ThreadLocal image, checks all
other bootstrap image bytes, and recomputes the ordered commitment with the
pinned local Keccak implementation.

The direct runtime-root source measures 393291 bytes, 75 bytes above the
393216-byte cap. The recovery is outside `_bootstrapRoot`: the private
post-allocation `_validateInitialMainRoot` helper never reads its `Program`
argument, so its signature and one call pass only `RuntimeState`. This is a
semantics-preserving unused-argument elimination. The rebuilt runtime is
392834 bytes, a 457-byte recovery and 382-byte headroom (SHA-256
`7f4cd30f0cfeed3ba64b1d0be7663669bbd15e9cb388081052fe7643589f2a8b`).

This correction uses only the existing generated stage sources, accepted
raw37 parent evidence, pinned local Java 8/solc tooling, and generated
fixtures. It does not open an original artifact or use the network. The rebuilt
pins record engine Keccak-256
`3f2fbc5b00b4abe283482cb88ff86e095957143be3208daac796fabb540ad679`.
The rerun passes 111 focused/retained rows, 390 commands, and 4683 canonical
receipts in 359.116 seconds (cap 1200); its q1/q7/direct/reopen ThreadLocal
get result remains 51 Java and 2 internal steps with identical terminal
machine and opaque payload roots.
