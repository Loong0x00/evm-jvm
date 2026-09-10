# VFS0a parent path finding — acceptance blocker

Status: **independently reproduced prototype/Java8 mismatch; production fix pending**.
This refines the initial lexical-resolution assumption in `cca4841`. Do not promote
passing core fixtures, standalone kernel or frozen wrappers to VFS acceptance while
these cases are unresolved. No production Solidity/peer worktree has been edited.

## Evidence

Parent stock Java8u504 and Java21, explicit LC_ALL=C, separate owned tempdirs with
regular files `file`=`x` and `seed`=`y`:

| path | File.exists | FileInputStream(File) |
|---|---|---|
| seed | true | reads121 |
| file/child | false | FNFE `file/child (Not a directory)` |
| missing/../seed | false | FNFE `missing/../seed (No such file or directory)` |
| file/../seed | false | FNFE `file/../seed (Not a directory)` |

On the independently rebuilt standalone EVM kernel, parent new actual EVM calls give:
seed open=1 (236341gas); file/child=-1/MISSING (238079gas);
missing/../seed=1 (249779gas); file/../seed=1 (246248gas).
The latter two open successfully because pure lexical collapse erases an invalid
intermediate traversal. The file/child status would select the frozen Java wrapper's
wrong ENOENT suffix rather than ENOTDIR. This is not a codec/hash/host-oracle mismatch.

A separate Java8/21 control establishes operation-specific behavior:
`mkdir("missing/../onea")` and `mkdir("file/../oneb")` both false;
`mkdirs("missing/../manya")` and `mkdirs("file/../manyb")` both true.
Thus globally removing dot support, or blindly using the same strict intermediate
walk for mkdirs, would not be an honest implementation of the measured Java8 cases.
Java File.mkdirs has canonical fallback behavior unlike mkdir/open/stat.

Logs `/tmp/mc-vfs0a-parent-path{8,21}.log`,
`/tmp/mc-vfs0a-parent-path-kernel.log`, `/tmp/mc-vfs0a-parent-mkdir{8,21}.log`.
Ignored oracle/kernel reproducers are in `build/java-diff-mc-vfs0a-parent/`.
Permanent trusted host expectations are also in
`jvmevm/localcontinuation/vfs0a/parent_test.go`,
`TestVFS0aParentPathTraversalHostOracles` (explicitly HOST-only, not passing VFS tests).
The root Code is separate from trusted OracleMain's owned-file setup so it can be
reused later with equivalent raw EVM seeds and actual production native execution.

## Required parent correction before acceptance

Preferred correction: preserve normalized lexical File.path for messages, perform
operation-appropriate traversal before erasing `..` for stat/mkdir/open, and distinguish
missing from a non-directory ancestor. Add open status -4/NOT_DIRECTORY and ordinary
Java suffix Code ` (Not a directory)` for FIS/FOS, with newly compiled/reviewed pins.
Keep mkdirs' measured canonical fallback separate. No native Java allocation or
host path decisions, no new OS errno carrier, no mutation on failed open.

Raw initial seeds may retain their explicitly defined lexical normalization contract;
this is a configuration operation, not a stock Java File open. Read-only inspectFile
must have an explicitly recorded path policy and cannot silently be treated as proof
that File.exists/open accept the same ambiguous lexical traversal.

The two implementation workers were already writing against the initial freeze.
Parent will reconcile this finding at handoff (or a reviewed freeze amendment), update
all affected source/class/artifact pins, rerun genuine failed-path controls and their
continuations, and retain the current failure evidence. Do not silently treat a wrong
Java value/message as success. An explicit narrower hard-unsupported profile would
require a documented parent scope decision instead, not an invented Java result.

All previous accepted profiles remain untouched. VFS0a remains unaccepted and Minecraft
has not run; no EULA, listener, filesystem capacity or readiness claim follows.
