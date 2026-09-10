# LOCAL MC-VFS0a continuation transport

Package `vfs0a` is the bounded opaque Go transport for the frozen
`VFS0aInterpreter` profile. **VFS0a remains unaccepted.** The integrated original
287440-byte artifact is known nonfunctional: its first actual EVM run reverted all
24 roots with `ThrowableProfileError(2,37-or-38,0)`. Runtime correction and a fresh
artifact are dependencies of the behavioral gates below; tests do not skip or mask
that failure.

The harness loads only the embedded
`vfs0aassets.Artifact()` and validates the exact five-method/one-event ABI. There is
no artifact fallback or missing-artifact test skip.

`SeedFile` carries raw path/data bytes and a read-only bit only on `Start`.
`Resume` has no seed input. Java classfiles, checkpoints, seed bytes, dynamic
Java class names, and file-view paths/data remain opaque to production Go;
path normalization, VFS mutation, Java execution, checkpoint validation, and
all native effects occur in EVM code. `InspectFile` is a bounded EVM view over a
fully validated checkpoint. It uses a copied state and neither publishes a
head nor grants resume authority.

The oversized runtime is explicitly installed once at the frozen LOCAL address
`0x4a564d45564d564653304152554e54494d450001` (the initial harness's accidental
IOE0 address was corrected); this is not CREATE or standard
chain deployment evidence. Calls retain the fixed dev-chain context, finite
1..1,000,000,000 gas range, 1 MiB checkpoint cap, owner/epoch/root CAS, exact
17-field result, ten-field head, and VFS roots/counters.

`Open` creates only an empty format-1 namespace marked
`JVMEVM-MC-VFS0A-DISK-STORE-1`, or reopens its committed trie/code without a
startup reinstall. Publication preserves IOE0's ordering: durable checkpoint
blob, trie/database sync, then owned manifest temporary, rename, and directory
fsync. Existing blobs are resynced before reuse. Pre-publication failures reload
the old root; an ambiguous post-rename failure poisons the session until reopen.
Failed publication returns diagnostic gas only—never speculative result,
checkpoint, or logs. Reads are bounded and internal symlinks are refused.

The trusted fixture corpus pins the plan's original 24 Java-8-primary roots in three
groups and opaque seed records. A separate seven-root regression bundle preserves
stock Java 8/21 observations for `file/child`, `missing/../seed`, and
`file/../seed`, including ENOTDIR messages for both stream wrappers and the distinct
`mkdir`/`mkdirs` behavior; it does not change the original root identities.
Tests require all 24 one-call controls and full
q1/q7 chains for the selected ten roots, with at most 4,096 units and 4,096
slices per VFS0a case. Java 8 and Java 21 C-locale host-only oracles run in
owned temporary directories; both currently return 1 for every root, so there
are no secondary-version differences to retarget. A disk/new-process test pauses only at a decoded test-only descriptor phase1 with
nonzero bind depth/PC—not merely at a nonzero descriptor count—after output
truncation and before handle binding. It then resumes without reopening/truncating
or installing code and compares exact terminal roots/counters with an uninterrupted
control. Production Go still has no checkpoint/heap/path parser.

## Harness-r1 verification record

At harness commit time, the read-only runtime-r1 peer had a freshly built but not yet
integrated 292377-byte candidate, deployed-runtime SHA-256
`569bf7072f663539595052985a0c99c77aa32197bc9f4c85236413b619c87475`.
A Go overlay replaced only the embedded artifact input with that peer file; no runtime
source/artifact was copied or committed here. Against those exact bytes:

- all original 24 controls and the selected ten full q1/q7 chains passed in 185.332s;
- all seven path/ENOTDIR actual-EVM controls, plus q1/q7 for the two file-prefix
  wrappers and mkdir distinction, passed in 103.419s;
- exact phase1/FOS putfield-PC29 pending-truncate disk/new-process resume passed in
  5.625s without code reinstall;
- the final harness package (including new-process embed independence) passed in
  301.122s.

Reproduction used `go test -overlay=/tmp/vfs0a-runtime-r1-overlay.json
./jvmevm/localcontinuation/vfs0a -count=1`; the overlay mapped only
`jvmevm/runtime/local/vfs0a/artifacts/VFS0aInterpreter.json` to the peer's same path.
This is dependency evidence, not a claim that this branch's old embedded artifact
passes: a direct `seedFile` replay still fails with the retained
`ThrowableProfileError(2,37,0)`. Parent must integrate and independently hash/retest
the final runtime before acceptance.

Ordinary calls use 100,000,000 gas; explicit boundary work may use
1,000,000,000 gas. The runtime remains limited to 320 KiB (VFS0a revision1 only),
checkpoints to 1 MiB, ordinary cases to 4,096 dispatch units, and dedicated quota
cases to 65,536 units. The external acceptance gate remains 20 minutes/4 GiB. This
package adds no host filesystem production bridge, Java/path/heap parser,
Minecraft/JAR/EULA execution, listener, or readiness claim.
