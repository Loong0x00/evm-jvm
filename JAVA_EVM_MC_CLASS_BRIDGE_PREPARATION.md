# Next preflight: EVM-decoded class bytes to the existing EVM JVM

Status: **PREPARATION ONLY**, no production class-loader freeze/acceptance.
DI0 accepted56848a1b1. Parent has now actually decoded original
net/minecraft/server/MinecraftServer.class inside EVM:33457 bytes,CRC verified,
5 EVM-created pages. See evidence/java-evm/di0/official-entry-56848a1b1/.
No Java instruction from Minecraft has executed; no EULA/listener/world/Done.

## Immediate dependency to measure

Connect verified EVM resource bytes to an already accepted in-EVM Java execution
entry point, initially on small TRUSTED GENERATED Java8 fixtures. Do not start by
implementing full Java ClassLoader/Java SE or by widening VFS/JVM quotas. The host
must stop supplying raw class bytes as execution authority after uploading the ZIP.
Name/root assertions are fine: EVM index/decode/read must actually produce the bytes
that the EVM JVM parses/executes. Test oracle JVM/direct runner is a separate path.

One Sol/high worker only, disposable preflight. Own ONLY
JAVA_EVM_MC_CLASS_BRIDGE_PREFLIGHT.md and evidence/java-evm/class-bridge/preflight/**
plus own ignored build/java-diff-mc-class-bridge-preflight-*/. No production edits,
accepted runtime/AS0/ZI0/DI0/VFS/core/consensus/opcode/gas/Make/global settings/push,
peer writes or spawning. No Fast/priority. Key code/logs/hash/reproducer tracked,
not /tmp-only. No official input/class execution or EULA/listener/server work.

Inspect actual accepted JVM/VFS0a ABI/state/entry limitations first. Propose the
smallest EVM wrapper or continuation adapter that can call it with class bytes
obtained from DI0 FINAL pages. Existing oversized LOCAL JVM installation is a
separate accepted mechanism: if needed, install ONLY its exact accepted pinned
engine in the clearly labeled test harness, unchanged. Do not claim EIP170 deployment
for that engine. All resource/controller/data/output pages remain ordinary CREATE;
no host SetCode for class/resource pages, runtime substitutions, host Java evaluator
or host inflater/catalogue. No changing accepted engine's callbacks/loader semantics.

Measurements/checks required:

1. Actual selected engine ABI/pins/quotas, caller/continuation ownership, class image
   and bootstrap framing. Identify whether direct nested EVM calls are possible,
   whether a separate EVM-owned input/checkpoint adapter is required, and exact
   current4-class/64KiB or other limits. Do not silently expand them.
2. A tiny genuine end-to-end prototype on a generated ZIP: AS0 -> ZI0 -> DI0 ->
   EVM-side resource read -> existing EVM JVM -> Java bytecodes -> observed result.
   The JVM's runtime call must receive the EVM-produced bytes, not a host copy of
   the fixture class. Two distinguishable classes/inputs must change guest results.
3. Generated Java8 oracle(s) may establish expected behavior only; no oracle output
   becomes execution input. At least one nontrivial loop/branch/calculation rather
   than only a literal return, plus a genuinely executed method call if supported.
4. Refuse wrong binding/name/unverified output before class execution; measure class
   image/name/declared-name mismatch/malformed byte failures with existing verifier
   behavior, rather than fabricate success. Caller roots are assertions, not imports.
5. If continuations needed, genuine repeated bounded EVM calls and q grouping/root/
   guest-result equivalence; checkpoint bytes are EVM-issued and never recovered
   from OOG traces. Clearly separate resource F, input/package binding and JVM
   continuation/trie roots. No Java outcome extracted from a failed EVM call.
6. Pinned solc0.8.30 opt200 viaIR Cancun metadataoff for any disposable wrapper;
   ordinary100Mgas/30s, labeled1B/120s boundary only, total20min/4GiB watchdog.
   Record real code/init/gas/state/call counts/wall/RSS and owned source/replay hashes.
7. Report concrete remaining gaps to original-server class loading/link/init: archive
   class identity vs Java binary name, bootstrap resolution, needed class/image/heap
   quotas, interpreter feature/class initialization frontier. Static evidence only
   where original bytes are concerned; not reachability or execution claims.

If existing ABI/ownership/caps prevent a bridge, preserve the real reproducer and
propose the smallest explicit next profile rather than patching the accepted engine.
Deliver a bounded report and reproducible actual evidence; parent independently
replays and freezes any production adapter only afterward. This is not acceptance
of a general loader, Minecraft class execution, or genuine Minecraft readiness.
