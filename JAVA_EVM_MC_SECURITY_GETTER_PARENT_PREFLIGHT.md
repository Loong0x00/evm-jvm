# Parent System.getSecurityManager preflight

**Parent-verified narrow default getter COPY.** Not full System/security/JVM,
Session or Minecraft startup acceptance. Evidence:
`evidence/java-evm/minecraft-entry/parent-2293e298e/`.

Worker f45ab41ed/ed13f2126/2293e298e integrated locally after de8bdadfa. Parent
independently compiles the exact guest System source/image, mechanically verifies
all other47 bootstrap bytes, rebuilds Solidity, compares complete artifacts, and
derives the Go driver from the actually executed user-authorized LOCAL1B source.

The owned System image has one private nullable SecurityManager reference and
exact getter. Default guest static state is null. Existing arraycopy is unchanged;
there is no setter, SecurityManager class, permission framework, ClassLoader,
System properties or resource-search fallback. Unsupported setter remains an
honest missing member.

## Pins and limits

* Java8 System338B SHA256
  `2dbd8eb88dfc0ed82e0bf84e6a1c06e7530b666674c461e857416782e77bf49a`;
* LOCAL initial-state-only engine
  `0x4d43534543555249545947455454455200000001`, domain
  `MC-SECURITY-GETTER-PREFLIGHT1`;
* engine322301B, SHA256
  `4a8aafbfafef9fed3c3fd3106d99b9819a40ecc2eccfe40e234efa448dc038f9`,
  Keccak `74609271d2d333b617e12d0c2ddeae2574b7812fc72f719453614acb3cc081ae`;
* ordinary-CREATE coordinator3547B, Keccak
  `113bcbc2b3512af2cbddc90379dbc8cacfb64f7df50ef7ec8f89e1bdfe8ed59a`.

User-authorized LOCAL1B external ceiling,30s/call,25M reserve,20min/4GiB;
24/262144, actual128 frames,CP/Code/heap/VFS/1MiB checkpoint/32768BHead/320KiB
engine unchanged. No accepted/core/ABI/Makefile change or standard-chain claim.

## Independent generated proof

Fresh q1/q7/direct generated worlds all genuinely reach VOID at169J/4I,
epoch169/25/1. Machine root and opaque terminal state agree; max gas24971680.
All195 canonical ABI/event/checkpoint/counter/read-range receipts verify. Java8
TEST oracle passes. Executed unsupported setSecurityManager produces exact
CallError(3,1), root unchanged. No unselected branch or broad security semantics
is claimed.

The parent runner removes nested child sessions so its final source build,
generated replay and original21 run share one group: **293.716102s/884891648B**,
exit0. Two harness failures are preserved:

1.194.174699s/900976640B: driver-text equality found worker's only source
difference was cosmetic omitted `0x` on two HexToHash strings; parent keeps
canonical prefixes and asserts that exact difference.
2.195.370904s/899174400B: copied generated runner derived ROOT from its new build
location and refused before Java/EVM; parent pins absolute source/root paths.

Neither is guest failure or evidence suppression.

## Original frontier

Fresh original21 (221382B) under new code commits245 epochs/1715J/12I. Last CP
12247B SHA `9be6496b8a5d9fbaa71face93f07b047a5ae421be3928c7f1b2d0dfbef46e35a`,
root `23b0081921ecb27a6cfdce9535549d31849719dfa302b52b6bba197c790cf7fc`,
last gas104413566. The next EVM error changes from missing System member to
missing original `LoaderUtil$ThreadContextClassLoaderGetter` at new PC6,
gas77296699.

Fresh original22 adds that exact JAR class:222822B, last CP12251B SHA
`250be05401e175f5419009d3daa55df3e4fa284df9d14ad29d7dcf6611125287`,
root `73d1b5821c725f780c7aaf13bd4636d3e842c6c5173219236e3868480da62691`,
last/max gas105829246. EVM hierarchy error is now
`MCEntryMissingClass(4098,21,java/security/PrivilegedAction)`, gas78387637.
245 receipts verify independently.

**Precision:** both successful original heads remain1715J/12I before LoaderUtil
initializer PC0. The missing-inner/interface diagnostics arise from failed calls;
no new original state/steps are credited, and PC6 is before LoaderUtil's eventual
security-null conditional. Generated proof establishes the VM getter's default
null semantics, but no original null branch is claimed committed yet.

Next add only genuine PrivilegedAction interface, then use q1 worlds to expose
committed original steps. No failed trace recovery, original substitution,
permission bypass, EULA/main-body/world/Done. Archive contains generated fixtures,
metadata and mutable checkpoints, no original JAR/class/pages/LevelDB. No push;
last authorized remote remains1e4027b9b.
