# Parent-found Math.asin image commitment mismatch — corrected generated candidate

The original candidate `41a4cbe35` was **not parent-accepted**. Its 304-byte Math+asin image hashed to `109b0210...`, but materialized `DBOOT_MATH` still used the old sin-only digest `e354be...`. Thus its claimed P2 ordered root `e4e36043...` differed from its actual Solidity-materialized root `e8d2682b...`. The original generated gate is preserved at `evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/results/generated-gate-v1/` and remains a **NON-ACCEPTANCE**; it has not been promoted.

## Correction and generated-only verification

Changed only the Math materialized `DBOOT_MATH` digest in Solidity. Strengthened `tools/verify_source.py` to check every `DBOOT_* = hex"..."` digest against the exact image selected by `_bootstrapRoot()`, evaluate the materialized source root (not just image bodies), require the pinned root, and normalize the one allowed Math-constant change back to the previous image for baseline diff. All seven materialized hex leaves pass. The other 96 images, bounded integer asin20/sin19 behavior, float packing/sparse format, authenticated boundaries, and raw71 limits are unchanged.

Fresh generated-only build and q1/q7/direct/reopen gate passed in 569.177 seconds with 4,314 canonical receipts. Engine runtime size is 387,706 bytes (cap 393,216). Both image-derived and Solidity-materialized P2 root equal `e4e36043b03626d5766b849f9504f6520fafbd462fc19238a0e9a580f480ef42`. Q120 test-only model covers 17,066 rows (max 1 ULP; 472 one-ULP differences; zero selected float mismatches). Durable canonical v2 evidence, including per-file hashes and receipts, is in `evidence/java-evm/minecraft-entry/math-asin-bounded-preparation/results/generated-gate-v2/`; its manifest explicitly identifies v1 as invalid-root non-acceptance.

## Scope and remaining parent work

This corrects the worker candidate only. Parent must independently rebuild and audit the compiled `_bootstrapRoot()` in a fresh domain, then run the unchanged original under the separately authorized LOCAL4.2B ceiling. No original Minecraft JAR/classes/resources/world was opened or run here. No EULA, world, Minecraft `Done`, or readiness claim is made.
