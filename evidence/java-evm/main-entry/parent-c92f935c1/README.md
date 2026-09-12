# Independent main-entry acceptance of a generated preflight

See JAVA_EVM_MC_MAIN_ENTRY_PARENT_PREFLIGHT.md. Worker c92f935c1 remains archived
unchanged; integration a70ca4acf. Original replay succeeded, but copied-report
controls exposed missing gas-range and q7-count assertions in its verifier.
check_original_verifier.py/verifier-findings.json retain this finding, not EVM
execution data. The worker's initial-package-pin-refusal.log is a handwritten
provenance note with unverified date, not a captured raw transcript.

repair_driver.py produces a COPY of the public-CB0 driver with actual setup receipt
gas, real bad-package Error16 bytes, ordinary retry, no-reCREATE checks and reopened
trie-root chaining. verify_parent.py checks all intermediate opaque checkpoint
files against actual receipt hashes, strict quantum/epoch/lifecycle/gas/counters,
78 distinct process identities and terminal equality. test_parent_verifier.py
accepts a valid copied control and refuses five distinct corruptions. These copies
are only verifier tests and never supplied as execution/checkpoint authority.

content/ is an independent885B generated Java package. It really reads UTF-16 code
units with String.charAt, including NUL, lambda, D83D DE00 surrogate pair and snowman;
original worker Unicode test observed only string lengths. No accepted code, ABI,
profile or quota changes. Separate Java8 oracle, never in the execution ZIP.

Final fresh combined gate17.197s/335765504B, whole20min/4GiB watchdog. final/ has all
actual setup/slice/terminal JSON receipts for main78 and content41 processes, final
reports, opaque terminal checkpoints, pin/regression logs and empty protected diff.
Terminal .checkpoint files are generated-fixture EVM outputs, not future execution
inputs or recovered failed traces. Every reproduction re-executes the EVM.

Scripts require a NEW ignored build/java-diff-mc-main-entry-* prefix. Essential
source and evidence are here, not /tmp; TMPDIR is scoped to each generated build.
Do not overwrite old captures or worker provenance. No original server/JAR bytes,
original Minecraft instruction/startup/world/listener/EULA/Done or implicit push.
