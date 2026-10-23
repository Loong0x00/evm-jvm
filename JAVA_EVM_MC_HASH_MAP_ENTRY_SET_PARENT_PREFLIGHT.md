# P47 — parent-corrected live HashMap.entrySet

## Accepted scope and rejected attempts

`HashMap.entrySet()` now caches a real ordinary guest EntrySet backed by the map, not an always-empty result or snapshot. View size/isEmpty read real map fields; iterators traverse the real Node[] buckets/chains and return existing Node entries. JDK8 next() checks structural modCount before exhaustion, throwing genuine ConcurrentModificationException or NoSuchElementException. hasNext does not fail fast. Nonstructural replacement and Node.setValue preserve live aliasing. Unimplemented view operations explicitly raw-refuse; no remove/clear/toArray/reflection expansion is claimed.

Worker `0c7d3d510110704f9d4d7770ae6a39d6c82feb40` supplied generated-only direct EVM evidence but no coordinator/persistent reopen proof. Parent did not accept it unchanged:

1. A real fresh EVM raw Set.add(Object) probe exposed a compiler bridge that threw ClassCastException before the unbound-native refusal. Stock Java8 throws UnsupportedOperationException. Parent preserved the terminal evidence and corrected the private view to generic EntrySet<E>, so add(E) erases directly to native add(Object), without a casting bridge. An explicit package constructor also removes the unused synthetic HashMap$1 dependency. No interpreter dispatch/native code changed.
2. The first full original replay still refused invokeinterface Map.entrySet at the same PC: the existing bounded Map interface had no entrySet declaration. Concrete HashMap-only tests were insufficient. Parent preserved that entire failed world/build, appended the proper abstract interface declaration, and changed independent generated fixtures to call through Map. A second fresh original start passed it. No old checkpoint continued across code.

## Exact build

Parent independently rebuilt all used Java8 images with javac -g:none and all Solidity artifacts. Only old leaves40(Map declaration) and100(HashMap) change; all other108 prior image bytes/order, including Node104, remain exact. Three genuine helpers append110/111/112: EntrySet, EntryIterator and minimal no-arg ConcurrentModificationException. Map's nested Entry declaration is compile-time context only; its independently accepted engine image remains unchanged.

113-image root: `f17b95bad49e93149b028bcc14c1df26926ec7916494d3faf1b787d590457ee2`.

- Engine429415B SHA256 `db0b3a5ed75c268a3d52d4b9b0c21766f1bba186a5d6d8ce3ece0ea9e0297e22`, Keccak `c2fe549f931dd213b1dc8458251d657b587c91fd916170834a544dc0e6838718`.
- Coordinator5411B SHA256 `7af53ef47330e61853ab4f09709a8f1ee851052ea3ae56ec648fba517030ff96`, authenticating that exact engine.
- Actual domains `MC-HASHMAP-ENTRY-SET-BOUNDED-P47`; actual image/code/package commitments, never friendly labels, bind continuations.
- put/spread/resize/treeification refusal and Node Java source remain unchanged. All native21/String12, ABI/storage/codec/eager heap/dispatch and quotas fixed: arrays8192, objects4096, elements262144, handles12545, raw150/1063930B, CP2MiB, runtime-artifact1MiB, frames128, q65536/internal4096, reserve25M.

## Independent genuine EVM verification

Parent fixtures compile/run against stock Java8 as generated-only test oracles, never execution inputs. Actual new-artifact geth-EVM tests cover interface-typed entrySet, repeated cache identity, cross-map isolation, empty-to-populated view, null keys/values, real collisions, key equality replacement preserving the original key, entry.setValue/put aliases, legal nonstructural iteration, empty/exhausted iterator NSEE, and structural CME precedence.

- Small raw2 q7/q1:2144 JVM instructions;130.796s combined, canonical1B; peak66128725gas. Exact final machine/VFS/counters/heap and separate-process EVM checkpoint/code/Head validation/reopen.
- Raw150 +113 bootstrap =263 internal classes, q4096/q65536; separately2B after preserved1B shortage; peak1473126276gas. Real CME[] index262 metadata0x206 and a distinct eager shallow clone survive exact comparison and new-process reopen. Coordinator uint8 still counts <=150 raw resources, not263 internal classes; no wire-width migration.
- Independent resize map:41 actual entries, table growth and live iterator,10164 JVM instructions, q4096/q65536, separately4B after preserved1B/2B shortages; peak3101551494gas. Separate-process reopen passes. An earlier resize reopen report classifier rejected a parent case after EVM validation; preserved and corrected only the diagnostic summary branch. Fresh v2 gates pass unchanged validation.
- Eight fresh1B atomic controls: unsupported equals, raw Object add, clear, iterator.remove and reserved raw HashMap/EntrySet/EntryIterator/CME replacements. No head/root/checkpoint publication on refusal, no substitute Java error.

Generated public watchdog30s remains distinct from outer1200s. Original replay uses separately authorized uint64.max/60s. Heavy compilers/EVM runs were serial for host stability only.

## Genuine original progress and coordinator integration

A fresh unchanged original124/870262B package through authenticated AS0/ZI0/DI0 and the new coordinator/engine genuinely returned entrySet through Map. Committed HashMap8250/class224 caches EntrySet8257/class234, whose actual owner field points back to8250. Original iterator invocation is not claimed; generated tests independently prove iteration.

**2223979 JVM instructions /128 internal steps**,45 canonically verified successful receipts, epoch45/lifecycle1. Checkpoint1285526B SHA256 `36ec4e7843fecb4248e5476fde3c908739a66cfb9debf89cedeba7538cb0ccfa`. Discovery670.617s plus same-code/package precision665.412s. World `build/java-diff-mc-entry-set-original124-parent-p47-v2/official`.

Next exact q1 missing original **com/google/common/collect/Iterables**, site4107/context4. Heap3569 objects/4682 arrays/106145 elements. All65536 sine bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

No original host Java/ZIP/class parsing, rewrite, injection, oracle input, terminal resumption or cross-code/package checkpoint migration. Protected geth core/vm/core/state/params equal base95665d570. Oversized engine is LOCAL StateDB.SetCode preinstallation through ordinary EVM Call, not standard CREATE deployability. Gas/consensus/EIP170/EIP3860 unchanged; block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-hash-map-entry-set/artifacts/iterables-resource-blocker.json`, all113 root audit, high-index arrays, genuine cached-view heap proof, small/wide/resize/reopen/refusal records and45 ordered original receipt hashes. `review/` and old build/world directories retain both rejected source/execution attempts.
