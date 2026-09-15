# StringBuilder formal size recovery result

## Status

**Not accepted.** A semantics-preserving source-layout repair cleared the deployed-code cap, but the one substantive generated gate stopped at its StringBuilder OOM control. No retry was run.

## Repair

`f3672a818` moves the already-existing post-VFS bootstrap assignment tail from `_prepare` into a private helper and gives image85 one helper materialization site. It does not alter an image payload, slot, limit, binding, class count, or guest bytecode semantics. `_bootstrapRoot` still computes `h[84]` as `keccak256(_bootstrapStringBuilder())` and computes the full bootstrap root at runtime; no full root was precomputed.

The strict parent-89928ece8 source verifier passed, including all 84 prior images/order, image85 provenance, raw30/262144, frames128, checkpoint/head caps, native/exception counts, and the runtime-derived commitments.

The one allowed full product build used solc `0.8.30`, optimizer runs `200`, viaIR, Cancun, and metadata-off. It measured a 386100-byte engine runtime: 9219 bytes below the failed 395319-byte candidate and 7116 bytes below the fixed 393216-byte cap. This exceeds the requested 2104-byte recovery.

`e71a98afe` corrects two gate-only path references discovered before any EVM gate work. They do not affect Solidity, generated artifacts, or runtime behavior.

## Gate outcome

After the runtime fit, one substantive generated-only gate ran. Its chained non-null StringBuilder q1/q7/direct/reopen controls, bounded-null q1/q7/direct/reopen controls, and uninitialized control completed. The next `stringbuilder-oom` start returned `LC0StateError(1,0)` from the fixed 1MiB checkpoint path; the driver then correctly refused to resume its unstarted manifest. The fixture retains enough guest arrays that the checkpoint guard is reached, so this is not a valid accepted OOM witness under the unchanged checkpoint cap.

No original artifact, resource, world, network, sibling worktree, or push was used. The gate did not complete; this profile must not be accepted or described as verified beyond the recorded partial controls.

## Evidence

`evidence/java-evm/minecraft-entry/string-builder-recovery-f3672a818/` contains pins, compiler logs, generated-fixture summary, successful gate command records/terminal heads, the failing OOM receipt, and checksums.
