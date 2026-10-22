# P43 — genuine Java8 Function SAM link/apply acceptance

## Result

Added a real Java8 `java.util.function.Function<T,R>` interface image exposing abstract `R apply(T)`. Generated concrete implementations and synthetic bridges execute their own ordinary guest bytecode. No fake apply/default return or new operational native was introduced. `compose`/`andThen`/`identity` remain outside this apply-only profile; a generated identity call explicitly raw-refuses, not a fabricated result.

Fresh unchanged original115 /802490B now links original Guava Function and completes `awu.<clinit>`. Its static function field points to **original awu$1 instance8247**, class108, with no fabricated fields. This proves interface hierarchy linking and original implementation construction; **original apply invocation is not claimed**. Generated tests independently exercise actual invokeinterface/bridge apply.

Precise original: **2223790 JVM instructions /112 internal steps**,44 independently verified successful canonical receipts, epoch44/lifecycle1. Checkpoint1283705B SHA256 `2b05be6edcc4015337763d3a87a014685819d1a099602d686d0e19b1bcc11337`. Fresh discovery643.085s plus same-package precise586.389s. World: `build/java-diff-mc-function-original115-parent-p43/official`.

Next exact q1: `MCEntryMissingClass`, **java/util/NavigableMap**, site4098/context105 (original ImmutableSortedMap). Still before main argument processing, world preparation, EULA/configuration startup, listening or Done.

## Parent corrections and independent build

Worker36f753033 honestly did not claim EVM execution. Parent found two missing pieces before acceptance: Function's raw namespace guard was not wired, and coordinator source still authenticated the old P42 engine. The worker source/results are preserved in `parent-function-interface/review/`; parent added only the exact reservation and the new actual engine-codehash anchor, then freshly compiled.

- Engine420330B SHA256 `1cc023e3613138f6e943e049e5b69c0acee01f3500c8ffdb60d236bfe9058584`, Keccak `4f2c95991a4c30e01e77793b8af9ecc7c681e47f969ba468e5143623bf720a67`.
- Coordinator5411B SHA256 `71975e2ae320eb34af26de9eb190052c9d0a54b3689b991aa68662a28ed706e6`.
- Bootstrap106, root `f9bc0a2e1368e55ca1e9b8f04ce5addf0d8d2427ce73c9996a05c7a1fddec670`.
- All105 old image bytes/order are unchanged, including parent-corrected PAT2. New Function leaf105 is a freshly javac8-reproduced275-byte interface, SHA256 `0c295ec9f5fcca2672e7b39bb33639dcf5134397eab22909b0ee6b773609bf1a`.
- Only prepare/count/append/root/new materializer and explicit profile domains change; execute/virtual/native dispatch unchanged. ABI/storage exactly match; native21/String12 unchanged.
- Array8192/object4096/elements262144/handles12545/raw150/1063930/CP2MiB/runtime-artifact1MiB/frames128 and execution-quantum limits stay fixed. Derived combined-class bound256=106+150 is not a quota increase or wire change.

## Fresh parent EVM verification

Parent-owned fixture covers direct/inherited SAM, captured state, identity/null arguments, generic synthetic bridge, wrong-type bridge ClassCastException, null-receiver NPE, instanceof hierarchy, and retained PAT2/fixed-width-CRLF/String replacement/array.clone behavior. Stock Java8 oracle is test-only, never execution input.

- Small raw4 q7/q1:3553 JVM steps, exact machine/VFS/counter/heap equality,167.203s at1B, distinct-process EVM checkpoint/code/Head validation.
- Same behavior with **exact150 raw classes /256 actual classes**, including the Function at **class index255**, q4096/q65536:3553 steps, exact roots/heap/reopens. An actual1B budget shortage was preserved; fresh **separate2B** pass in1.965s, peak1544879261gas. No false ordinary1B claim.
- Fresh1B omitted-identity/raw-Function controls: typed profile refusal after successful checkpoints or raw reservation rejection, unchanged Head/root. Identical profile Function bytes supplied as raw are also forbidden.

The worker's broad `go test`/`go vet` result is not used as a substitute for these new-artifact EVM gates. Parent's fresh Java/Solidity/Go build and source/root/ABI proof are preserved. All65536 sine bits still match the accepted read-only-oracle-verified table SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

No geth opcode, gas/state/consensus, EIP170/EIP3860 or shared legacy-profile change. Oversized engine remains LOCAL preinstalled StateDB.SetCode executed through ordinary EVM Call, not standard CREATE deployability. Fixed block/time1 and checkpoints are not mined blocks. Changed code/package requires fresh original startup; no old checkpoint migration occurred.

## Evidence

`evidence/java-evm/minecraft-entry/parent-function-interface/artifacts/navigable-map-interface-blocker.json`, `original-function-link-proof.json`, `all106-root-audit.json`, fresh raw4/raw150 gates/reopens, typed namespace/omission controls,44 canonical receipt hashes and q1 refusal. `rebuild.py` independently verifies the nine-file P42 baseline and actual106-entry root, then builds the corrected coordinator. Source-only baseline is preserved at `function-interface-source-base-p42/`; current source/artifacts at `function-interface-link/` label the worker record as pre-parent history.
