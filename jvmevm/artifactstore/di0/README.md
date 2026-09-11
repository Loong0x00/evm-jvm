# MC-DI0 opaque resource transport

Bounded ZIP method0/raw-DEFLATE method8 decoding takes place entirely in the
`DI0Resource` EVM contract, using accepted AS0 byte storage and ZI0 indexing.
Go only transports opaque input/calls and persists EVM state. See
`JAVA_EVM_MC_DI0_PLAN.md` and the parent review for scope/acceptance status.

A session owns one AS0 upload, one ZI0 index and one decoder on the same trie:

1. `NewMemory(owner,length)` or `Open(directory,owner,length)` ordinarily CREATEs
   only AS0. Reopen never CREATEs; inspect `Creation()` for its initial receipt.
2. `Append`, `Seal`, then separate `CreateIndex`, `DiscoverIndex`, `ScanIndex`,
   `FinishIndex` calls. Raw names remain opaque; `Entry`/`Lookup` are EVM queries.
3. `CreateDecoder(indexRoot,rawName,gas)`, then `Step(work,units,gas)` while phase1.
   **units1..128 is an upper bound**, not a promised increment. Use actual EVM Head
   progress; the EVM yields after positive work with less than25M remaining gas.
4. After CRC/length verification, `Publish(page,rolling,1,gas)` issues one EVM-created
   page per call. Only FINAL phase4 permits `Read`/`Page`. Empty output auto-finalizes.

DI0 resource bounds:262144B plaintext,32768 lookback,32-byte copy action,
8192B pages<=32,4096B read. These do not expand JVM/VFS/AS0 quotas. Ordinary calls
100Mgas; explicitly labeled boundary allowance<=1B. No opcode/core override.

`Head.StateRoot` is the trie root; `Head.Decoder.FinalRoot` is the resource
commitment. All successful mutations commit/reload; disk publication synchronizes
trie+code, writes/fsyncs a unique manifest temp, renames and fsyncs its directory.
Prepublication failure restores the last published root; ambiguous postrename
failure poisons the session until exact reopen. EVM errors expose gas/revert only;
publication errors expose gas only. No error receipt contains a success root/page.

The separate marker is `JVMEVM-MC-DI0-DISK-STORE-1\n`. Foreign/incomplete namespaces
are not adopted. Never use ZIP/class parsers, host inflaters/Huffman/CRC evaluators
or SetCode in this transport. Such helpers in `_test.go` are generated-fixture
oracles only. Final EVM page code is the output authority, never a Go decoded map.

```
make java-mc-di0-test
make java-mc-di0-demo  # generated resource commitment fixture, NOT a Minecraft demo
```

A DI0 runtime instance may share a FINAL index with other instances in future
loader integration. The current single-decoder session route is a proof scaffold,
not a claim of ClassLoader/Java execution, a world, listener, EULA or genuine Done.
