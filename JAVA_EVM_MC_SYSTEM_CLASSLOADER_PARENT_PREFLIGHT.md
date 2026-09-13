# Parent ClassLoader.getSystemClassLoader preflight

**Parent-verified LOCAL384 narrow native getter.** Not resource lookup, full
ClassLoader/JVM/Session or Minecraft startup. Evidence:
`evidence/java-evm/minecraft-entry/parent-bc4aa5f31/`.

Worker964258f2a/bc4aa5f31 candidate correctly adds public static native zero-arg
getSystemClassLoader, binding6, exact metadata/return validation, normal active-use
initialization, `_push` stack check and canonical existing-loader scan. Prior
native1..5 behavior remains. Parent renamed worker evidence `.go` to `.go.txt`,
restores unrelated `_classNameUnits` formatting, independently compiles the195B
ClassLoader image and rebuilds under new all-nine domain/address identity.

## Cap and pins

The unchanged320KiB builder **genuinely fails**. Same source under separately
labeled user-authorized LOCAL384KiB succeeds:

* ClassLoader195B SHA256
  `9a2d38f5b25e30aee6f0b494d23bba28aeb686ea8e338a21616b8ac6a6118f86`;
* LOCAL engine `0x4d432d5359534c4f414445522d504152454e5401`, domain
  `MC-SYSTEM-CLASSLOADER-PARENT1`;
* engine328695B SHA256
  `ec2a0ca639a7878752432f6390af14a69ebc7e767df0f9f4bc541ee9be4f43d3`,
  Keccak `90f8b0d4b4c3a0d3a968c50d190674c6e537df4256f5363e4b01e0fddc99459c`;
* ordinary-CREATE coordinator3547B, Keccak
  `744ed75c11fa95f3d655ee69bd0afee9d4b6d8dc278d10c21732a30b2591a7ba`.

Accepted320KiB remains unchanged; exact engine is LOCAL initial state only.
LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,128frames and all other caps unchanged.

## Generated and parent gate

Generated three raw mirrors and repeated system getter share the same nonnull
VMClassLoader; bootstrap mirrors remain null. Prior Thread/PrivilegedAction/
System/Properties/arraycopy controls pass. q1/q7/direct reach VOID332J/8I,
epochs332/48/1; machine/opaque agree.381 canonical receipts pass. Caller
VMClassLoader replacement rejects; `getResources` remains CallError(3,21).

Whole parent320 failure +384 build + generated + original:
**542.262533s/951513088B**, exit0. First parent script stopped in0.213718s because
its source assertion counted every unrelated `return 6;`; fixed to exact
ClassLoader descriptor/binding text. No Java/EVM failure hidden.

## Original committed frontier

Fresh original22 q7 successful head epoch257/**1799J/16I**, CP SHA
`2ca4649f32c5fc1f28c7f0d0544b651171e41e7c369fc0de74c5d73e78ea9c5e`,
then missing LinkedHashSet. Preserve failure; three q1 checkpoints commit:

*1800J: getSystemClassLoader returns canonical loader, findUrlResources PC34;
*1801J: stores third loader array entry, PC35;
*1802J: frame at PC36 before `new LinkedHashSet`.

Final13613B CP SHA
`8ca95d5d6893ea4a2080d135223da4c8c684fc7ded878fac4805d69546702252`, root
`7dc5fea5f375e17a4c31375d9db90f3265502f221bc0d208521475dab2ccaa52`,
last gas119782735/max121029535. Next q1 actual
`MCEntryMissingClass(4104,36,java/util/LinkedHashSet)`, gas85634932,
Head/root unchanged.260 canonical original receipts pass.

All three loader-array slots now hold real canonical loader identities; no empty
resource result exists. Next implement only minimal ordered Set/Collection/Iterator
hierarchy required to construct/iterate LoaderUtil result sets. No main-body/EULA/
listener/world/Done. Parent archive2671 allowlisted files excludes original JAR/
class/pages/LevelDB. No push; authorized remote remains1e4027b9b.
