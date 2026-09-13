# Next measured Minecraft platform blocker: Properties construction

Parent classcount24 proof: `JAVA_EVM_MC_CLASSCOUNT_PARENT_PREFLIGHT.md`.
Actual untouched original20 reaches1680J/10I then
`MCEntryMissingClass(4104,4,java/util/Properties)` at original
PropertiesUtil(String)'s allocation. TEST-only excerpt confirms no-arg constructor
atPC8, then original LoaderUtil.findResources atPC13. Only the allocation/constructor
need is currently measured; later resource searches/load methods have not executed.

## Minimal new isolated platform COPY

Derive exactly from parent-verified classcount24 engine/coordinator and actual
bounded parent driver. Add legitimate guest Java Properties storage/construction,
not an empty stand-in for Log4j configuration. Preserve Java type hierarchy:
Properties extends Hashtable<Object,Object>; Hashtable extends Dictionary and
implements Map, Cloneable, Serializable. Minimal owned Dictionary/Hashtable
surfaces needed for that hierarchy may be appended, without claiming complete
Java SE implementations. Prefer real guest Java using the existing map subset;
no arbitrary host property/map callbacks.

Required no-arg Properties constructor; sensible bounded map backing rather than
hardcoded results. Small generated controls may cover defaults constructor,
getProperty(key[,fallback]), setProperty and necessary inherited map operations,
old-value/null/type/default-chain behavior and hierarchy identity. Existing guest
map/virtual equality can be reused. Do not implement unmeasured Properties.load/
store parsing, enumeration APIs, XML, System properties/environment, ClassLoader,
Thread, URLs, resource search or broad collections merely to complete Java SE.
Missing APIs must remain honest refusals; never fake an empty resource search,
substitute an original class, skip guest branches, or fabricate startup output.

Append new reserved bootstrap images after existing45, retaining all prior bytes/
indexes, conditional supplied-Runnable/Class indexing, exactmain/argument semantics,
lazySelected/direct reads and repaired arraycopy arity/behavior. New addresses,
domains, store identity and pins; no cross-code checkpoints. Oversized engine is
explicit LOCAL initial-state-only; controllers/resources ordinary CREATE.

Retain24/262144, CP4096, Code65535, heap/VFS/frame caps,1MiB checkpoints,32768B Head,
320KiB engine,100M gas/30s calls,25M reserve, and a whole20min/4GiB process-group gate.
Use the actual bounded parent driver. No accepted/core/ABI/quota/Makefile/settings
changes, no push, no workers touching originals. Default Terra/high, one semantic
Solidity writer, early commits, fresh ignored build directories and absolute TMPDIR.

**Measured pressure:** original20's last successful call already costs97161371gas
and has14 physical frames including initializer continuations. A faithful
Properties/Hashtable/Dictionary/Object constructor chain may expose a real gas or
frame limit. Preserve it. Do not short-circuit constructor linkage or raise limits
to hide it. Parent will diagnose that actual next failure if it occurs.

Generated Java8 TEST oracles, q1/q7/direct, aliases/defaults/real type hierarchy,
shifted-tail Class/arraycopy controls and fresh reopen. Require actual lifecycle/
outcome, guest sentinels, canonical EVM events/checkpoints and opaque machine
agreement; a host finished label is not proof. Archive no LevelDB/resource-page
payloads. Parent independently rebuilds and replays before a NEW original20 world.
