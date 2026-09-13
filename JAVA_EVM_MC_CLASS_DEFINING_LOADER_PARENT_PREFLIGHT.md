# Parent Class defining-loader preflight

**Parent-verified startup-path defining-loader COPY, with bounded edge caveat.**
Not resource lookup, full Class/ClassLoader/JVM/Session or Minecraft startup.
Evidence: `evidence/java-evm/minecraft-entry/parent-102911980/`.

Worker bfa06755f/102911980 candidate fits320KiB by22B but omitted whole-group RSS
and dynamic tamper/alias negatives. Parent independently compiles Class,
ClassLoader and concrete VMClassLoader images and source-builds the exact candidate.
Review found two real boundary issues:

1. On the first raw mirror, if its class-name String is already interned and no
   loader exists, code creates loader+mirror but checked capacity for one object/
   handle. Parent computes reserveObjects=2 before any allocation; String misses
   already delegated correct reserve to `_internStringUnits`.
2. VMClassLoader itself was not caller-reserved. Parent extends the ClassLoader
   reservation to both abstract/public and VM-owned concrete names.

Parent also restores unrelated `_classNameUnits` formatting; semantics unchanged.
The repaired source surprisingly emits **327266B** and still passes320KiB with414B
headroom, so LOCAL384 was not used. This is a measured optimizer-layout result.

## Repaired pins and semantics

* Class440B SHA256
  `4e13134b8f82af8fb51b268f92fea91ccf3ed731b1adcb24eddc66b1889913bd`;
* VMClassLoader143B SHA256
  `936fc65d33d3b2f7d9c2267b8e62c42e58c8135b35d6e4d08f65daec831cf944`;
* LOCAL engine `0x4d432d4445464c4f414445522d504152454e5401`, all-nine domain
  `MC-CLASS-DEFINING-LOADER-PARENT1`;
* engine327266B SHA256
  `34150d673860288d41228bfcde5804cff60fc4d89c755c84eff1f179242b0bfd`,
  Keccak `a34de6dbd33d3a4bdf323e61c9a2ce4d7abe8529d0b18eae2a5ae0874d628489`;
* ordinary-CREATE coordinator3547B, Keccak
  `e308d1c42c8c34c764b872f377d041abca9995e2f00331731e8340d50db2f586`.

Class mirrors hold name and definingLoader ordinary fields. Immutable Program
rawClassCount distinguishes supplied raw classes from appended VM bootstraps.
Raw literal mirrors share one nonnull checkpointed concrete VMClassLoader;
bootstrap mirrors have null. Loader identity is reconstructed by validated heap
scan, not host side table; duplicate/wrong/missing identity and wrong mirror
fields reject in source. Only actually created mirrors are required. No loader
operation or resource result is implemented.

LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,128frames,CP/Code/heap/VFS/1MiBCP/
32768BHead/320KiB otherwise unchanged. Engine is LOCAL initial state only.

## Parent evidence

Generated parent fixture has three raw classes, noninitializing literals, shared
nonnull loader, bootstrap null loaders and prior Thread/PrivilegedAction/System/
Properties/arraycopy controls. q1/q7/direct reach VOID331J/8I, epochs331/48/1,
equal machine `1d6ea96459b5d51a0ed7c360dbd4d70767763f3d508d117504824f267af03a13`
and opaque `d3e14b033f2b16f71e86f4c270c734fc1778a68b5707a57f24949987906f07fe`.
380 canonical receipts pass. Caller VMClassLoader replacement now rejects;
getSystemClassLoader remains CallError(3,0).

Dynamic checkpoint-byte tamper was not executed: public anchor hash would reject
before state decoding, and no private Session access is used. This is an explicit
edge-coverage caveat, not claimed acceptance. Parent source review and generated
identity paths cover the measured startup need.

Whole exact candidate build + repaired320 build + generated + original gate:
**521.778868s/956329984B**, exit0. First parent attempt failed in0.106147s because
Java8 javac lacks `--release`; preserved, corrected to source/target8+rt bootpath.
Worker had no whole RSS number; parent value is authoritative.

## Original committed frontier

Fresh original22 q7 reaches epoch257/**1799J/16I**,13709B CP SHA
`8117c42cc2de7f4e6dc5856b0d3fa73674b9f8a50007c4e61d886fc78498ce89`, root
`caa63b53db686354745fca8e322d2759afe97c0e1af2af7c877ba4f5ba25d99f`.
Last successful gas120443236; max verified121020901. Frames show
LoaderUtil.findUrlResources atPC31 with its three-element ClassLoader[] on stack.
The raw LoaderUtil mirror returned the same nonnull defining loader; the previous
inner fallback and `Class.getClassLoader` are committed.

Next actual q7 and minimum q1 both CallError(3,31), gas85647013, Head/root unchanged:
`ClassLoader.getSystemClassLoader()Ljava/lang/ClassLoader;` at
findUrlResources PC31. No q1 progress is fabricated.257 canonical receipts pass.

Next implement only this VM-provided static getter returning the already canonical
loader; no getResources/loadClass or fake empty collection. No main-body/EULA/
listener/world/Done. Parent archive2651 allowlisted files excludes original payloads
and LevelDB. No push; authorized remote remains1e4027b9b.
