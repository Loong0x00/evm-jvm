# Resume anchor — Minecraft-first, local-only

Verified at recovery from main `3ac58bf72` (branch `java-on-evm`, not pushed):

- Accepted P19 semantic source: `evidence/java-evm/minecraft-entry/parent-668583cae/artifacts/engine/MCEntryInterpreter.sol`.
- Gas-only authorized original continuation: `parent-668583cae/u64max/`. The 62-file parent evidence manifest and authentic terminal checkpoint SHA256 were reverified on recovery.
- Untouched original JAR: `/home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar`, SHA256 `fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`.
- Last authentic execution: 1,405,662 JVM /84 internal, epoch1399, lifecycle3, guest `java/lang/OutOfMemoryError` kind7/handle1974. Checkpoint SHA256 `1a5996cc032cdee1ddf48d1a652368ec5e2b1291b23e4979fa0693a5f89aa771`. It is a terminal result, **not a resumable RUNNING state**.
- Measured cause: ordinary arrays1024/1024; objects943/1024, array elements81133/262144. Only MAX_ARRAYS1024->2048 is the next scoped candidate.
- User-authorized original LOCAL gas is now `uint64.max`, q<=4096, EVM Cancel watchdog30s/call. Generated gates retain ordinary1B and1200s whole-gate limit. High gas removed the artificial4.2B blocker; no more low-return gas micro-optimization cycle.
- Candidate draft: worktree `/home/user/evm-jvm/max-arrays-2048`, branch `mc-max-arrays-2048`, from3ac58bf72. Sole semantic writer restarted there; generated-only, no original/sibling/network inputs.
- Optional unrolled-lanes candidate `8b09c2dba` remains preserved on `mc-packed-float-unrolled-lanes`, deliberately not merged (runtime392895 leaves only321 bytes, unnecessary after high-gas authorization).

Preserve all existing commits, worktrees, generated evidence, original worlds and failed-attempt evidence. No reset/clean/push. New independent semantic domains must rebuild/authenticate source and recompute all97 materialized bootstrap leaves; no reuse of an OOM/failed checkpoint. Goal remains genuine unchanged-original startup through `Done (...)!`, superflat first. Logger completion, world creation, EULA handling and `Done` are not yet established.
