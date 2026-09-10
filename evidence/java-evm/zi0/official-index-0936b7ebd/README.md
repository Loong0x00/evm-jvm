# First real official1.12.2 JAR index in EVM — NOT Java execution

After ZI0 acceptance0936b7ebd, parent supplied the official server JAR as opaque
bytes to the accepted AS0+ZI0 transport. Unlike the earlier synthetic acceptance
fixtures, this run actually indexed the pinned original artifact in unmodified EVM.
It did NOT execute server Java, inflate entries, create a world/EULA, bind a listener,
or produce Minecraft readiness. An archive has been indexed, not launched.

Input30222121B, host transport SHA256
fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e.
The driver performs no host ZIP parsing/catalogue/extraction; Go only hashes raw
input, asserts page commitments, ABI-drives the EVM and persists state. Entry names
are lookup queries, never a supplied catalogue/offset map. EVM AS0 created all3690
pages, sealed the bytes; EVM ZI0 discovered20554 entries/2100796-byte CD and built
its index through322 scan calls. Total4017 per-call publications. Same-process
close/reopen retained final roots without CREATE; separate new-process behavior
was proven in acceptance tests, not re-labelled as occurring here.

External watchdog25.178s/126558208B sampled groupRSS, exit0/no limits. Ordinary
100M gas calls only: AS0CREATE611673;append6565590601 sum/max1830926;seal34194;
ZI0CREATE1935216;discover69092534;scans2407247789 sum/max8652013;finish46129.
Read-only view sum16324020 separately. These are sums, not one-call gas or op counts.

AS0 content commitment:
5c77ef7a2deb6df6ff07bf166ab9a1f0e8e31f577460fe4581cef8445dfd5ac9
ZI0 final index commitment:
4f339e8513dfbd294bd7dacf786ea7b6085c082304a1b2866a5e833c82a08f4e
Committed EVM trie root:
013595268acc3f632593eee005199151845bb38e5a01520fc7cfa8bedf843d8f
These are instance-bound EVM commitments; none is a whole-file EVM SHA256 proof.

Actual EVM lookup/packed metadata (parent compared returned fields with prior
static inventory only AFTER execution; none of these offsets was an input):

| query | ordinal | local header | data start | compressed | declared plain |
|---|---:|---:|---:|---:|---:|
|log4j2.xml|2940|2972204|2972244|459|1124|
|META-INF/log4j-provider.properties|6106|7060413|7060477|520|904|
|net/minecraft/server/MinecraftServer.class|3010|3026184|3026256|15798|33457|
|org/apache/logging/log4j/LogManager.class|5959|6860135|6860206|4282|11864|

All four are method8/flag0x0800. Method/CRC/plain size are metadata; compressed or
uncompressed class contents have not become Java execution evidence.

`driver.go.txt`, `report.json`, `run.log`, `watchdog.json` are the durable evidence.
The official JAR and its byte-bearing code/trie database are deliberately NOT Git
fixtures. Local store is in ignored build/java-diff-mc-zi0-official-index/state/;
it can be reconstructed from the pinned private input, accepted code and driver.
The driver refuses an existing store rather than wiping or reusing it. To rerun,
choose a NEW workspace/report path in a copied driver; preserve this capture.
No public push or distribution of server bytes occurred.
