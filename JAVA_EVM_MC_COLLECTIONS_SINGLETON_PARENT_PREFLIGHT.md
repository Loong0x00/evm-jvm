# P55 — independently verified true Collections.singletonList

## Accepted capability

The ordinary generic Collections.singletonList(Object):List factory creates a real one-element holder, including for null or a zero-length array passed as ONE object. size1 and isEmpty=false are truthful structural invariants. Every iterator is fresh with independent availability state: true once, next returns the SAME stored element, false after consumption, then genuine NSEE. An array element is neither flattened nor confused with an empty list.

The list is immutable within this bounded profile. add explicitly raw-refuses rather than falling through to AME; inherited content equality/hash/typed-copy and other unimplemented APIs remain raw refusals. get/contains/indexed mutation/full Collections or serialization behavior are not claimed. Parent corrected the new helper to implement Java8's existing RandomAccess and Serializable markers after a real EVM probe disproved the worker's returned type flags; stock-Java8 header and failed guest evidence are preserved.

## Pinned compiler cliff and exact config commitment

Worker `73a559a89acd6e598fcfb749d6acc8a034ff5773` includes the correct120-image assembly. A wrong119-image variant compiled but overwrote old slots; it remains failed evidence and no checkpoint from it is resumed. Correct120 hit solc0.8.30 viaIR stack depth in _configRoot. Parent measured a minimal source-only fix: store the original13 config fields in an internal memory struct, ABI-encode that ONE dynamic struct, then hash DATA after its leading32-byte ABI offset. Field order/types and the legacy uint32[11] limits remain exact. Unnecessary startMain/resumeMain/_commit/envelope rewrites were reverted to baseline.

No ABI/wire change is inferred merely from compilation:512 generated host ABI vectors (dynamic strings including NUL/UTF8, signed-int32 extrema and variable arrays) prove structEncoded[32:] == originalFlatTuple. Parent additionally compares actual COMPILED EVM config roots to independent original13-field flat ABI encodings for all fresh singleton schedules and the original-server checkpoint. The original case's608-byte preimage hashes identically. Config-root/entrypoint semantics, external ABI and storage layout are preserved; no gas-speedup claim.

## Independent build and image commitments

Parent verified all15 source-base hashes, compiled actual Java8 images, rebuilt pinned solc/coordinator/Go/vet, and audited source deltas. All117 prior image bytes/order are exact; new utility/list/iterator append117/118/119,120 total. Actual parser slots105..109 remain count-15..-11; ReflectArray116 moves to count-4, not over a new helper. Raw helper names are reserved.

- Root `08d8a3019da084226f5d4c0e60d8f0f450bc0421aa7f04da031314e05070252a`.
- Engine441562B SHA256 `f0506373cdad2daeb97216629f949653edefcacc9ec0471e8f8a14dafe10f348`, Keccak `43060afcfcb29780be2a385aad90bde40aa8eba9008768e414f97d369e611539`.
- Coordinator5411B SHA256 `2fa5eff126cf957f772c4fb3e39847c395e2c2b08148a07414e62effb1128688`, authenticating that engine.
- Actual9 engine/4 coordinator profile domains `MC-COLLECTIONS-SINGLETON-LIST-BOUNDED-1`.
- Native1..22/String12, bytecode execution, heap/codec, ABI/storage and quotas unchanged: arrays8192, objects4096, elements262144, length65536, handles12545, raw150/1063930B, CP2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M.

## Fresh parent genuine EVM evidence

Generated-only stock Java8 is test oracle/build context, never execution input. Parent tests arbitrary object/null/zero-array elements, size/empty/type markers, new factory instances, two independent iterators, identity/null return/NSEE, reflected arrays as elements and retained ArrayList/HashMap typed-copy/tail behavior.

- Raw1 q7/q1:647 JVM instructions,34.277s combined at canonical1B; peak70955593gas. Exact machine/VFS/heap/counters and separate-process checkpoint/code/Head reopen.
- Raw150 +120 =270 classes, q4096/q65536:647 JVM instructions,1.556s at the SAME1B; peak728615561gas. Actual list268/iterator269 private fields and null/non-null elements survive u16 wire audit/reopen. Coordinator uint8 remains RAW<=150, not internal270.
- Eleven fresh1B atomic controls retain add/content equality/hash/typed/noarg copy/get/iterator.remove/Collections.emptyList and all3 new raw-owner refusals. No fake mutation return, AME or UOE substitution.
- Current native22/P53 reference-array/Poison-no-init/NPE-negative/ASE/clone/Class.getName/asSubclass/arraycopy/old-tail controls are rerun at q4096/q65536 and1B,619 JVM instructions, peak584744625gas, with fresh-process reopen and compiled-flat-config checks.

Generated per-call30s is separate from outer1200s. Original uint64.max/60s remains separately authorized. Builds/EVM runs stayed serial for host stability only; all compiler failures, wrong layout worlds and broader rejected refactor experiments are preserved.

## Fresh unchanged original136

A new136-resource/945385B world through authenticated AS0/ZI0/DI0 and the coordinator returned a real SingletonList8281/class254 storing actual Object[]8280/length0. Real iterator8282/class255 stores the SAME element and availability=true; the tuple has not yet been consumed when the next resource blocks. Cartesian product results are not claimed.

**2224516 JVM instructions /136 internal steps**,40 canonical successful receipts, epoch40/lifecycle1. Checkpoint1288033B SHA256 `5e4d012887bfcb670490fc9e16a6d117076a28e95a7d8e67bc82a014e492b3c7`. Discovery691.682s plus same-code/package precision526.977s. World `build/java-diff-mc-singleton-list-original136-parent-p55/official`.

Next exact q1 missing original **com/google/common/collect/Iterators$7**, site4104/context5 in original Iterators.transform. All65536 sine bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

No original host Java/ZIP/class parsing, rewriting, injection, oracle input, failed-state/terminal resumption or cross-code/package checkpoint migration. Protected core/vm/core/state/params equal95665d570. Oversized LOCAL SetCode preinstall through ordinary EVM Call, NOT standard CREATE deployability. Gas/state/consensus/EIP170/EIP3860 unchanged; block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-collections-singleton/artifacts/iterators-transform-resource-blocker.json`, all120 root audit, private singleton state, compiled-flat-config proofs, marker correction, parent gates/refusals/reopens and40 ordered original receipt hashes. `compiler-stack-relief/` preserves validated narrow source and512-vector ABI proof.
