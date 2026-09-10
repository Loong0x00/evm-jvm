# LOCAL MC-VFS0a continuation transport

Package `vfs0a` is the bounded opaque Go transport for the frozen
`VFS0aInterpreter` profile. It loads only the embedded
`vfs0aassets.Artifact()` and validates the exact five-method/one-event ABI. There is
no artifact fallback or missing-artifact test skip.

`SeedFile` carries raw path/data bytes and a read-only bit only on `Start`.
`Resume` has no seed input. Java classfiles, checkpoints, seed bytes, dynamic
Java class names, and file-view paths/data remain opaque to production Go;
path normalization, VFS mutation, Java execution, checkpoint validation, and
all native effects occur in EVM code. `InspectFile` is a bounded EVM view over a
fully validated checkpoint. It uses a copied state and neither publishes a
head nor grants resume authority.

The oversized runtime is explicitly installed once at LOCAL address
`0x4a564d45564d564653304152554e54494d450001`; this is not CREATE or standard
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

The trusted fixture corpus pins the plan's 24 Java-8-primary roots in three
groups and opaque seed records. Tests run all 24 one-call controls and full
q1/q7 chains for the selected ten roots, with at most 4,096 units and 4,096
slices per VFS0a case. Java 8 and Java 21 C-locale host-only oracles run in
owned temporary directories; both currently return 1 for every root, so there
are no secondary-version differences to retarget. A disk/new-process test
pauses after output truncation has created the first descriptor and before the
constructor chain completes, then resumes without reopening/truncating or
installing code.

Ordinary calls use 100,000,000 gas; explicit boundary work may use
1,000,000,000 gas. The runtime remains limited to 256 KiB, checkpoints to 1
MiB, ordinary cases to 4,096 dispatch units, and dedicated quota cases to
65,536 units. The external acceptance gate remains 20 minutes/4 GiB. This
package adds no host filesystem production bridge, Java/path/heap parser,
Minecraft/JAR/EULA execution, listener, or readiness claim.
