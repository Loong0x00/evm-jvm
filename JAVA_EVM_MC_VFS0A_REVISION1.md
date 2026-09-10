# VFS0a revision1 — explicit LOCAL code-size review and path correction

Status: **parent implementation revision, NOT acceptance**. Supersedes the initial
VFS0a256KiB installation gate in cca4841 ONLY for this still-unaccepted profile.
All accepted IOE0/SC0/TL0/LC0/LB0/stock budgets and artifacts remain unchanged.

## Measured size and selected LOCAL design

Runtime candidate32a159b integrated f2b64ff, harness7913c85 integrated06e39c2.
Parent checked source/runtime/ABI/combined bytes and their hashes independently:
source `e84afe936f561415c06b8937aecd2cf0f38f42825e51c1e86c5f2161af5e3f2e`;
287440-byte runtime `03d502fa3bf036d997891d5e43bfb4852052ed3d7e5c29ab8cc213283e395bd6`;
ABI `16346751accb944db73a8a8b33bee6923c9ccabca1896af41f4926a2895e6520`;
combined `3a37affdc008fe0b888196520dc29aa166e302ad74b6f41e8dc3b128b0c690aa`.
Exact excess25296B over262144. Parent reproduced the mandatory Go-loader rejection
in `/tmp/mc-vfs0a-parent-initial-cap.log`, exit1; no EVM behavior was accepted there.

Options reviewed: (A) remove substantial required filesystem/validator functionality;
(B) split into separately committed EVM modules, introducing another code identity,
ABI/serialization boundary and new deployment/continuation proofs; (C) retain the
single LOCAL interpreter with a newly explicit finite installation allowance.
Select C under the user's LOCAL artistic VM-in-VM priority, rather than making stock
module migration a prerequisite. This does NOT assert optimization is impossible.

**New VFS0a LOCAL code ceiling:320KiB=327680 bytes**, enforced in the new build/loader/
tests. The initial measured candidate leaves40240B under this allowance. This is a
repository transport/install policy, NOT EIP170, CREATE, consensus or EVM semantics.
No new opcode/precompile/free work, host Java evaluator or host filesystem bridge.
100M ordinary/1B boundary gas,25M commit reserve,1MiB checkpoints, all guest/VFS quotas,
per-call units and20min/4GiB watchdog remain exactly unchanged. Old profiles stay at
their old ceilings. Future excess requires another explicit review, not auto-growth.

Raising the LOCAL code allowance establishes NO gas, semantic, continuation or
Minecraft success. Both workers had delivered unexecuted VFS behavior; actual gates
must now run, preserve all failures, and be independently accepted after corrections.
The original over-cap artifact/hashes and failed gate remain historical evidence.

## Required path amendment

JAVA_EVM_MC_VFS0A_PATH_REVIEW.md is an acceptance blocker, not an optional probe.
Preserve slash-normalized lexical File.path and C-locale messages. Stat/mkdir/open
must not erase missing or non-directory intermediate traversal by prematurely
collapsing `..`. Missing traversal gives absent/ENOENT; a non-directory ancestor gives
absent for stat, false for mkdir, and **open -4 NOT_DIRECTORY**. Add ordinary Java
` (Not a directory)` suffix selection to BOTH FIS/FOS message builders. Recompile and
record their new source/class pins; do not native-mint message Strings/Throwables.
Other six new images and all30 accepted IOE0 images remain byte-identical.

Retain the Java8/21-observed canonical fallback for mkdirs (both file/../new and
missing/../new may succeed); do not globally apply strict mkdir/open traversal to it.
Keep explicit lexical seeding normalization as configuration semantics, and specify
inspectFile path policy separately from Java File open. Pending-bind PCs must be
re-derived/verified against revised pinned Code, never assumed after recompilation.

## Next disjoint work

One runtime writer owns runtime/local/vfs0a: path/status/Java image amendment, actual
native/codec/runtime defects, updated artifacts/repro,320KiB build. Harness writer
owns localcontinuation/vfs0a excluding parent's parent_test.go/validation_test.go,
and testdata/local/vfs0a: actual controls/chains, opaque transport/durability fixes.
Parent retains independent32 groups, revised pin review, integration, watchdog/legacy
runs and acceptance. No third worker, Fast/priority, push/settings/core edits or fake
Done. Last accepted IOE08f29f8c; Minecraft/EULA/listener have not run.

## Parent integrated revision1 pins (not acceptance)

Runtime6b8caf8f8 integratede38c5e734, harness02e9c31..761a991 integrated throughb9211d274.
Final293010B runtime SHA78d57a051311538c13ed6b60a59ceab5800722bf49ec9e9f3683bb23521739c9;
source168a965ad0aa43eb3216d97cf38169da63d0a4294ea9f9651ab86ddd0d0c04c3;
combined6dc889b2461775397d7cdbdffd0c82c9fa1f8e9680ddb3a5b06af270f2a549b8.
ABIunchanged16346751accb944db73a8a8b33bee6923c9ccabca1896af41f4926a2895e6520.
New FIS1515B/cdda6fb532785d7e43d535bea0225e0bd5e920e28b39353c54f13e3d41ef9a65,
source0041c83044413ba6e4199e6a8be990a8810283aa07f5c5587ee69653945e26e8;
FOS1618B/50aa63fa914989dada682851a65c9ce0c5400fd0f8e4e52246553ee2fc084315,
source79f3010db7a8ee7adea15937dec5a06798da6f48017a34a265fcd73f4ebb82e8.
Eight new images now6050B; parent independently recompiled all8 and verified30 inherited
commitments unchanged. Other6 new images unchanged. Original5976B pins are historical.
Parent must rerun FINAL293010B artifact: harness worker reported success on DIFFERENT
292377B/569bf7072f663539595052985a0c99c77aa32197bc9f4c85236413b619c87475 intermediate.
