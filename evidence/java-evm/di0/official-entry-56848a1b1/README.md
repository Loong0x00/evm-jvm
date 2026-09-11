# Original MinecraftServer.class genuinely decoded by EVM

Execution base: accepted DI0 commit56848a1b1. This is **resource/class BYTES only**,
not JVM class loading, Java method execution, Minecraft, EULA, listener, world or Done.
No server JAR or decoded class payload is committed here. The ignored EVM database
contains byte-bearing state and is reconstructible from the pinned original input.

Parent driver accepts only the original1.12.2 server:30222121B,
SHA1 886945bfb2b978778c3a0288fd7fab09d315b25f,
SHA256 fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e.
Host hashing checks opaque input transport integrity, not guest execution authority.
Host code has no ZIP parser, inflater, Huffman/CRC evaluator or decoded page installer.
AS0/ZI0/DI0 derive metadata and output inside unchanged EVM; only the raw query name
`net/minecraft/server/MinecraftServer.class` is supplied, never offsets or plaintext.

Actual EVM results:3690 input pages,20554 indexed entries,2100796B directory;
compressed range starts3026256,15798 compressed bytes ->33457 verified plaintext
bytes,16090 bounded actions,5 EVM-created output pages,CRC32 3887236386.
Plain SHA256 observed AFTER final EVM reads:
246e7916fde4261e776c4beb17c5b7e84a80948c5ce60abf1e8011ca88288b0f.
CAFEBABE observed, not interpreted/executed. Resource root:
1a7f79cd7638d79c9e39738fc6abeaf8ee19cce4f71cf33b8269d99e58a2e029;
trie root f169df710c3d686aba09676143ca9bbc6c9d54a2a5bf308200c2e2705ef15460.

4149 successful mutations including initial AS0 CREATE (4017 upload/index pipeline,
then decoder CREATE+126steps+5output publications). Ordinary100M per mutation;
max mutation69092534gas, max decode step5060183gas, mutation total9433550706gas acrosscalls (Head/query-view gas is not included).
Max measured mutation103ms. Full readback followed by same-process FINAL reopen
with no CREATE and unchanged resource/trie roots. Not a new-process official run;
new-process semantics were tested separately with generated fixtures at acceptance.

Actual watchdog88.570s/144207872B sampled peak groupRSS,exit0/no20min4GiB limit.
Driver reports its own88.543s. Namespace owner differs from the earlier ZI0 official
index proof, so input/index commitments are not expected to be identical to it.

Reproduce from repository root into NEW ignored paths (driver refuses existing state):

```
mkdir -p build/java-diff-di0-official-UNIQUE
cp evidence/java-evm/di0/official-entry-56848a1b1/main.go.txt build/java-diff-di0-official-UNIQUE/main.go
go build -trimpath -o build/java-diff-di0-official-UNIQUE/proof build/java-diff-di0-official-UNIQUE/main.go
python3 evidence/java-evm/watchdog.py build/java-diff-di0-official-UNIQUE/report.json build/java-diff-di0-official-UNIQUE/watchdog.json \
 build/java-diff-di0-official-UNIQUE/proof /PATH/TO/PINNED/minecraft_server.1.12.2.jar \
 build/java-diff-di0-official-UNIQUE/state net/minecraft/server/MinecraftServer.class
```

No original data is extracted by a host ZIP utility or used as test-runtime authority.
The driver may query another name, but no other official decoded-entry result is
claimed by this capture. Java class loading/execution remains the next dependency.
