# VFS0a candidate integration findings (parent, unaccepted)

Base: f2b64ff runtime32a159b +06e39c2 harness7913c85; revision1 profile410a32b.
Initial candidate source SHA e84afe936f561415c06b8937aecd2cf0f38f42825e51c1e86c5f2161af5e3f2e;
runtime287440B SHA03d502fa3bf036d997891d5e43bfb4852052ed3d7e5c29ab8cc213283e395bd6.
Parent verified hashes and exact artifact/runtime agreement. Under initial256KiB the
loader correctly rejected it; revision1 explicitly selects320KiB only for VFS0a.

## Actual first behavioral run: ALL24 controls reverted

`go test -v ./jvmevm/localcontinuation/vfs0a -run '^TestVFS0aHarnessContinuationCorpus$' -count=1`
failed0.925s. Log `/tmp/mc-vfs0a-parent-initial-behavior.log`.
Exact selector b584576c is `ThrowableProfileError(uint256,uint256,uint256)`.
Revert arguments `(2,37,0)` or `(2,38,0)` depend on fixture class count. No terminal
checkpoint, q1/q7 chain, VFS value, gas-success or readiness claim follows.

Source explanation: `_validateVFSHeap` and `_streamHandle` pass `handle:I` to inherited
`_canonicalFieldOffset`, which unconditionally requires KIND_REF. FIS/FOS int fields
therefore fail the Throwable field helper. Fix typed canonical VFS field resolution;
do not globally weaken Throwable's exact reference-field validation.

## Additional source review items requiring real controls

1. `_runVFSNative(stat0)` directly returns inode.kind (DIR1/FILE2), while pinned
   Java exists/isFile/isDirectory expects stat missing0/FILE1/DIR2. Translate the
   distinct native status convention; do not change inode wire kinds or Java pins
   to hide the mismatch.
2. `_bindVFSField` and `_validateVFSHeap` use fixed PCs rather than re-deriving the
   actual pinned constructor's native-return/putfield corridor. The latter checks
   a descriptor ID in a local for almost all PCs, but does not require the exact
   operand stack shape/ID/receiver at each corridor position. Do not accept a valid
   generic integer local as sufficient proof of the active branch/store stack.
3. Clarify and enforce serialized bindPC as the exact **putfield PC** (initial pins
   FIS28/FOS29), not the native invoke PC (18/19). Derive invoke and bind locations
   from parsed reserved Code; require exact method/frame/post-super local0 REF,
   owner, top constructor depth and ID placement. No host metadata or skipping.
4. Apply the independently reproduced path/ENOTDIR amendment in REVISION1 and
   PATH_REVIEW, including operation-specific mkdirs fallback and revised Java pins.

These are not an exhaustive review. Initial EVM gates were not performed by the
workers under the old size block; after correcting these issues, actual full controls,
continuations, codec/provenance/heap/frame boundaries, persistence failures and parent32
probes are mandatory. Keep failures and successful independent IOE0 Code controls.
No accepted profile/source/bytecode/core limits have been modified.
