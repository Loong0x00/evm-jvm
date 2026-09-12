# Parent-verified generated Java main entry

**Generated preflight verified, not a new production profile.** Worker c92f935c1
integrated a70ca4acf, parent freshly rebuilt and replayed, then added independent
receipt/verifier/UTF-16 controls. Accepted CB0 0fdb9dcf7 and all EVM/JVM/core code,
root ABI, quotas, artifacts and LOCAL installation rules remain unchanged.

## Useful result

A real guest `int Launcher.run(int mode)` can create `String[]`, invoke a second
class's `public static void main(String[])`, then read its actual post-void-call
static state. This requires NO new engine root ABI. A future explicitly supplied
launcher could invoke an unchanged application's main; the target JAR need not
be rewritten. It is still an extra guest launcher and NOT direct void-main ABI,
JAR discovery, a lazy ClassLoader or original Minecraft execution.

All execution inputs are opaque generated ZIPs through PUBLIC CB0 Session APIs:
AS0 -> ZI0 -> DI0 FINAL -> EVM bounded page reads -> unchanged VFS0a Java. No host
class-array input, ZIP/class parser/inflater, evaluator, reflection/private Session,
StateDB access, page injection or failed-trace recovery. Java8 host oracles are
separate TEST processes; Oracle.class is excluded from the uploaded ZIP.

## Parent review findings

The worker's positive results replayed independently in6.226s/332533760B. All its
archived SHA256SUMS and freshly regenerated fixture hashes matched. However:

- Its verifier claimed nonordinary gas rejection but never asserted the range;
  a COPIED report with gas100000001 passed. It also accepted q7 replaced by the
  direct report. These are verifier flaws, not evidence of actual excessive gas
  or bad EVM execution. Copies only, original reports unchanged.
- Original Unicode inputs were only observed via `String.length()`, so they did
  not establish actual character values. Parent added a separate content fixture.
- initial-package-pin-refusal.log is a handwritten narrative with an unverified
  date, NOT a raw failure transcript. Preserve it as worker provenance only. Parent
  made fresh real bad-package EVM calls and retained typed receipts/revert bytes.

Parent copied/instrumented the replay driver without modifying the archived worker
source or production code. All successful setup mutation receipts now have actual
nonzero<=100M gas/root, including performed initial AS0 CREATE. All reopened Java/
terminal processes explicitly check NO engine install, NO AS0 CREATE, gas0 there.
Each Start/Resume records the EVM-loaded prior trie root, which must equal the prior
successful published root. Epoch, quantum, cumulative counters, lifecycle, typed
NPE, events, AS0/ZI0/DI0/package identity and terminal roots are asserted. Every
reported checkpoint SHA is checked against the actual retained opaque EVM file;
Keccak binding is checked by the accepted APIs and the Go replay. Terminal files
are archived. Counterexample tests prove the new verifier accepts a valid copied
control and rejects overgas, fake q7, changed checkpoint byte, re-CREATE flag and
wrong reopened root. These mutation tests are NOT EVM execution evidence.

The real bad assertion is one flipped bit of the asserted package root. EVM returns
exact CB0Error16 (`0x27cad659`+uint25616), positive ordinary gas, no success root.
Published root before/after remains equal; then the ordinary correct constructor
succeeds. This is transport-level published-root recovery, NOT an assertion about
raw failed-CREATE creator nonce rollback. Failure is never fed as a checkpoint.

## Measured Java and process results

Original generated Launcher417B+TargetMain378B=795B, ZIP SHA256
4eae36f7769eee73ea7c6646d85995cdf3e087e8d9e624989d13ef2af256f928:

| input | outcome | Java/internal steps | slices |
|---|---:|---:|---:|
| empty String[] |341|24/4|1|
| ASCII array |381|54/4|direct1/q7=8/q1=54|
| lambda/snowman length probe |351|57/4|1|
| null array |ordinary typed NPE,kind6|22/5|1|

Same input direct/q7/q1: final machine/VFS/package/AS0/index/DI0 roots agree.
Checkpoint/epoch/trie roots are NOT falsely required to agree across grouping.
Parent strict suite:78 distinct actual processes,66 actual checkpoint-file SHA
checks,180 recorded mutations including initialization and real bad assertions;
max mutation gas8428965, aggregate637425082 across calls (not a per-call budget).

Separate parent content fixture885B actually invokes String.charAt in loops over
ASCII, NUL, U+03BB, surrogate pair D83D DE00 (U+1F600), and U+2603. Ordinary Java int
arithmetic/overflow accumulates actual UTF-16 code units; separate Java8 oracle:

| input | result | Java/internal | slices |
|---|---:|---:|---:|
| empty |341|27/4|1|
| ASCII |-266910634|196/4|1|
| NUL/lambda/surrogates/snowman |-821743102|184/4|direct1/q7=27|
| null |typed NPE kind6|22/5|1|

Direct/q7 content roots and counters agree;41 distinct processes, max Java gas
15420736. All terminal returns AND Java exceptions retain/hash/reopen the exact
EVM-issued checkpoint. No Java interpretation or recovered failed bytes in Go.

## Final fresh gate

**17.197s /335765504B sampled process-group RSS, exit0**, full20min/4GiB watchdog.
Fresh guarded output directories, pinned CB0 artifact check, both complete new
replays, strict verifier controls, Go vet, accepted CB0 pipeline/eight-process/
publication/class-boundary/CAS regressions and empty protected-code diff. No1B
call or gas/quota increase. TMPDIR scoped only to ignored task build directories;
no global settings or unrelated temporary-data removal.

Evidence: evidence/java-evm/main-entry/parent-c92f935c1/; final/ retains all actual
per-process JSON receipts, reports, terminal checkpoints and gate sublogs. Scripts
require fresh ignored destinations; preserve old captures. The original worker
sources/failures/report and independent verifier findings remain separate.

## Next dependency

Investigate the actual fixed-package link/loading frontier with generated omitted
superclass/interface/unused-versus-used reference cases and a closed transitive
chain. Do not guess that all CP references are eagerly linked or call a4-image
package lazy loading. Current caps remain <=4/65536 aggregate, constant pool4096,
Code65535 and checkpoint1MiB; already EVM-decoded AbstractLogger90309 exceeds the
unchanged class/package cap. Any extension needs a separate explicit measured
proposal; adding an unnecessary root ABI is not the next step.

No original Minecraft instruction/main, EULA, listener, world or genuine Done.
No push. Continue default-Terra/high workers with independent parent gates.
