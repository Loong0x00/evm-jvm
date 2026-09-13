# Parent System.arraycopy preflight

**Parent-verified narrow COPY, not a full System/JVM/Session or Minecraft startup
acceptance.** Source and evidence:
`evidence/java-evm/minecraft-entry/parent-f780f1a13/`.

The user explicitly authorized a push. Only the previously reviewed main was
pushed: remote `origin/java-on-evm` independently confirmed
`1e4027b9b48fd7b63103aa27e4fe911af513b928`, replacing `31e40ad6f`.
Subsequent integration/repair remains local; no standing publication permission.

## Independently reproduced candidate failure

Worker `fd614c645` / `f780f1a13` was integrated locally as `1747c4925` /
`0e60ebab6`, not accepted from its report. Parent rebuilt the candidate from
Solidity alone and matched the complete engine/coordinator compiler artifacts.
Fresh q1/q7/direct worlds reproduced:

* q1: epoch176 / Java176 / internal3, **RUNNING**, main PC106, five operands.
* q7: epoch25 / Java175 / internal3, **RUNNING**, main PC105, four operands.
* Both next resumes and direct q4096 panic `0x32`, leaving published roots
  unchanged. Host `final-reopened` does not mean guest VOID.
* These are differing prefix boundaries before the same failure, not terminal
  quantum divergence. The worker's VOID claim was false.
* `_loadNativeCallee` removed `s.argumentCount = 1` without assigning the parsed
  count. Invocation used `base = sp` rather than `sp - 5` and indexed outside
  the operand-stack allocation on the first arraycopy.
* The worker driver still appends read/PID histories despite claiming bounded
  metadata. Parent uses the actual prior `executed_bounded_driver.go.txt` and
  retains its 32768B Head limit. No old-Head edit/rescue or quota increase.

## Narrow repair and pins

`rebuild.py` sets `s.argumentCount = s.argumentKinds.length`, preserving one
argument for prior FP bit intrinsics and five for arraycopy. Other changes are
isolated identities and resulting pins. The implementation otherwise remains
worker source: bounded overlap-safe copying, distinct primitive leaves/raw bits,
reference component checks and genuine partial-prefix ArrayStoreException.

* Source-only solc0.8.30, optimizer200, viaIR, Cancun, metadata off.
* LOCAL initial-state engine, **not CREATE/standard-chain deployment**:
  `0x4d434152524159434f5059504152454e54000001`.
* Domain: `MC-ARRAYCOPY-PARENT1`; old-code checkpoints are incompatible.
* Engine **314365B**, SHA256
  `7ccbbc5da13ebc7a3eddf46fd76061e8fd4ee8f070705c387a23c884a42570f7`, Keccak
  `0325b00519b2213c8baeda0b1246ac03852ae38e97ef2c4301f48224fb15d9df`.
* Ordinary-CREATE coordinator **3547B**, Keccak
  `2936a42058eca016ad73933c1485d1e4d16da13d1020b4d2aeb3cea7bf9e3a39`.
* All 44 prior embedded bootstraps are byte-identical; System is appended at44.
  Generated platform sources independently reproduce all pinned images.
* Experimental16/262144, CP4096, Code65535, heap/VFS/frames/1MiB checkpoints,
  100M gas/30s calls, 25M reserve and 320KiB engine limit unchanged.

## Generated independent results

| Fixture | Java/internal | q1/q7/direct epochs | Result |
|---|---:|---:|---|
| worker ArraycopyMain | 650/9 | 650/93/1 | VOID, static sentinel4107 |
| parent EdgeMain | 310/15 | 310/45/1 | VOID, static sentinel0x1234 |

Within each fixture all three terminal machine roots and opaque checkpoint tails
are identical. Direct gas is respectively **31946639** and **19160066**, with no
rescue. Fresh-process reopen checks pass. Java8 TEST oracles execute the generated
fixtures only. Tests cover both reference overlap directions, aliases/distinct
arrays, real Marker interface arrays, actual exact ends/zero length, null/type/
bounds/overflow precedence, eight distinct primitive kinds including raw NaN and
signed-zero bits, partial reference-copy effects and nested array components.

