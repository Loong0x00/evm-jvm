# Parent ClassLoader.loadClass preflight

**Parent-verified LOCAL384 immutable-Program loaded-class lookup.** It is not archive
class growth, Class.forName or full ClassLoader. Evidence:
`evidence/java-evm/minecraft-entry/parent-77185cca2/`.

Worker72b850003/692e0e4d1/77185cca2 replaces only abstract ClassLoader position49
with777B/SHA `2642b16dc68706079058f50f2b08544328c495a23217740499d4bb897ae69e3d`.
Public instance loadClass(String) ordinary Java calls exact private static native
loadClass0 binding8. Binding validates0x010a/one String ref/Class ref return. It
compares genuine guest UTF-16 dotted names to every immutable parsed Program class,
and shares canonical `_classMirrorForTarget` with ldc: raw mirrors use the one
VMClassLoader, bootstrap mirrors null, repeated identity, no target initialization.
No host/JAR catalogue or fabricated null.

Worker preserved: initial getter-before-mirror LC0StateError; first binding omitted
publishing arena heap/frontier and failed ReferenceError(1,4); wrong local NODE_PATH.
Final worker fixes frontier publication. Parent additionally fixes quota handling:
shared allocator OOM now invokes existing guest `_raiseJava(7)`, as ldc does, rather
than worker LC0StateError. Ordinary successful behavior is unchanged.

## Pins and generated proof

* LOCAL engine `0x4d432d4c4f4144434c4153532d504152454e5401`, domain
  `MC-CLASSLOADER-LOADCLASS-PARENT1` all nine;
* engine354502B/38714B LOCAL384 headroom, SHA256
  `4edb971a54b5b84b5f773ca0007e1f97a90c13e2f56311dd872a08114b156cbc`,
  Keccak `e6012b354d1d22658aade989ba7ff7fe7700e7698e1d1654adab272d8820d7ce`;
* ordinary coordinator4146B, Keccak
  `1535c48d422b9a8e9764345e48d6e6f92f967f9840395c897e3cbaaf242b9e46`;
*66 bootstrap images/native1..8; accepted320 and all LOCAL384/1B limits unchanged.

Generated combined fixture materializes loader via raw main mirror, loadClass-es an
uninitialized raw nested class twice, matches later literal/defining loader, loads
bootstrap Boolean with null defining loader, then runs all Boolean/System/IAE/EVM-ZI0
resource/URL/set/thread/PA/Properties/arraycopy controls. q1/q7/q4096 VOID3556J/22I,
epochs3556/508/1, machine
`aa1c751981d737b7ae99acebd0ff379f373abd92612f35bfcc21331bfa76003b`, opaque
SHA `0728bc352c3f5613773c09690cc1839226d3a5a63ed3ba4778c68faefda6c90d`.
4065 canonical receipts/reopens pass. Missing/malformed names preserve
ClassLoaderLoadError2/1; omitted overload, raw replacement and prior omissions refuse.

Final whole gate exits0 in **995.980424s/978673664B**. Four parent harness failures
are retained: missing VMResourceEnumeration javac dependency0.212825s/69414912B;
wrong two-static-field sentinel index784.615182s/966344704B; missing raw-System
replacement source861.683791s/978223104B; worker did not commit its claimed receipt
verifier, discovered at864.712460s/971894784B. All occurred after/before clearly stated
subsets and are not positive acceptance.

## Original dynamic miss

Fresh unchanged original22 q7 head remains epoch325/**2275J/24I**, CP SHA
`12896d47e08f4def76a8d324d99e3090a7c02e1683d72745abb60e40443cbac2`,
then genuine loaded-Program miss. Five successful q1 checkpoints resolve/invoke public
loadClass, enter ClassLoader method4 and commit PC1 before private native loadClass0.

Final epoch330/**2280J/24I**,15246B CP SHA
`e8868956423f79fdb69a7810beaa7fdbd6b92d948a97a47baa99a942b878207c`,
checkpoint root `5e50b5883256db753bf4b3959532b0dd2e7697b89983c373ed709ef8d3e02ec3`,
machine root `d02e7b9d9eef05688ac7e8b38afe7b313f882a9989d56d5d35c62624ecc0ab8f`.
Last gas151020773/max153731584. Next q1 returns ClassLoaderLoadError(2,1),
gas108042085, Head/root unchanged.330 canonical receipts pass.

Read-only checkpoint decoding proves the name is **`javax.servlet.Servlet`**. Parent
ZIP inventory proves it is absent from the pinned JAR. This is an optional
LoaderUtil.isClassAvailable probe and must become catchable guest
ClassNotFoundException, not a Solidity refusal. Next appends minimal
ReflectiveOperationException/ClassNotFoundException and maps missing binding8 status
to guest exception kind13; no lazy JAR class load/Class.forName. Archive10630 files
excludes original payload/LevelDB. No push/main-body/world/Done.
