# Marker-map COPY: independent replay and original arraycopy frontier

Narrow MC-first COPY verified for the exercised paths, not full collections/JVM
or accepted-profile promotion. Worker b11879cae/bb5074e3e/25b1f35a0 integrated as
85dc04e4b/dfbff66f6/4eecb16e7. Original MC and bundled Log4j remain unchanged.

## Independent build and actual transport limit found

Parent source-only solc0.8.30/opt200/viaIR/Cancun/metadataoff rebuild exactly
matches engine310375B SHA256df1418eae9dbdad7fe455ea6b8d3d1270be20527f84aa18837b80351985c2f70,
Keccak edc205611814164dea1c67b9c62f5de9ba5ad39e6126a87720fcf1323a238c30;
coordinator3547B Keccak213d900ca684872adf26d842e321ea11301256486fd7a25c7c8d11161120a25f.
LOCAL engine0x4d434d41524b45524d4150000000000000000001, not ordinary CREATE;
controller/resources/pages ordinary CREATE.44 bootstraps,16/262144 COPY only.
Build201.581895s/887308288B sampled group RSS. Other limits remain unchanged.

The first independent q1 map replay actually reached epoch1291, then failed because
its cumulative read-size history inflated Head to32780 bytes above the existing
32768-byte read bound. It had published a Head it could no longer reopen. Raw
failure/Head/source preserved, not rescued by changing that Head or raising limits.

Parent `bound_metadata.py` fixes only this owned Go COPY: full read fragments and
process histories remain external per-call/per-process receipts; Head retains
bounded scalar read counts and the current process ID, not unbounded arrays. A
prepublication size check enforces the SAME32768B limit. No EVM, guest heap, CP,
gas or Solidity cap change. New Go store marker separates the corrected format.
Fresh same-code map q1/q7 run now succeeds at1397 Java/9 internal,1397/200 epochs,
identical machine root and opaque terminal payload; independent Java8 TEST oracle
passes.65.168333s/160714752B. Directq4096 retains actual LC0ControlError7 ordinary
reserve refusal, not OOG or1B rescue. Map clear/growth extreme-OOM and complete
ConcurrentHashMap/thread semantics are not claimed by this small implementation.

## Actual original server progression

All original worlds use opaque unchanged1.12.2 JAR30222121B SHA256
fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e.
EVM AS0/ZI0/DI0 parse/decompress/CRC/publish/select every class. No host Java or
ZIP/class evaluator, raw-class/page injection, logging replacement or trace recovery.

1. Ten original bindings now reach **54 Java steps**, passing CHM construction and
   map use. Next actual missing original type is MarkerManager$Log4jMarker at
   site4104/PC21; gas38659786. Parent adds it and Marker from the SAME JAR.
2. Twelve bindings reach54 again, then EVM names the remaining hierarchy interface
   StringBuilderFormattable (site4098, owner class index10, not PC10). Parent adds
   that exact JAR entry. Twelve-binding gate41.602655s/157036544B.
3. Thirteen original images total **184522B**,54 successful DI0 return fragments
   per Java slice. Execution commits **epoch364/Java364/internal8**. This includes
   ordinary Java platform bootstrap execution and original initialization; it is
   NOT364 instructions of main's body. Root main frame remains unentered.
   Last successful call50598767gas;6431-byte checkpoint SHA256
   `1744ef6bf7420589df53022f639977db5dda10bc84cc8c9882c06f933dc7b2ed`, Keccak
   `e6e65f690a9bea30466555d24c7f98af60bafaad00c317e5d99fd20c14228dbb`.
   Independent hash/event/pin/read-range checks and fresh EVM Head reopen pass.
   Thirteen-binding input-to-refusal gate111.652983s/155336704B.

Next actual failure: **MCEntryMissingClass(4107,29,java/lang/System)**,
43618173gas. Successful CP shows original Log4jMarker.setParents atPC29 with5
arguments on stack, original AbstractLogger initializer suspended atPC28. Static
TEST-only javap identifies the exact required member:
`System.arraycopy(Object,int,Object,int,int)V`. This is no longer a guessed
platform expansion. Add only that array-copy substrate next.

No original main-body/EULA/listener/world/Done claim; no push. Accepted4/65536 and
core remain unchanged. Parent artifacts under minecraft-entry/parent-25b1f35a0
retain source recipes, generated oracles/receipts, raw metadata-limit failure and
original metadata/checkpoints. No official JAR/class/resource-page/LevelDB payload
is archived. Read-only CP frame diagnostics bound expanded to60 to match this
COPY's possible16+44 classes; this is not an execution quota change.
