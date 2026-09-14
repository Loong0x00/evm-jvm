# Measured `Class.newInstance()` preparation — completed

Accepted cap25 original execution reaches epoch549/3819 Java steps, inside
`AbstractLogger.createDefaultFlowMessageFactory()`. Its exact bytecode at PC3 is
`invokevirtual java/lang/Class.newInstance:()Ljava/lang/Object;`; the current
replacement `java/lang/Class` intentionally has no such method, so LOCAL EVM returns
`CallError(3,3)` with the published trie root unchanged. The receiver is the
canonical mirror for genuine packaged raw class
`org/apache/logging/log4j/message/DefaultFlowMessageFactory`, a public concrete
class with a public `()V` constructor and no `<clinit>` method.

Implement only the measured reflective construction path:

* add the genuine public Java8 signature
  `public native T newInstance() throws InstantiationException, IllegalAccessException`
  to the replacement `Class<T>`;
* add one distinct Class-local/global native binding (11), with exact native/public,
  descriptor, ownership and no-Code validation;
* for a canonical class mirror, validate a non-interface/non-abstract accessible raw
  class and a unique public zero-argument constructor before mutation;
* perform ordinary active-use initialization through the existing EVM class-init
  machinery (rewind/retry if genuine `<clinit>` frames are scheduled; never fake an
  initialized state);
* apply the same object-layout, throwable/VFS profile and heap quotas as ordinary
  guest `new`; allocate an uninitialized object, leave its alias on the caller stack,
  and run the genuine selected `()V` constructor frame so existing constructor return
  converts aliases to initialized references;
* null receivers remain ordinary guest NPE. Unsupported target/access/constructor
  shapes must use a new deterministic profile refusal before allocation rather than
  fabricate `InstantiationException`/`IllegalAccessException`. No generic failed-state
  recovery is requested.

Focused Java8-generated gates must cover q1/q7/direct/reopen/canonical equivalence,
canonical returned class identity, genuine target `<clinit>` before constructor,
instance-field effects, exactly-once construction, null NPE, OOM quota behavior, and
pre-mutation refusals for bootstrap/abstract/no-public-zero-arg targets. Retain
Class.asSubclass/forName, Integer/NFE, split/CNFE and all existing controls; update the
old intentionally omitted `Class.newInstance` control to assert the new bounded-profile
refusal without weakening the still-omitted Class APIs.

Parent acceptance and the next measured frontier are recorded in
`JAVA_EVM_MC_CLASS_NEW_INSTANCE_PARENT_PREFLIGHT.md`.

The accepted stage uses fresh engine/coordinator/address/domain/worlds under LOCAL384 and keeps raw25/262144,
71 bootstraps unless Java8 compilation proves otherwise, exception kinds14, frames128,
CP4096, Code65535, heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve/30s call and
20min/4GiB whole gate fixed. Source-build and verify exact bootstrap bytes. Then parent
must independently rebuild/replay and run a **new** unchanged original25 q7 then q1
world. No host execution path, lazy loader, fabricated class/object, original artifact
in worker evidence, Minecraft main-body/world/Done claim, or push.
