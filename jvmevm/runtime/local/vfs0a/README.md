> CURRENT: parent-accepted bounded LOCAL VFS0a, final292968B runtime
> SHA256717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86.
> See JAVA_EVM_MC_VFS0A_REVIEW.md for final fixes/gates/limits. Older candidate and
> overlay observations below are historical; they are not the final acceptance.
> This is Java/EVM file work, NOT Minecraft startup or standard deployment.

# MC-VFS0a local runtime correction candidate

Status: corrected runtime-worker delivery under `JAVA_EVM_MC_VFS0A_REVISION1.md`;
**not parent acceptance and not Minecraft readiness**. This directory is the single
LOCAL `VFS0aInterpreter` implementation. It does not modify consensus behavior,
accepted-profile budgets, checkpoint limits, host metadata handling, or the Java
execution boundary.

## Revision1 build and provenance

Build with Node dependencies pinned by `package-lock.json`:

```sh
npm ci --ignore-scripts
node build.js
node build.js --check
```

The build requires solc `0.8.30+commit.73712a01`, optimizer 200, via-IR, Cancun,
metadata disabled. The corrected artifact is **293010 bytes**, below the explicit
VFS0a-only LOCAL ceiling of 320 KiB (327680 bytes):

- Solidity source SHA256: `168a965ad0aa43eb3216d97cf38169da63d0a4294ea9f9651ab86ddd0d0c04c3`
- deployed runtime bytes SHA256: `78d57a051311538c13ed6b60a59ceab5800722bf49ec9e9f3683bb23521739c9`
- ABI SHA256: `16346751accb944db73a8a8b33bee6923c9ccabca1896af41f4926a2895e6520`
- combined artifact/provenance SHA256: `6dc889b2461775397d7cdbdffd0c82c9fa1f8e9680ddb3a5b06af270f2a549b8`

The eight appended image pins now total 6050 bytes. The other six new images and all
30 inherited IOE0 images remain byte-identical. The two recompiled Java8 stream images
containing ordinary ` (Not a directory)` selection are:

| image | bytes | source SHA256 | class SHA256 |
|---|---:|---|---|
| `java/io/FileInputStream` |1515|`0041c83044413ba6e4199e6a8be990a8810283aa07f5c5587ee69653945e26e8`|`cdda6fb532785d7e43d535bea0225e0bd5e920e28b39353c54f13e3d41ef9a65`|
| `java/io/FileOutputStream` |1618|`79f3010db7a8ee7adea15937dec5a06798da6f48017a34a265fcd73f4ebb82e8`|`50aa63fa914989dada682851a65c9ce0c5400fd0f8e4e52246553ee2fc084315`|

Recompile all eight tracked wrapper sources together with OpenJDK 8u504,
`javac -source 8 -target 8 -g:none`; `build.js` checks each source, class and embedded
Solidity image. Parent-owned tests must update only these two revised pins.

## Corrections

- VFS `handle:I` uses an exact INT-typed canonical-field resolver; Throwable's
  existing REF-only resolver and checks are unchanged. Heap/checkpoint validation
  also requires INT-tagged handle cells, while `File.path` remains REF-tagged.
- `stat0` translates wire inode kinds `DIR=1/FILE=2` to Java statuses
  `missing=0/FILE=1/DIR=2`.
- Pending bind authority is re-derived from the parsed reserved constructor Code.
  FIS/FOS currently derive native invoke PCs 18/19 and actual handle `putfield` PCs
  28/29. Serialized `bindPC` is the putfield PC. Validation requires the exact
  constructor method, top depth, post-super linked state, local0 REF/owner, ID local,
  and exact operand-stack shape at every success-corridor PC.
- Java stat/mkdir/open now walk the slash-normalized lexical spelling in order, so
  missing and non-directory intermediate components cannot be erased by `..`.
  Open returns `-4` for ENOTDIR. `mkdirs` separately retains the measured Java8/21
  canonical fallback; nonrecursive mkdir does not.
- `File.path` and error prefixes stay lexical. `inspectFile` intentionally remains a
  canonicalized read-only namespace view (the same lexical-collapse policy as seed
  lookup), not evidence for Java `File.exists`/open traversal behavior.

No native allocates Java Strings or Throwables. No reopen/truncate-on-resume, host
filesystem metadata, or host Java evaluation was added.

## Runtime evidence retained outside the repository

- Parent initial all-24 failure: `/tmp/mc-vfs0a-parent-initial-behavior.log`
  (`ThrowableProfileError(2,37-or-38,0)`).
- First successful 24-root/20-chain run after typed-field/stat correction:
  `/tmp/mc-vfs0a-runtime-typed-stat-behavior.log`.
- Corrected final build/check: `/tmp/mc-vfs0a-runtime-final-{build,check}.log`.
- Corrected path one-call aggregate: `/tmp/mc-vfs0a-runtime-path-control.log`
  (`result=2047`, genuine EVM).
- Five bounded one-call/q1 path controls against the final artifact:
  `/tmp/mc-vfs0a-runtime-final-path-q1-controls.log`; all terminal values,
  machine/VFS roots and counters agree. Results cover `file/child`,
  `missing/../seed`, `file/../seed`, FOS ENOTDIR, and mkdir/mkdirs
  operation-specific behavior.
- Pending truncate/new-process resume: `/tmp/mc-vfs0a-runtime-pending-newprocess.log`.
- Final harness attempt: `/tmp/mc-vfs0a-runtime-final-harness.log`. The genuine
  24 roots/20 q1+q7 chains, Java8/21 oracles, disk failure controls, ambiguous
  publication, and pending new-process resume pass. Two peer-Go harness defects
  remain outside this write set: `session.go` still uses the old IOE address instead
  of the frozen VFS address, and ABI-decoded missing inspection data is a non-nil
  empty slice while its test requires the exact zero `FileInspection{}` value.

Final parent validation, those peer-Go fixes, and reserved-test pin updates remain
outside this runtime worker's write set.
