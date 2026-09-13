# Next Minecraft blocker: reference Class literals and getName (COPY only)

Measured: original MinecraftServer initializer dispatched one Java step and
committed epoch1; next resume predecodes original LogManager.<clinit> and rejects
CONSTANT_Class loaded by ldc_w atPC6, BytecodeError13,6. Class.getName followsPC9.
This authorizes only the minimal class-literal capability needed next—not Java SE
or broad reflection. Preserve exact original guest code and genuine logging path.

Build a NEW isolated derivative of MCEntryInterpreter/Coordinator224c23b23,
including existing MR0, lazy Selected, Runnable and16/262144 COPY caps. No accepted
source/ABI/quota changes; no fakeMC/logger/Done or host execution fallback. Ordinary
100M30s,20min4GiB,<=320KiB engine,CP4096/Code65535/heapVFSframes/CP1MiB unchanged.

Minimum semantics:
- `ldc` and `ldc_w` CONSTANT_Class for ordinary reference classes/interfaces.
  Predecode validates CP structure/name form but does not eagerly bind otherwise
  unused targets or initialize a class. Resolve/access-check on actual execution.
  Missing target still returns true EVM diagnostic; malformed/other unsupported
  tags remain refusals, not accepted as arbitrary references.
- Real canonical guest java/lang/Class mirror references, one per represented type
  in the immutable package/loader context; stable equality across calls/slices/
  reopen. Genuine non-null object compatible with Object/Class casts. No host map
  becomes authority, no class-data/decoded-mirror injection.
- Add minimal owned Class bootstrap and `getName()Ljava/lang/String;` semantics:
  reference binary name uses dots, preserves `$`; genuine guest String. A small
  Java getter over VM-owned private fields is preferable where existing bytecodes
  suffice; no need broad native reflection. Preserve prior bootstrap indexes.
- Class literals must NOT execute target <clinit>. A generated tracker class proves
  the literal/getName leaves target initializer untouched until later active use.
- Existing mirror state must be EVM checkpoint authority. Prefer bounded ordinary
  guest heap/private fields and existing codec over broad new serialization/cache.
  Validate restored mirrors/type/name/uniqueness as necessary; obey OOM/reserve/
  frame/heap limits and normal initialization/access rules. No publicly forgeable
  mirror constructors/setters or raw java/lang/Class override bypass.
- No Object.getClass, Class.forName/newInstance, reflection enumeration/ClassLoader,
  Thread, primitive wrapper TYPE, arrays or primitive mirrors unless needed by this
  measured path. Unsupported cases may remain explicit profile refusals; do NOT
  claim full Class semantics. In particular CONSTANT_Class name `I` can mean class
  I, not a primitive mirror; do not misinterpret it as int.class.

Generated smoke: ldc narrow + ldc_w wide, class/interface/$ binary names, repeated
literal reference equality, non-initialization of target, actual later init, q1/q7/
direct persistence, typed String result content, missing target diagnostics and
untaken missing literal branch, ordinary quotas/real Java exception. Parent then
independently rebuilds and retries ORIGINAL unchanged-JAR frontier. No original
JAR/class handling by the runtime worker; no generic Session expansion.
