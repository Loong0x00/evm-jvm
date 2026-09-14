# Parent java.version and bounded String.split preflight

**Parent-verified with one constructor restoration.** Evidence:
`evidence/java-evm/minecraft-entry/parent-6e7185d9c/`.

Worker6e7185d9c correctly seeds the real guest System Properties table with exactly
`java.version=1.8` in ordinary `<clinit>`, and adds String-local native binding10 for
exact `split(String)String[]`. It accepts only UTF-16 `-|\\.`, splits literal `-`/`.`,
preserves internal empty pieces, drops trailing empties, preserves receiver identity
for no-match/empty input, and creates non-interned pieces with owned char[] plus rank1
String[]. Null receiver/regex raise guest NPE; unsupported regex refuses. Quotas are
preflighted atomically and OOM becomes guest kind7. Global native bindings remain1..9.

The worker stopped before generated EVM execution and accidentally removed existing
public `String(char[])` and `String(String)` constructors from its815B image. Parent
restores those ordinary Java methods before acceptance. Genuine Java8 `-g:none` pins:

* String1015B SHA
  `c412caea1d48baade8aa9d2653c6a23bb319a49deefe729ac99089f0c5248eba`;
* System825B SHA
  `fd3898b354bb3e804fc09580d6a7c1d01ea02db4789ca2a876deb3ef9e03ae44`;
* Class670B SHA
  `0e3d4ea717a8c96c75d6eca139874e100ab7e5700758dc14acd6ae47b84b7934`.

Parent domain `MC-JAVA-VERSION-SPLIT-PARENT1` uses engine
`0x4d432d4a5653504c49542d504152454e54000001`,361817B (31399B LOCAL384
headroom), SHA `6773f99a3feee7439a411f698b2a661e4c55a2c7c9de1130313e5e1fdb12fa0e`,
Keccak `0c8543128293d5be0150b6ac5814936135ef122f76e36ef49864f91bee289201`.
Coordinator4146B Keccak
`4611de5f53f7d5aa3a4125d7bd2f5aeb38dafc6996e602137e285bbea517e482`.
Total68, exception kinds14 and accepted320 remain unchanged.

## Generated acceptance

The parent combined probe covers java.version, split values/internal/trailing/no-match/
empty/derived identity, restored constructors, null NPEs, and a1026-piece quota case
caught as guest OOM, plus every forName/loadClass/CNFE, Boolean/System/IAE, genuine
EVM-ZI0 resource/URL/set/thread/PA/arraycopy control. Successful q1/q7/direct state is
identical at4174J/29I, epochs4174/597/2, machine
`8cc9fe32a12f20fbff8287e03dfd646338664cd5b767ec0669f07b79b0505a06`, opaque
`996ba0111e2c625e50591c9cf72f69a0f27955dc3ce50e784fdcd72e37a10f8b`.

Uncaught forName remains lifecycle3/kind13 at4J/3I, epochs5/1/1. Unsupported regex and
omitted split-limit both honestly refuse StringProfileError (PC4/5); raw String/System,
forName uninitialized/omitted and all prior replacements refuse without root change.
4174 q1 canonical receipts and606 fresh q7/direct/terminal receipts pass.

A development harness expected omitted split-limit to use CallError, but actual narrow
String fallback correctly uses StringProfileError; that expectation-only failure is
preserved. A first serial whole gate then hit the fixed1200s wall after source build,
a fully successful4174-epoch q1, and partial q7 (peak960294912B); no transient/failed
state is reused. Final gate independently source-builds exact code, canonically
revalidates that successful q1 world, runs fresh q7/direct and all refusals, proves
opaque equality, then runs a NEW original22 world. It exits0 in527.868048s with
982192128B whole-process-tree peak.

## Original frontier

Original22 consumes `java.version=1.8`, splits to `"1"`,`"8"`, and advances
Constants.getMajorVersion to exact PC16 invokestatic
`java/lang/Integer.parseInt(String)I`. `java/lang/Integer` is absent from the68
bootstraps, producing genuine MissingClass context4107/site16, selector555db429.

q7 reaches epoch380/2660J/26I then refuses at gas110339303. Three successful q1 steps
commit PCs14,15,16. Final epoch383/**2663J/26I**, checkpoint16607B SHA
`20a48e539db3375486229e676b99dc22b6a88a109686712935523ad46bd120c5`, root
`c976ad87ac10ec3b822b1a8c4464185d8e8666012a454e0e432e1e5263bd5f3a`, machine
`7d3b86402d5cb9d0ffc3551cace76678192b5e11da20725d7035b442d56b32be`.
Next q1 repeats MissingClass, gas110333730, Head/root unchanged.383 canonical original
receipts pass. Next append bounded Number/NFE/Integer with ordinary decimal parseInt;
no host parser. No Minecraft main body/world/Done.
