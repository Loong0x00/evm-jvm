# Result: guest-frame snapshot full generated gate

`full-gate-run3` reused the candidate's source-verified 372134-byte LOCAL engine
and combined current focused frame probes with the current parent-generated
retained corpus. It passed in **852.8919992969604 s** (limit 1200): **525**
generated-only commands, **192** result rows, **153** canonical successful worlds,
and **13,144** independently re-encoded canonical receipts.

The focused `guest-stack`, `guest-stack-two`, and unchanged `thread-empty`
witnesses each run q1/q7/direct/reopen. They retain equal Java/internal counters,
machine roots, and opaque checkpoint digests. The gate also directly reopens the
changed-leaf no-use control and rejects a raw `StackTraceElement` before guest
execution.

The retained input is the current 205-fixture
`index-out-of-bounds-string-constructor-preflight` generated corpus. Its 187
retained result rows run direct/reopen where repeating historical q1 chains would
violate the fixed 20-minute gate; its existing focused q1/q7/direct rows remain
included. This covers current StringBuilder append(int), Integer-toString,
IndexOutOfBoundsException(String), resource, raw50/324338, OOM, ownership,
omission, initialization, and prior retained controls.

Two historical expectations are deliberately **superseded**, not counted as
passes: the former empty `Throwable.getStackTrace()` positive and the former
`StackTraceElement.getClassName()` omission. The focused nonempty frame snapshots
now prove the changed behavior; the unrelated four-argument StackTraceElement
constructor omission remains a retained atomic refusal. `results/full-gate-manifest.json`
records the exact input-tool, output, and coverage hashes.

This is generated-only evidence. It is not an original/JAR/Minecraft/world/EULA
replay or an acceptance claim.
