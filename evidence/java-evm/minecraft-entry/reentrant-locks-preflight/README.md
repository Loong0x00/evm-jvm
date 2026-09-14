# Bounded Java 8 reentrant-lock bootstrap preflight

Basis: accepted CopyOnWriteArrayList source/evidence at `9935e1fbd`. This fresh
`LOCAL384` profile (`MC-REENTRANT-LOCKS-PREFLIGHT1`) is source/gate preparation,
not an acceptance, original-artifact execution, Minecraft startup, world, or `Done`
claim.

Exactly four immutable Java 8 `-g:none` images append at indexes 75--78: `Lock`,
`ReadWriteLock`, `ReentrantLock`, and `ReentrantReadWriteLock`. `ReentrantLock` has
only a guest `int holds` field and no-argument constructor; `lock`/`unlock` mutate
that field for balanced nested calls. `ReentrantReadWriteLock` has only its
no-argument constructor and read/write accessors. It creates two distinct guest
`ReentrantLock` objects once and returns their stable identities. Both concrete types
implement `Serializable` using the existing bootstrap interface.

This is deliberately a single-guest-thread data-model slice. It does **not** claim
fairness, conditions, timed or interruptible acquisition, ownership transfer,
contention, host locking, native locking, or unbalanced-unlock exception semantics.
No such method is supplied or fabricated.

`tools/verify_source.py` rebuilds all 79 owned Java sources against a Java 8 rt.jar
stripped of every replacement, checks all 75 prior image bytes exactly, and reverses
only the four append/domain/reservation/count changes to require exact equality with
the accepted COW source. It pins raw25/262144, exception14, global-native11,
String-local10, frames128, CP4096, Code65535, heap/VFS/checkpoint1MiB, Head32768,
LOCAL1B/25M reserve and the LOCAL384 runtime cap. It also raises only the diagnostic
class ceiling from 100 to 104 (raw25 plus bootstrap79).

The source tree contains no original Minecraft JAR/class/resource/page, world,
LevelDB, generated Solidity binary, or host Java execution route. `tools/gate.py`
uses only trusted generated lock and retained COW fixtures with Java 8 host oracles; a
later evidence-only commit may archive its summaries and monitor data.
