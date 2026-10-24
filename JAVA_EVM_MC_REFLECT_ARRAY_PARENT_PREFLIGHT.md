# P53 — independently verified one-dimensional reference Array.newInstance

## Scope and native inventory

The bootstrap-owned Java8 public `Array.newInstance(Class<?>,int):Object` wrapper forwards in ordinary guest Code to exact private static native `newArray(Class<?>,int)`. New Solidity-JVM binding22 allocates real rank1 reference arrays from canonical VM-owned component mirrors. Existing global1..21 and String-local12 behavior stay intact. Inventory22 is an explicit semantic extension, NOT a resource/gas/consensus increase or host precompile.

Only ordinary non-array reference classes/interfaces in the authenticated Program are admitted. Each call, including length0, creates a distinct real eager array with exact component metadata, null cells and normal casts/astore/ASE/clone/alias/checkpoint behavior. It neither creates component instances nor initializes their class. Null component yields genuine NPE before negative-length handling; a valid supported component with negative length yields genuine NegativeArraySizeException. Existing anewarray quota/fault handling is retained. Primitive/void/array component mirrors, multidimensional overload and reflection accessors remain raw refusals, not wrong-component Object[] results or invented Java exceptions.

No original-specific empty case or host Class/JAR/parser/allocator participates.

## Independent audit and isolated artifacts

Worker `18340fbd68086731fd5a5aac78c88ca57529eb1c` provided generated direct EVM evidence. Parent verified all9 base hashes, audited the full semantic delta, reproduced the477B Java8 class exactly (normal line/source metadata retained), and rebuilt engine/coordinator/Go/vet. Removing only the binding22 block reproduces the entire old executor text; validation/recognition additions are exact new-owner/private-static REF+INT->REF cases. Canonical mirror/name/loader validation and the array arena/quota machinery remain shared with accepted paths.

The worker retained all P52 engine/coordinator domain labels. Parent preserved those sources/logs, isolated all9 engine and4 coordinator domains, rebuilt the actual codehash authentication and reran fresh gates. Native allocator logic did not require a parent repair. Historical worker logs are not current-artifact acceptance.

All116 old class images/order remain exact; Array appends116,117 total. Actual historical parser slots105..109 are preserved by count-12..-8; no raw-count/index-width migration.

- Root: `20d06decae99c5a8cdd4ce6e674e81593a56025dc19b36445b140386488e47d0`.
- Engine435002B SHA256 `eadc25de896d01347ed8ff1ebda49ba47d734469dbf92e2ca4c66d4ed8d4454c`, Keccak `b94913eefc3e672fac01a1362ee4105f4f2e21be429ad3adb0430f0bdc89d8c2`.
- Coordinator5411B SHA256 `125735698a5db91c10b447b77e62a8b9061ce40ab58a6a17aca01f25ca5f0f5a`, authenticating that engine.
- Domains `MC-REFLECT-ARRAY-NEWINSTANCE-BOUNDED-1`; friendly milestone P53.
- ABI/storage/codec/geth rules and resource limits unchanged: arrays8192, objects4096, elements262144, array length65536, handles12545, raw150/1063930B, CP2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M.

## Independent genuine EVM gates

Generated-only stock Java8 is test oracle/build context, never execution input. Parent tests dynamic component arguments, Object/String/interface/private/abstract classes, distinct empty/nonempty arrays, actual stores and aliases, typed casts/ASE, shallow clone, null/negative/null-negative precedence and component non-initialization. A poison component remains uninitialized during allocation and only raises EIIE upon a later deliberate active use. Old Class.getName/asSubclass, System.arraycopy, EnumSet and actual bootstrap-tail identities remain tested.

- Small raw5 q7/q1:619 JVM instructions,60.855s combined at canonical1B; peak192142376gas. Exact machine/VFS/heap/counters and independent-process EVM checkpoint/code/Head reopen.
- Raw150 +117 =267 classes, q4096/q65536: separate4B after preserved measured1B/2B shortages,2.791s, peak2120837666gas. Actual ListIterator component264 produces typed array metadata0x208. Full decoded arrays/roots/counters and new-process reopen pass. This is not ordinary1B/2B success.
- At1B, length65536 creates one dense null array, checkpoint526913B; length65537 catches genuine OOM before array allocation. Element quota retains three real65536 arrays, then catches OOM on the fourth (196624 actual elements include mirror-name storage). No invented cap, hidden array or state continuation. These are length/element boundaries, not a fresh exhaustive8192-array/handle sweep.
- Four quota/EnumSet cases at q4096/q65536 all complete and eight authenticated checkpoints reopen in a separate process. The legacy harness's max3 report-arity check initially rejected8 requests; quota-only harness now requires EXACT8, retaining all code/CP/Head validations. Failure preserved.
- Seven fresh1B atomic controls raw-refuse primitive/array component literals, multidimensional overload, getLength, illegal direct private-native access, raw Array owner and raw Class replacement. The primitive/array-literal failures occur at existing unsupported mirror boundaries; no claim that those component kinds reach binding22.

Other preserved harness failures: candidate-only root helper rejected116 baseline; parent used the authenticated generic baseline helper. A private fixture's implicit constructor emitted a synthetic class; explicit package constructor fixed its count before current gates. A multiline Class materializer was missed by a single-line negative-fixture extractor; whitespace-only extractor correction and new output directory preceded EVM calls. No acceptance predicate or guest opcode was relaxed.

Generated public watchdog30s remains distinct from outer1200s; original uint64.max/60s is separately authorized. Heavy compiler/EVM stages ran serially for host stability only.

## Fresh unchanged original131

A new131-resource/917284B world through authenticated AS0/ZI0/DI0 and the actual coordinator completed reflective reference-array creation. Canonical mirror8273 names java.lang.Iterable, and binding22 created real array8276: rank1, metadata0x1da (component218), length0. The original wrapper/helper returned it and advanced to the next call. ew$b remains uninitialized while arguments are prepared; no Cartesian-product completion is claimed.

**2224329 JVM instructions /133 internal steps**,41 canonical successful receipts, epoch41/lifecycle1. Checkpoint1287819B SHA256 `1e82e770d6bc022ad4daafa5233b272cf6d530daa6bedecc99eb871f25224b8b`. Discovery1212.975s (non-missing failure localized through q1), then explicit same-package precision16.645s/reopen. World `build/java-diff-mc-reflect-array-original131-parent-p53/official`.

Next exact q1 CallError(4,51) is original ew.b(Class,Iterable), interface List.toArray(Object[]):Object[] on actual ArrayList8274/private size0, with new Iterable[]8276/length0 as target. ArrayList's inherited typed-copy guard remains unbound; no fake result is supplied.

All65536 sine raw bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`. No original host Java/ZIP/class parsing, rewriting, injection, oracle input, failed-state/terminal resumption or cross-code/package checkpoint migration. Protected core/vm/core/state/params equal95665d570. Oversized LOCAL SetCode preinstall through ordinary EVM Call, NOT standard CREATE deployability. Gas/state/consensus/EIP170/EIP3860 unchanged; block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-reflect-array/artifacts/array-list-typed-array-blocker.json`, all117 root audit, dynamic array/high-tail/Poison/mirror/fault/quota/EnumSet/refusal/reopen records and41 ordered original receipt hashes. Worker and parent failed attempts remain preserved.
