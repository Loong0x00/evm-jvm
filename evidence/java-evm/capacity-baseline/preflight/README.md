# DISPOSABLE capacity baseline preflight (worker draft)

**Status: measured draft only; not an accepted profile and not a self-acceptance.**

Base is `7b46769c5`. This durable evidence records the narrow authorized
`4/65536 -> 8/262144` COPY-only experiment. Accepted source is unmodified; all
prototype copies are ignored under `build/java-diff-mc-capacity-proto-smoke/`.
The compact `patches/*.patch.gz` diffs are the intended Solidity/profile delta; the driver is a
public `cb0.Session` pattern retargeted only to an isolated ignored package.

## Delta and boundaries

VFS copy changes only `MAX_RAW_CLASSES` 4->8, `MAX_RAW_BYTES` 65536->262144,
and its isolated artifact-root domain. CB0 changes only corresponding fixed
arrays/counts, raw class bounds, package/resource/vm domains, profile marker,
and freshly built experimental code pins. Its engine is a separately labelled
LOCAL initial-state install at `0x4A564D45564D564653304152554e5449ca000001`;
AS0, ZI0, DI0 and coordinator remain ordinary CREATE. AS0/ZI0/DI0 are exact
accepted artifacts and limits. Coordinator DI0 FINAL reads remain <=4096.

No accepted source/artifact/ABI/core/quota changes; no bootstrap/opcode/object/
FP/link/exception/VFS semantics changes. CP4096, Code65535, heap/fields/args/
frames/checkpoint and ordinary100M remain fixed. Fixtures are generated Java8
TEST-only; the execution driver consumes only opaque ZIPs via AS0->ZI0->DI0.

## Fresh copy compiler pins

Solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer200, viaIR, Cancun,
metadata off. VFS runtime: 292968B, SHA256
`4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f`, Keccak
`2beb5ef477d93f1479cdf7dfcb18e37792de9b0643b0ee57e15ba74f9e9d59e6`, <=320KiB.
Coordinator is3792B; raw build capture records exact hashes. Constructor profile
allowance is4096 only (eight maximum256B raw names ABI-bound at3744B); complete
init11722B. Parent must rebuild and validate these measurements.

## Actual ordinary-100M results

* Accepted four-class public-CB0 generated static chain: result54, 56Java/9
  internal, one terminal slice, 4,906,954 gas.
* Same four inputs through experiment: same result/counters/gas. Roots differ by
  isolated domain/code pins.
* Eight-class generated transitive static-init/call chain: result148,116Java/17
  internal, direct7,157,937 gas. q7 terminal uses17 fresh process slices; final
  machine/VFS/package/AS0/index/decoder roots equal direct; terminal reopen has
  no engine install.
* Genuine method-rich BigEntry=90874B, CP=2565,2552 methods; BigCaller invokes
  BigEntry.use then m2549. Java8 expected/EVM result15; terminal ordinary
  gas48,451,006, 11Java/2internal. Fresh terminal reopen is retained. This is
  not a padding-only positive.

No1B rescue, official JAR/class, Minecraft, EULA, listener, world, or Done.

## Incomplete (do not infer feasibility)

The full required gate is not complete: no generated5/6 chains, exact8-vs9 or
262144/+1 captures, actual DI0 fragment trace, strict full uint256 raw failure
decoding, or completed20min/4GiB watchdog. The copied public Session API does
not expose DI0 load fragments, and none are inferred. This result cannot choose
eager capacity over a bounded demand design or promote any profile.
