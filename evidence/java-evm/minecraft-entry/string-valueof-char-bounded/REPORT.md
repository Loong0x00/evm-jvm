# P57 candidate: ordinary `String.valueOf(char)`

Status: implementation and generated-fixture EVM proof completed locally; **not parent-accepted**. This is not an original Minecraft run.

## Source basis and scoped changes

The only source basis was the approved source-only snapshot `../string-valueof-char-source-base-p56/`, manifest-verified against all 10 recorded SHA-256/byte-count pairs. It names base/accepted commit `c52f0b8fb13cf0c28cf51b88b2ec63f6cbe9870b`. No original Minecraft JAR/classes/resources/world/receipts or parent review/performance-review evidence were read.

- Recompiled the unchanged baseline `String.java` by itself with `/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -bootclasspath /usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar`; it exactly reproduces bootstrap index 26 (2198 bytes, SHA-256 `d4a4e57f636968bc3d6d0ab5c11e45e52ea85c521c31baa63e671243db045155`). The baseline class is retained under `repro-old/`.
- Added only `public static String valueOf(char)` ordinary bytecode: allocate one-element `char[]`, store the input code unit, and `new String(chars)` through the existing copy constructor. The resulting Java8 image is 2285 bytes, SHA-256 `fe68ab4a5124d504c2a56805cf8766b4c5f5ccdbb646733351b67bac8ddfef2a`, Keccak `a6bea491c1a065db2e954d2c8ca825def0af9db04aa736af05c5ff05c0516486`.
- The sole String-profile symbolic-call exception is the exact non-interface ordinary reference `java/lang/String.valueOf:(C)Ljava/lang/String;`. All other calls keep the prior rejection path. No native binding was added or changed.
- Recomputed the 123-leaf bootstrap root. Exactly leaf 26 changed; all other 122 ordered leaves are byte-for-byte equal to the P56 pins. Root: `e018143afd38ad0531860fad7f8116bcdbfaa6ebe3c9348fa06a424097f09573`.
- Updated only the coordinator's fixed engine code hash to bind the candidate engine. Engine/coordinator ABIs and engine storage layout match P56 exactly. Candidate engine runtime is 445564 bytes (SHA-256 `ca7d9a96440c2ba3f1f7fb9bbec6d4f672278e1f666db4c27a3dfb6740f75f5b`; Keccak `172100f22e0a2407309029b667be9c27e77781466dcb2732a82906336b4f959c`). Coordinator runtime is 5411 bytes (SHA-256 `1b07a75710606dea27db6e8c466fe4846e6c9914e3f73037f2bd68856e30493e`; Keccak `2ef323726dd8b93dcdb64541304215a8fdbc90f4df0ddded844e286e1a5b103e`).

## Checks and observed results

- Java8 baseline reproduction: exact 2198-byte baseline class hash.
- `audit_class.py`: same class structure/fields and all pre-existing method disassembly after constant-pool-index normalization; only public static ordinary-Code `valueOf(char)` added. Its bytecode contains one-element `newarray char`, `castore`, and `invokespecial String.<init>:([C)V`.
- Java8 generated host oracle: all 65,536 UTF-16 code units plus representative boundary list passed; length is one and `charAt(0)` preserves the exact unit, including NUL and isolated surrogates. The oracle also checks independent String results, value equality/hash/compare, `toString` identity, and char-array constructor copy behavior. This is an oracle only, not host execution authority for EVM results.
- Generated guest class `p57/ValueOfCharEvm` contains direct `invokestatic String.valueOf:(C)String`; seven representative values (44, NUL, 255, 256, D800, DC00, FFFF) additionally check independent result identities, ordinary String methods, existing copy constructor isolation and intern agreement. Fresh EVM worlds completed successfully through terminal lifecycle 2 at q=1, q=7, and q=65536. Each was started and finished in separate driver processes. All three report 1422 Java steps and equal machine root `0xc5b4913c3c8ed751be84dd175fc0199019c06aae7c1d202922144dde81aaa035` and VFS root `0xece4edd0086695b92a85b747a6c6631e8e31408afd1d8566e7b3d044fc4c10c0`; epochs were 1422, 204, and 1 respectively.
- A generated unsupported `String.valueOf(int)` fixture was run with q=65536. It ended in the existing raw `StringProfileError(1,2)` refusal, with root and durable Head unchanged (start-refusal receipt retained under `reports/world-negative-int-q65536/`). It does not establish every unsupported overload/control case.
- A first negative q=1 world remains preserved as an incomplete attempt; it was not used as evidence. An initial generated-fixture lookup attempt using a binding without `.class` also remains preserved; it failed in DI0 lookup before Java execution.

The candidate has not demonstrated every requested negative control, private-backing inspection, or independent parent replay. No original artifact was accessed or executed. Do not describe this as Minecraft readiness, a full Java profile, or parent acceptance.
