# Entry-origins design evidence

This directory is durable design provenance for `JAVA_EVM_MC_ENTRY_ORIGINS_PROPOSAL.md`, produced at Git base `ea1fa2c8a9628e23c8024d6d835cba70a553f6b7`.

It contains **no EVM run, generated class, ZIP, original-JAR payload, or Java execution output**. The proposal's measurements are citations to already parent-reviewed generated-only evidence; source facts are pinned by the paths and SHA-256 values in `SHA256SUMS`.

## Inputs retained by reference

| source | role | status retained exactly |
|---|---|---|
| `JAVA_EVM_MC_MAIN_ENTRY_PARENT_PREFLIGHT.md` | parent-generated wrapper/main result and verifier repairs | measurement, not a direct-main implementation |
| `JAVA_EVM_MC_LINK_FRONTIER_PARENT_PREFLIGHT.md` | fixed package loading/link behavior and static capacity context | measurement/source review, not a loader |
| `JAVA_EVM_MC_CAPACITY_BASELINE_PARENT_PREFLIGHT.md` | generated 8/256KiB disposable experiment and dense ordinary refusal | measurement; **not** a profile promotion |
| `JAVA_EVM_MC_CB0_REVIEW.md` | accepted transport/ownership/persistence contract | accepted source review |
| `jvmevm/localcontinuation/cb0/runtime/CB0ClassCoordinator.sol` | exact common-index constructor and load route | read-only source fact |
| `jvmevm/localcontinuation/cb0/{session.go,cb0.go}` | public Session, Head, persistence and cap source facts | read-only source fact |
| `jvmevm/runtime/local/vfs0a/VFS0aInterpreter.sol` | exact-int root and artifact/checkpoint source facts | read-only source fact |
| `jvmevm/artifactstore/{zi0,di0}/runtime/*.sol` | EVM archive/index/resource binding source facts | read-only source fact |
| `JAVA_EVM_MC_NEXT_ENTRY_FRONTIER.md`, `JAVA_EVM_MC_STARTUP_PROPOSAL.md` | existing static MC/JAR boundary facts | static only; no runtime authority |

The source hashes are a snapshot identity aid, not an authority that replaces the EVM checks described in the proposal. Read paths are repository-relative to this base. No input was copied, modified, or deleted.

## Refusal provenance preserved

The proposal relies on, but does not relabel, these parent-recorded negatives:

* CB0 constructor `CB0Error(13)` is the common-index/root restriction in source, not an observed two-origin run.
* The capacity baseline's generated dense 181969-byte/three-image package refused at ordinary gas with `LC0ControlError(7)`; direct/q7 and the next ordinary q1 resume refused. The parent separately recorded only boundary 1B completion. This remains evidence against a broad 8/256KiB claim, not proof of any particular expensive function.
* The link-frontier PC38 correction is an `invokevirtual` demand resolution, not a null `checkcast` failure; do not use it to claim eager or lazy target loading.
* The main-entry worker's original verifier defects and handwritten initial-package narrative remain non-evidence as the parent review states. The proposal cites only the parent-corrected result.

No failure log has been overwritten, moved, or cleaned up by this design task. Existing raw receipts/checkpoints remain in their original tracked parent evidence directories.

## Reproduction boundary

This is a documentation/source-audit result only. To repeat the audit at the recorded base, verify `SHA256SUMS` from repository root:

```sh
sha256sum -c evidence/java-evm/entry-origins/design/SHA256SUMS
```

This check does not run Java/EVM and does not validate a future artifact. Any eventual B0/A0 preflight must use a fresh ignored `build/java-diff-mc-entry-origins-*` directory, preserve its own sources/receipts/refusals/hashes under a new evidence directory, make ordinary <=100M/30s EVM calls only, and use the 20-minute/4-GiB watchdog. No 1B call is authorized by this design.
