# P48 — parent-verified bounded EntrySet.toArray(T[])

## Accepted capability and boundary

The real HashMap EntrySet now implements the measured generic Collection.toArray(T[]) call in ordinary guest Java, for supplied arrays whose capacity is at least the real view size. It returns the SAME target, copies actual existing Node entries through the real iterator, writes exactly the required first unused null, and preserves the remaining tail. Null-array NPE and incompatible-component ASE are real JVM faults. No empty-input shortcut, fake element, snapshot node or replacement Minecraft code exists.

A shorter target is a valid API case outside this bounded profile: an unbound private native guard raw-refuses BEFORE any array writes. Component-preserving growth/reflection, no-arg toArray, stream/mutation and other unmeasured Collection algorithms remain unsupported, not fake Java errors or wrong-component Object[] allocations.

## Parent correction and exact build

Worker `94a8845c4a71f16bad322ea3572c1d79ab8a1f66` supplied generated direct EVM gates but no durable/coordinator proof. Parent did not accept it unchanged: adding an abstract Collection declaration made unsupported inherited calls on HashSet and related classes throw AbstractMethodError. A fresh real EVM probe committed javaKind11, which was preserved. Parent reproduced the old AbstractCollection image exactly, then added ONLY an unbound native typed-copy declaration in that common base. HashSet/EnumSet/ArrayList/COWAL/CLQ now raw-refuse; concrete EntrySet still overrides with the sole new copy behavior. No interpreter resolution or fault rule changed.

Parent independently rebuilt Java8 -g:none, full ordered images, solc, coordinator, canonical1B driver and separate authorized original driver. Only leaves53(Collection),55(AbstractCollection refusal guard),110(EntrySet) change. All other110 images, including Map40/Map.Entry94/HashMap100/Node104/iterator111/CME112, are exact. Still113 images; no count-width or quota expansion.

Root: `28a117d6b859fff966c517f49485e15df7db911f9ed1d077a8e7a5f6337f7413`.

- Engine429978B SHA256 `d45a84f99606d44480ef4830f9f04fe6d87dd6e0d527c9d0a69862fc7e3bb6d9`, Keccak `28a4336d0c9e1e5fe7e6e3fdc59635967ee8ead1ebca1a4d3275acabd2b60a15`.
- Coordinator5411B SHA256 `912bafd76875e7fc1277a31d33e1e3c4ae2305647a7f268beb03bdf2119c2faa`, authenticating that exact engine.
- Actual domains `MC-HASHMAP-ENTRY-SET-TYPED-TO-ARRAY-BOUNDED`; friendly milestone P48. Actual code/image/package commitments bind checkpoints.
- Native21/String12, eager heap, dispatch, codec, ABI/storage and quotas unchanged: arrays8192, objects4096, elements262144, handles12545, raw150/1063930B, CP2MiB, runtime-artifact1MiB, frames128, q65536/internal4096, reserve25M.

## Independent genuine EVM gates

Generated-only stock Java8 is a test oracle, never execution input. Interface-typed Collection tests verify empty/exact/oversized same-target reuse, tail-null/rest-tail preservation, null keys/values, real node identity/order, aliases after put/setValue, repeated copies, null-array NPE and typed String[] ASE.

- Small raw1 q7/q1:2570 JVM instructions,158.075s combined at canonical1B; peak70256906gas. Exact final machine/VFS/counters/heap and separate-process checkpoint/code/Head validation/reopen.
- Raw150 +113 =263 internal classes, q4096/q65536: separate2B after preserved measured1B shortage, peak1790354213gas,2.119s combined. Real CME index262 array metadata0x206 and distinct shallow clone survive exact outcome/heap/root checks and independent-process reopen. Coordinator uint8 remains a raw<=150 count, not internal263.
- Twelve fresh1B atomic controls: two short-target cases (including sentinel target), no-arg/add/equals, inherited unsupported copies on HashSet/ArrayList/COWAL/CLQ, and raw Collection/AbstractCollection/EntrySet replacements. All raw-refuse without publishing Head/root/checkpoint or substituting a Java exception.

Generated public watchdog30s is separate from outer1200s. Original runs use authorized uint64.max/60s. Heavy compilation/EVM runs stayed serial for host stability only. Initial parent javac missing-output-directory failure is retained; it preceded compilation and changed no guest/EVM behavior.

## Fresh unchanged original125 and coordinator integration

A new125-resource/889395B package through genuine authenticated AS0/ZI0/DI0 and the new coordinator passed Collection.toArray. The real cached EntrySet8257/class235 created actual iterator8258/class236, retained owner8250, and returned caller Map.Entry[]8251, rank1/length0. Original nonempty copying is NOT claimed; generated fixtures prove it independently.

**2224082 JVM instructions /128 internal steps**,44 canonical verified receipts, epoch44/lifecycle1. Checkpoint1285152B SHA256 `f837ca9d1a3d0458c5bc0d3e5f43442a53cdb2fdcfbf41a8fa41630e1d52ee73`. Discovery670.165s plus same-code/package precision642.186s. World `build/java-diff-mc-entry-array-original125-parent-p48/official`.

Next exact q1 missing **java/util/LinkedHashMap**, site4104/context0. An authenticated read-only EVM scan of original Guava Maps binding84/method12 proves newLinkedHashMap(): NEW atPC0 and genuine zero-argument constructor call atPC4. No full LinkedHashMap API is yet accepted.

All65536 sine raw bits remain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`; heap3570 objects/4682 arrays/106145 elements. Protected core/vm/core/state/params equal95665d570. No original host Java/ZIP/class parser, rewrite, injection, oracle input, terminal resumption or cross-code/package checkpoint migration. Oversized LOCAL SetCode preinstallation through ordinary EVM Call, NOT standard CREATE deployability. EVM gas/state/consensus/EIP170/EIP3860 unchanged; fixed block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-entry-set-to-array/artifacts/linked-hash-map-constructor-blocker.json`, all113 root audit, parent positive/high-index/refusal/reopen records, real original copy heap and44 ordered receipt hashes; `review/` preserves the rejected inherited-fault probe and original worker metadata.
