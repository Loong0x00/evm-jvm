# Parent-owned shared-world preflight (not production acceptance)

The interrupted worker had uncommitted drafts and a failing verifier, not a result.
Original selected drafts/failed log were preserved under draft/ with SHA provenance;
its worktree was not edited or deleted. Parent inspected and repaired separate copies.
repair_driver.py records draft-to-parent corrections; driver.go.txt is the actual
standalone source. There is no reflection/unsafe/private-session attachment.

See JAVA_EVM_MC_SHARED_WORLD_PARENT_PREFLIGHT.md for measured scope/corrections and
JAVA_EVM_MC_CB0_PLAN.md for the subsequent production freeze, not an acceptance claim.
Sources and trusted generated Java8 fixture builder are here; no official JAR/classes.
Final captures include per-process BEFORE/AFTER counters; true observed deltas, NOT
inferred +1 on reopen, form the actual report. Metadata-only stage writes are separate
from EVM mutations. Local exact VFS engine install is explicit and not EVM CREATE.
All class bytes entering the JVM are assembled/read inside EVM from FINAL DI0 pages.

first-direct* / initial-guard-not-oog.json preserve the parent's initial incorrectly
named OOG proof failure: actual EVM result was existing VFS LC0ControlError7 after
a completed changed guard SSTORE, not OOG. The final test checks that exact refusal
and raw trie equality BEFORE reload, then normal retry; no failed result is used
as a continuation. Draft/incomplete-run.log preserves its separate read-count failure.

terminal-complete-watchdog.json is the final full fresh reconstruction:7.456s,
325885952B sampled process-group RSS,exit0/no20min4GiB limit. Terminal checkpoints
are retained and checked on reopen. Earlier final-watchdog.json precedes that extra
terminal-blob check and is not substituted for it. Fifteen actual processes; results
317/299, Java36/internal5, direct/q1/q7 slices1/36/6; exact4-class65536B bound executed,
65537 and five-class count rejected. Core/accepted profiles unchanged.

Reproduce into a NEW ignored workspace, using new outer log names:
python3 evidence/java-evm/watchdog.py build/java-diff-NEW.log build/java-diff-NEW-watchdog.json \
 bash evidence/java-evm/class-bridge/shared-world-parent-d76a45057/reproduce.sh build/java-diff-mc-shared-world-parent-NEW

The terminal proof is a preflight with diagnostic manifest/schema, not a hardened
production transport. Constructor/binding/errors and atomic initial publication
for the new production profile are frozen separately. No Minecraft Java execution,
EULA, listener, world, Done, provider-review credit or implicit push.
