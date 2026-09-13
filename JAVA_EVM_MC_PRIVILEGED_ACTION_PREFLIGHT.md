# PrivilegedAction preflight

This is a LOCAL, generated-fixture-only derivative of the exact
`parent-2293e298e` security-getter basis. It is not acceptance, a general JVM,
or a Minecraft main-body/world/Done claim. Parent alone must source-only
rebuild/replay and then start fresh original22 at quantum 1; failed original
calls are not continuation authority.

## Narrow change

The derivative appends only genuine Java 8
`java/security/PrivilegedAction<T> { T run(); }` as bootstrap root image 48
(after the existing 0..47 images). Its compiled image is 198 bytes, SHA-256
`8188676e90fe79c605761b4592483b511966e7396f8a14e0d9b7962f00d948da`.
The copied parent source is mechanically checked to retain all prior 48
bootstrap bytes exactly. The source change increases the bootstrap root array
48→49, appends the image after Properties in the dynamic class table, reserves
`java/security/PrivilegedAction` against caller supply with
`BootstrapProfileError`, and changes only the bootstrap domain.

No `AccessController`, `SecurityManager`, `ClassLoader`, permission API,
Thread, System-property/resource lookup, privilege grant, or branch bypass is
added. The parent System private nullable default getter and native arraycopy
remain unchanged, as does the Properties `super.get` repair.

## Isolated pins and fixed limits

* domain: `MC-PRIVILEGED-ACTION-PREFLIGHT1`;
* local engine: `0x4d432d50524956494c454745442d414354494f4e`;
* owner: `0x4d4350524956414354494f4e0000000000000002`; fresh generated store:
  `0x47057e167c5f3d9b94af3d4b2675c5cc28891b14`;
* engine: 323700 bytes, SHA-256
  `02272e32a4885c99c63f69e900828bf758d9c98eb37f4b253e847c6f9e303902`,
  Keccak `05259639552222f01f3ba651c88175ea9a03926d877bc7825c6cf0f1fd8038d5`;
* coordinator: 3547 bytes, Keccak
  `49c31659c3a6ae89fbab6bf481ae3e5e3322c2780c55d66d39311a9da4323c23`.

The copied bounded driver retains user-authorized external LOCAL1B, 30 s/call,
25M reserve, 20 min/4 GiB whole group; 24 classes/262144 bytes, actual 128
frames, CP4096, Code65535, heap/VFS, 1MiB checkpoint, 32768-byte Head and
320KiB engine cap are unchanged. The oversized engine is LOCAL initial state
only; controller/resources use ordinary CREATE. This does not change accepted
caps, ABI, core, consensus, artifacts, or Makefiles.

## Generated result

`evidence/java-evm/minecraft-entry/privileged-action-preflight/` contains the
Java sources and recipe; its `artifacts/` child contains the exact
copied-and-derived Solidity/Go sources, pinned compilation outputs, complete
slice receipts/checkpoints, logs and SHA256SUMS—without a Go binary, LevelDB,
original payload, resource pages, JAR, original class, or original world.

Pinned Java 8 fixture `PrivilegedActionProbe` genuinely implements
`PrivilegedAction<String>`. It invokes `run` through a raw erased interface and
a typed generic interface; Java 8 `javap` records both String and Object bridge
methods. It also exercises `PrivilegedAction.class.getName`, default-null
`System.getSecurityManager`, unchanged `System.arraycopy`, and Properties.
Host Java is only the generated-fixture oracle.

Fresh direct/q1/q7/reopen EVM runs reach VOID respectively at 1/226/33 epochs,
all 226 JVM + 4 internal steps, with identical machine root
`0x704e7fb5e5f2b2e41fec7d0dfab001c9f0891799ceee3714f79ca4f8334a5ae8`
and opaque checkpoint SHA-256
`6924ab444a77f9b3169164470f6d8bc364c29ef619bab6916bb453d98f80ec25`.
The driver validates canonical nested ABI/events/checkpoints/read traces per
slice; 226/33/1 full receipts are retained. Maximum call gas was
20,612,966 / 20,950,945 / 34,947,589.

Caller-supplied `java/security/PrivilegedAction` is refused with canonical
`BootstrapProfileError` selector `0x6a23ad80`, root unchanged. The retained
`direct-evm-failure.json` files are the driver's existing AS0 post-create
wrong-PI rollback control, not guest execution failures. The explicit
unsupported `AccessController` control remains honest
`MCEntryMissingClass(4107,0,java/security/AccessController)`, selector
`0x555db429`, root unchanged. Neither refusal supplies progress.

The successful gate took 202.974 seconds; solc peak observed RSS was
873280 KiB, under the one 20-minute/4GiB group bounds. It used solc
0.8.30 optimizer 200 viaIR Cancun, metadata off, with
`NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules` and an absolute
fresh ignored `build/java-diff-mc-privileged-action-*` TMPDIR. All child
compiler/fixture/Go/EVM processes inherit one group; no child session or
per-command budget reset is used.
