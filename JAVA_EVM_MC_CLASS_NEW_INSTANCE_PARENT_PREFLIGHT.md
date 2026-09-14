# Parent acceptance: bounded `Class.newInstance()`

The parent independently accepts the measured LOCAL-only `Class.newInstance()` path.
Worker commits `85005e73a`/`c4da5cd11` were integrated as
`28e7a803e`/`94710ca9b`. Parent evidence is
`evidence/java-evm/minecraft-entry/parent-94710ca9b/`.

## Scope and source build

The 1171-byte Java8 replacement `Class<T>` adds exact public native
`T newInstance() throws InstantiationException, IllegalAccessException`, SHA256
`2cd0cbf46c408cff70c8dc8a4ac8b6f3e5a153162f4a42b5afc9f59bad360e8a`.
The checked types are declaration metadata only; this bounded successful profile does
not fabricate them or add exception kinds. Binding11 is accepted only as
public/native/no-Code `()Ljava/lang/Object;` on canonical `java/lang/Class`.

The receiver must be an existing canonical mirror for a raw public concrete class with
a unique public zero-argument constructor. Constructor descriptor/Code/profile checks
happen before active use or allocation. Unsupported bootstrap, abstract/non-public or
constructor shapes deterministically revert `ClassNewInstanceProfileError` rather than
pretend to implement reflection failures. Null remains the ordinary catchable guest NPE.

Successful calls run the existing class-initialization continuation, rewind/retry if
`<clinit>` is scheduled, apply ordinary object/profile/heap quotas, allocate a genuine
uninitialized EVM-owned object, and execute the selected real constructor frame. Existing
constructor return/unwind initializes or poisons aliases. No host reflection, loader,
class execution, fake initialization or synthetic result is used.

The isolated parent domain is `MC-CLASS-NEW-INSTANCE-PARENT1`, engine address
`0x4d432d4e4557494e5354414e4345000000000001`. Independent solc0.8.30
optimizer200/viaIR/Cancun/metadata-off build produced 374848 bytes, SHA256
`97bccc5fbe15f9b91b63b86f2d8f115ab1b4183d2d4c3db70d21ee725fb0f44b`,
Keccak `72586aa389a0fda42e9aae266a094709dadcddf418473cab6b37358713949186`.
The 4146-byte coordinator Keccak is
`3f88f0c86fc7b6272212f53dcf683bc9a1ea6ca136447d9fe8750366b87f3af3`.
The build took236.60s, peaked at989786112 bytes group RSS, and stayed inside LOCAL384.
Raw25/262144, bootstrap count71, exception kinds14, String-local10,128 frames,
CP4096, Code65535, heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve/30s and
accepted prior worlds remain unchanged.

## Parent gates

Fresh Java8 generated q1/q7/direct/reopen and canonical receipt verification pass for:

* target `<clinit>` before construction, two distinct objects, exactly-once class init,
  exactly two constructors, class identity and instance/static field effects;
* q1 checkpoints with target state1/init continuation and initializer frame, followed by
  22 checkpoints carrying genuine constructor `KIND_UNINIT` aliases that reopen and
  converge with q7/direct;
* caught null NPE kind6;
* constructor-thrown `IllegalArgumentException` propagation and alias poisoning;
* failing `<clinit>` producing existing EIIE behavior, then erroneous-class NCDFE on retry;
* object-profile quota OOM kind7 using a valid 1025-instance-field target;
* root-unchanged profile refusals for bootstrap, abstract and private-constructor targets.

All retained Class.asSubclass/forName/CNFE, Integer/NFE, split, resource, loader,
Properties, Boolean, VFS and prior focused controls pass. No watchdog exceeded20 minutes,
4GiB or30 seconds/call; the largest observed group RSS was the source build above.

## Unchanged original Minecraft result

A fresh world used the pinned untouched server JAR SHA256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`
and the same genuine25-class/228073-byte package. q7 reached a successful
checkpoint at epoch548/3836 Java/32 internal steps. Four q1 checkpoints then reached
epoch552/3840 Java steps. All552 successful receipts passed independent canonical nested
ABI/event/checkpoint/counter/resource-range verification. The genuine
`DefaultFlowMessageFactory` target is initialized and its real constructor returns;
`AbstractLogger` returns and `StatusLogger.<init>` advances to PC7.

The next measured blocker is `new java/util/concurrent/CopyOnWriteArrayList` at
`StatusLogger.<init>` PC7: `MCEntryMissingClass(4104,7,...)`. q7 and q1 failed calls
preserve the published trie/head. This is a Java platform class, not a request for a 26th
same-JAR raw class. No Minecraft main-body, world creation or `Done` is claimed.
