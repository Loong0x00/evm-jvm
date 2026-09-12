# MR0 B0 prototype root ABI (frozen draft)

This is a COPY-only disposable LOCAL experiment based on repository commit
`343b55537eee00730c36382529353a78a471f5e5`. It does not alter CB0, VFS0a,
the accepted engine, source tree, artifacts, quotas, or any production ABI.

## Root selection

`RootSpecV1` is not caller-supplied: MR0's coordinator has exactly one root:

```
version=1
kind=MAIN_EMPTY_STRING_ARRAY (1)
method UTF-8 ASCII = "main"
descriptor ASCII = "([Ljava/lang/String;)V"
argsCommitment = keccak256("JVMEVM:MR0:MAIN:EMPTY-STRING-ARRAY:1")
```

The selected `entryAt` remains an EVM-bound raw `.class` binding. The engine
uses the matching internal class name and rejects any selection except one exact
method whose name *and* descriptor match. Method access must be public+static,
not native/abstract/synchronized, with exactly one Code attribute and supported
Code. Other overloads do not count as duplicates; a duplicate exact pair rejects.

## Prototype public ABI

The isolated coordinator exposes only these new selectors for Java execution:

```
startMain(bytes32 assertedPackageRoot,uint8 entryAt,uint64 maxJvmSteps,uint32 maxInternalSteps)
resumeMain(bytes32 assertedPackageRoot,uint64 expectedEpoch,bytes32 expectedCheckpointRoot,bytes checkpoint,uint64 maxJvmSteps,uint32 maxInternalSteps)
```

It never accepts host arguments. It reads all selected classes only through its
one EVM-bound FINAL DI0 route in <=4096 byte reads, then calls the isolated
engine's `startMain` / `resumeMain`. Old `start` / `resume` selectors are absent
from MR0 and the accepted CB0 contract is untouched.

Engine `MR0MainSliceResult` has `outcome`: `1=RUNNING`, `2=VOID_TERMINAL`,
`3=JAVA_EXCEPTION`; `legacyIntResult` is always zero and is not a Java return.
`javaKind/javaRef/javaClass` have their normal existing exception meaning only
for outcome 3. A terminal void has kind/ref/class all zero. EVM validation or
publication failures are reverts, never a result tag.

The checkpoint/anchor config commits schema/root kind/exact method/exact
descriptor/empty-args commitment. The prelude serializes the same fields and
contains no int argument vector. Resume derives the root local from the validated
opaque checkpoint only; it must not create/recreate an array from calldata.

## Bounds/nonclaims

Inputs remain 1..4 classes, aggregate <=65536 bytes, 38 bootstrap images,
CP<=4096, Code<=65535, existing heap/fields/frames/args/VFS and <=1MiB
checkpoint. Calls are <=100M gas/30 seconds. The isolated engine is a LOCAL
initial-state code installation and, if compiled <=320KiB, does not claim
ordinary CREATE, accepted VFS identity, standard-chain compatibility or a quota
promotion. No original archive/class or Minecraft content is used.