Independent verification re-encodes canonical nested return ABI and checks events,
checkpoint SHA/Keccak, counter chains, pinned identity and actual DI0 read ranges
for **1100** generated successful receipts. Six deliberately corrupted TEST
receipts (ABI/event/checkpoint/counter/pin/lifecycle) reject; control passes.
This is not a broad Session/CAS or unrecorded phase-I/O acceptance.

Candidate rebuild/reproduction + repaired rebuild/smokes: **427.352815s**, sampled
process-group peak **889974784B**, exit0. Follow-up bootstrap/edges/original gate
stopped at the old observer's512-slice assertion: **173.010797s/157851648B**, exit1;
this failure is preserved and is not a guest refusal. Subsequent observation
batches retain runtime limits, stop normally as RUNNING at the same512 boundary,
and reopen the exact same-code checkpoint. No timeout process-group escape.

## Untouched original JAR progression

All original input/resource/class processing remains EVM AS0/ZI0/DI0; no host
Java/ZIP/class execution authority and no raw-class or decoded-page injection.

1. Original13,184522B/54 actual DI0 fragments, q1 reaches **1671 Java/8 internal**.
   Earlier System.arraycopy at original Log4jMarker.setParents PC29 is passed;
   original AbstractLogger initializer reaches PC110. Last successful checkpoint:
   **8299B**, SHA256
   `4ea8ad5ea3f0a43d9f58363ec4b30d722213368f88d88a4d887e2376eb2294e7`, root
   `a4bf204c6be4a261a1224f4dac780c3959e5d3adf470c1f5c0198b70ebcedb51`,
   gas67304838. Next actual refusal:
   `MCEntryMissingClass(4108,110,org/apache/logging/log4j/message/ReusableMessageFactory)`,
   gas53037998. Additional same-code observation gate594.234276s/143982592B.
2. Fresh original13 q7 reaches epoch238/Java1666, then the same missing class.
   **All238 aligned successful q7 checkpoint tails and machine roots match q1**.
   Gate85.555215s/152342528B. Differing last prefix counts are not divergence.
3. Add genuine ReusableMessageFactory, MessageFactory2 and MessageFactory:
   original16 = **195571B/59 DI0 fragments**. Fresh q7 reaches epoch238/Java1666/8I.
   Last checkpoint **8333B**, SHA256
   `46c511bcc27d4d44389a3b2423298cecaa76c7fe900bbb18269421193fc06efe`, root
   `e130b666ba74caf4cb43127a29146b5a1693daf975f8b7a5258ed04311807c63`, gas70238232.
   Next actual refusal is now
   `MCEntryMissingClass(4108,113,org/apache/logging/log4j/message/ParameterizedMessageFactory)`,
   gas57868100. Gate88.180283s/157327360B. The failing slice does not publish its
   intermediate class literal or other effects; no failed-trace recovery.

Across the three original worlds, **2147** successful receipts independently
verify; combined with generated worlds, **3247**. Static TEST-only `javap` excerpts
explain actual missing owners and their mandatory hierarchy, never execute guest
branches or supply decoded execution input. ParameterizedMessageFactory extends
AbstractMessageFactory: retaining the current required bindings needs at least18
original images, exceeding this COPY's16 limit. See the separate class-count
preparation; this arraycopy profile has not silently raised that cap.

Main-body, EULA, listener, world generation and genuine `Done` **have not run**.
Counters include platform Java and initialization dispatch. Accepted sources,
ABIs, quotas and artifacts remain unchanged. Parent archive omits original
JAR/class/resource-page/LevelDB payloads; public checkpoints contain mutable
state/frame metadata, not original class images. Historical worker evidence is
unaccepted and distinct from the parent metadata-only archive.
