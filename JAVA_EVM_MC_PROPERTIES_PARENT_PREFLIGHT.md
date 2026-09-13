# Parent Properties recovery / preflight

**Parent-verified narrow Properties COPY; original startup is now gas-blocked.**
Not full Properties/Hashtable/Dictionary/JVM/Session or Minecraft startup acceptance.
Evidence: `evidence/java-evm/minecraft-entry/parent-c24d374bc/`.

## Recovery and independently reproduced repair

Worker WebSocket stop left a clean worktree with5998b3d81,35433e305,bfc989092,
c24d374bc, no active processes. Parent recovered them locally as aa07cffe3,
6ec5def48,3d6584cd7,b035397d0. Worker completion/interruption was not acceptance.

Source-only candidate bootstrap/engine/coordinator builds match complete captured
artifacts. Parent found a real dispatch difference: owned getProperty called get
virtually, whereas Java8 calls Hashtable.get with invokespecial. Generated
OverrideProbe passes Java8 TEST oracle but candidate EVM throws ArithmeticException
from its counter assertion:181J/6I, lifecycle/outcome3, gets=1/puts=1/done=0.
The initial parent assertion mistakenly expected javaKind3; registry source shows
ArithmeticException is1. This **parent test error** and its198.882764s/898940928B
failed gate are preserved, including exact first script. Corrected fresh replay
confirms the same genuine guest failure and canonical receipt chain.

The only guest semantic repair is `Object value = super.get(key);`. setProperty
keeps virtual put; defaults keep virtual getProperty. Both are discriminated by
the parent subclass fixture. No original Minecraft/Log4j class is altered.

## New repaired identity and limits

* Compiler solc0.8.30+commit.73712a01.Emscripten.clang, optimizer200, viaIR,
  Cancun, metadata off; bootstrap sources rebuilt with pinned Java8 javac.
* LOCAL initial-state-only engine, **not ordinary CREATE**:
  `0x4d4350524f50455254494553504152454e540001`; domain `MC-PROPERTIES-PARENT1`.
* Engine321590B, SHA256
  `877f35a4ac4092a7c65ab5071104413e4579ced0b69a172852db77d772aee1bb`, Keccak
  `eb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7`.
* Ordinary-CREATE coordinator3547B, Keccak
  `4ac62a3ecc1612110cbc97779ebf760d101a33f1c85ddfb03c75d1b5478f2bae`.
* Prior45 bootstrap byte images/order unchanged; Dictionary/Hashtable/Properties
  append at45..47. Proper inheritance and real guest Object[] storage/growth,
  virtual equality, defaults/type/null/prior-value behavior; not a complete Java
  SE hash table, concurrency implementation or property-file parser.
*24/262144, CP4096/Code65535, heap/VFS/frames,1MiB CP,32768B Head,320KiB engine,
  ordinary100M/30s/25M reserve remain unchanged. No cross-code checkpoints.

## Fresh generated proof

| fixture | Java/internal | q1/q7/direct epochs | result |
|---|---:|---:|---|
| parent override/default dispatch |323/5|323/47/1|VOID, sentinel412|
| construction/Class/arraycopy |73/4|73/11/1|VOID|
| storage/default/type/alias/grow/remove/NPE |2859/9|2859/409/refusal|sliced VOID|

Within each successful fixture, machine roots and opaque terminal tails agree.
Direct large-storage run preserves ordinary LC0ControlError7, with no rescue.
All three caller-supplied Dictionary/Hashtable/Properties overrides independently
receive exact EVM BootstrapProfileError(1,1) and unchanged roots. Fresh reopen,
Java8 TEST oracles and3724 canonical ABI/event/checkpoint/counter/read-range
receipts pass. Additional26 candidate-negative receipts verify the reproduced
failure. These do not establish broad Session/fault or full API acceptance.

Corrected source-build/generated/original gate:491.176291s/896630784B sampled
whole process-group RSS, exit0. Parent does not use the worker runner which unsets
TMPDIR and has no RSS sampler. All parent build/run scratch is fresh ignored and
absolute; no nested-session/timeout escape or automatic gas increase.

## Original20: new measured minimum-slice budget blocker

Same untouched20 original images,214042B/66 genuine DI0 fragments, in a NEW world
with repaired pins. q7 reaches epoch239/1673J/8I, then actual
`LC0ControlError(7)` at74069428gas. No failed-slice progress is credited.

Parent then supplied **1** to the existing public ResumeMain instruction-budget
argument. The Go COPY adds a smaller-budget mode only: it does not rewrite the
saved default quantum7, interpreter, gas/reserve, profile or opaque checkpoint.
The old q7 failure receipt is preserved. Ten genuine successful same-code q1
continuations advance to **epoch249/1683J/10I**. Last successful checkpoint:

*11359B, SHA256
  `affcf10ae1a90714a60255dc1b13475e62026d412dd38b1993e802b36528d2fe`;
* root `16a6be321c8b9464a9a7a7566c9871b8b91ddd04db5517422e4ca4df90bc7d40`;
* last gas97536685; maximum successful gas in this world97932316.

Next **q1 also refuses LC0ControlError7**, at73494750gas, with Head byte-identical
and EVM root unchanged. This is the minimum valid Java slice, not a timeout or
proven out-of-gas.249 original successful receipts verify independently. The
smaller-budget build/replay/reopen gate took4.812551s/327299072B.

Last public checkpoint has14 physical frames. Top original PropertiesUtil(String)
constructor is atPC4 (`new java/util/Properties`), after its Object constructor.
There is **no committed Properties allocation/constructor progress**. The precise
reserve-guard site and gas-cost distribution require read-only EVM profiling;
do not assume it is frame exhaustion, preparation or commit merely from selector7.
Three source guard sites exist (_checkBudgets, _execute, _commit).

Next step is measurement-led cost reduction under the SAME100M/25M limits, not
raising gas or skipping constructor/guest branches. No original body/EULA/listener/
world/Done. All original indexing/DEFLATE/CRC/class evaluation stays EVM-side.
Parent archive9515 allowlisted metadata/checkpoint/generated-fixture files excludes
original JAR/class/resource-page and all LevelDB payloads. No push: latest expressly
authorized remote snapshot remains1e4027b9b; later work is local only.
