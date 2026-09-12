# CB0 fixed class package, shared LOCAL EVM world

See JAVA_EVM_MC_CB0_PLAN.md and parent review for acceptance status. CB0 transports
opaque ZIP input through accepted AS0/ZI0/DI0, then a constructor-fixed coordinator
EVM-reads FINAL resource bytes and passes them into unchanged VFS0a start/resume.
No host ZIP/class parser, inflater, raw-class execution API or private Session access.

Fresh initialization explicitly installs exact accepted oversized LOCAL engine code
at its fixed address (nonce0, no EVM gas claim) plus one ordinary AS0 CREATE, then
publishes ONE atomic root. All resource/coordinator/pages use ordinary CREATE.
This is not standard-chain deployment of the oversized engine. Reopen never installs
or creates code; its Initialization receipt reports no performed initialization.

One world owns one archive/index, up to4 DI0 decoders, one immutable ordered class
package and one Java instance. A package may reorder/subset existing resource slots;
its selected images total<=65536B. No new decoders after coordinator construction.
Start/Resume never accept raw classes; the EVM alone materializes the class array.
Root/name/package arguments are assertions, not guest-byte authority. VFS seeds are
empty and existing heap/bootstrap/checkpoint/VFS/JVM budgets stay unchanged.

Lifecycle: Append/Seal -> CreateIndex/DiscoverIndex/ScanIndex/FinishIndex ->
CreateDecoder/StepDecoder/PublishDecoder -> CreateCoordinator -> Start/Resume.
Use actual Head/returned epoch/checkpoint roots, not assumed progress increments.
Latest opaque checkpoint remains readable after ordinary return OR Java exception.
ReadCheckpoint only exposes the latest published head and returns a defensive copy.

JavaResult contains the typed EVM Slice, Checkpoint, StateRoot, GasUsed and exactly
one copied nested engine CheckpointCommitted log. CB0's own ABI declares no events.
Event instance/epoch/roots/lifecycle/counters must match the slice. See the explicit
JAVA_EVM_MC_CB0_EVENT_AMENDMENT.md correction to the original no-log draft.
EVM failure exposes gas/revert only; publication failure gas only, no checkpoint,
Java outcome, logs or success root. Every success commits/reloads and disk fsyncs
checkpoint/trie/code/manifest/rename/directory before its receipt. Ambiguous after-
rename failure poisons APIs until exact reopen; earlier errors restore prior roots.

Namespace: JVMEVM-MC-CB0-LOCAL-STORE-1\n. Bounded metadata/marker/routing/pins checked
before database open; nested links and incomplete/foreign stores refused. Only
test fixture generators use ZIP libraries or javac, never production execution.

make java-mc-cb0-test
make java-mc-cb0-demo # generated class pipeline only, NOT Minecraft readiness

CB0 is a fixed package bridge, not a general/lazy ClassLoader. It does not expand
Java root descriptors, provide main(String[]) yet, execute original Minecraft code,
accept EULA, run a listener/world, or produce genuine Done.

If this machine's /tmp user quota is exhausted, scope temporary storage to one run:
mkdir -p build/java-diff-cb0-tmp
TMPDIR="$PWD/build/java-diff-cb0-tmp" make java-mc-cb0-test
This is not a global setting or permission to remove other processes' temporary data.
