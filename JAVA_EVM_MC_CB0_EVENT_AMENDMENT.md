# CB0 parent event-contract correction

Originally recorded while CB0 was UNACCEPTED; now verified in JAVA_EVM_MC_CB0_REVIEW.md. Parent strict Java-pipeline tests exposed a conflict in the
original freeze: it prohibited all emitted logs, but the exact unchanged accepted
VFS0a engine emits CheckpointCommitted on EVERY successful start/resume. The CB0
controller itself correctly has no events; nested engine logs still exist in EVM.
The interrupted transport silently omitted them. Neither omission nor rejecting
all successful Java slices is an acceptable final interpretation.

Amend ONLY the unaccepted CB0 Go receipt/validation contract:

- CB0 ABI still has exactly10 functions+constructor+CB0Error, no events.
- Every successful Start/Resume must emit exactly ONE log from the pinned VFS0a
  address, with its exact CheckpointCommitted event ID, bound coordinator instance,
  epoch, checkpoint/machine/VFS roots, lifecycle and cumulative counters matching
  the decoded EVM slice. Extra/mismatched logs reject and restore prior state.
- JavaResult gains Logs []*types.Log, defensive copies returned ONLY AFTER successful
  publication. EVM failures still gas+revert only; publication failures gas only,
  with no slice/checkpoint/root/logs. No engine/runtime/bytecode/gas/quotas change.
- Expected instance can be cached from the successful pinned coordinator constructor's
  fixed static ABI hash of address/package/salt; reopen reconstructs it from already
  validated EVM Head getters. No hidden publication-time getter or caller authority.

The failed parent strict-no-log test is preserved in session-fixes.log. This was a
parent freeze error corrected from actual engine source/behavior, not a change to
fixture results or a claim that the unfinished transport was already verified.
