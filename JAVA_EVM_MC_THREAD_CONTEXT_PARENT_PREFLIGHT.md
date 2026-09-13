# Parent single Thread context preflight

**Parent-verified one-guest-thread COPY.** Not concurrency, scheduling, full Thread,
Class loading/resources, JVM/Session or Minecraft startup. Evidence:
`evidence/java-evm/minecraft-entry/parent-cc0c40e71/`.

Worker1173e59d4/cc0c40e71 appends a normal guest Thread with a static singleton,
private nullable ClassLoader field, exact currentThread and
getContextClassLoader. Parent removed accidentally tracked Python bytecode cache,
independently compiles the450B image, reverses the complete semantic delta to
exact parent-d19622e52 source, rebuilds complete artifacts and derives the
LOCAL1B driver from parent evidence. All nine domains/addresses are isolated.

## Pins and generated proof

* Thread450B SHA256
  `4c76217e07b547c39ef42523e3cef55af582541265882b6998332124b3f72cb5`;
* LOCAL engine `0x4d432d5448524541442d434f4e544558542d3031`, domain
  `MC-THREAD-CONTEXT-PREFLIGHT1`;
* engine326052B SHA256
  `d11b3725ba5151fbfc12011a5df87741cd3c80114eaafb1e056157736b8ea86c`,
  Keccak `ca811ec4bf1be44d6a8a6469d38543cb8ba89b21c93589ba07338c1ed5b7f0df`;
* ordinary-CREATE coordinator3547B, Keccak
  `7c16213411499ea7fd34fc4da229122e244bbf937a8d76a3e1ef96bddc01852a`.

Prior50 images exact, Thread appended50/reserved. Remaining320KiB headroom1628B.
LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,128frames and all other caps unchanged.

Fresh generated repeated singleton/default-null context and retained controls
reach genuine VOID at291J/7I, q1/q7/direct epochs291/42/1, equal machine
`b366bd14d9d38d656456dbcc3a2f83b46dbab0464241e9a6aad85c4e2c3761a0` and
opaque `bd1f32bcf961edc9a224aef61d8e3d8e539639f5160f0556a22255eda0cf4db2`.
334 canonical receipts pass. Caller replacement plus unsupported setter/start/
ClassLoader getter all refuse with unchanged roots. Worker and parent monitors
use a true persistent group high-water mark; parent whole source/generated/
original gate **310.262671s/893448192B**, exit0.

## Original committed frontier

Fresh original22 q7 commits epoch253/**1771J/16I**, CP SHA
`48856625e57380b662405cc60f065928eb3fa1e15c4dcf51968f5dd39f54d76e`,
then CallError(3,16). Preserve failure; two successful q1 checkpoints reach
epoch255/**1773J/16I**. Final13875B CP SHA
`059eabd401d85e02e7be05fee5fd2f79e4740923e9c3f2e6d2afcda3d9994623`, root
`cc8177d0e07e8a27f6a3bd4d0ae32bb1f4311b33cdb563f8e343ba70d5f32555`,
last/max gas113977473.255 canonical receipts pass.

Frames show ThreadContextClassLoaderGetter typed run PC16 with one Class mirror on
stack. Thread class initialization, canonical currentThread identity and default
null getContextClassLoader have committed successfully. The original fallback
then executes `LoaderUtil.class` literal and fails on exact
`Class.getClassLoader()Ljava/lang/ClassLoader;` at PC16. Next q1 same CallError,
gas85451165, Head/root unchanged.

Next cannot honestly return null for every raw class merely to force empty resource
search. It needs a real defining-loader identity for raw class mirrors; bootstrap
mirrors may remain null. No ClassLoader getResources/system methods are yet
implemented. No main-body/EULA/listener/world/Done. Parent archive2559 allowlisted
metadata/checkpoint/generated files excludes original JAR/class/pages/LevelDB.
No push; authorized remote remains1e4027b9b.
