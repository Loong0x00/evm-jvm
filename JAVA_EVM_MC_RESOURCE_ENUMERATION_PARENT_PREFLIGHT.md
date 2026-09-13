# Parent EVM-index resource enumeration preflight

**Parent-verified LOCAL384 EVM-ZI0 presence bridge.** It supports one immutable
archive's empty/single Enumeration and URL identity only—not contents, openStream,
network URLs, full ClassLoader or Minecraft startup. Evidence:
`evidence/java-evm/minecraft-entry/parent-fdc55a341/`.

## Worker refusal and parent correction

Worker c604c4095/e1d8c0a90/fdc55a341 produced engine348319B/co4146B but its
probe's first operation was getSystemClassLoader before any raw Class mirror had
materialized the canonical loader. `LC0StateError(7,0)`, gas7272966, unchanged root
is therefore correct missing-loader rejection, not resource failure. Parent
independently reproduced it; a generated diagnostic variant first called raw
`Class.getClassLoader` and then completed266J/6I/static253 through present+missing
ZI0 paths. No failed state was reused.

Worker also accidentally changed ClassLoader access from public abstract to concrete.
Parent restores Java8 ACC_ABSTRACT and recompiles all four affected images:

* ClassLoader SHA `5df84572f2811ee34985319bfd1ad277277ec8f9958846534168e375370ae260`;
* Enumeration `2f40664fea8fdcc8105d92928ff21aa265b0b33193cbb1048f1636e457345adb`;
* URL `7ec786e74cb371710ea60693c37d8d1d65bcac270d00a728a121209e56929dfb`;
* VMResourceEnumeration `ed77d813a3f649ea2ced1beb9cccf798f689a03cdcc6f5f6071e04bd329165f6`.

ClassLoader.getResources is ordinary instance Java calling exact private static native
resourceExists(String) binding7. Binding validates0x010a, one reference argument,
boolean return and genuine guest String backing; ASCII1..256 only. Engine uses a
1M-gas staticcall while protecting25M reserve. The exact calling coordinator alone
revalidates engine, ZI0 code/phase/finalRoot/owner and calls immutable EVM
`finalIndex.lookup(bytes)`. A unique ZIP name yields zero or one URL. No host
catalogue/name list or hard-coded absence exists.

Guest Enumeration owns an independent consumed bit and throws existing NSEE when
exhausted. URL owns the resource name and implements equals/hashCode/toString for
LoaderUtil deduplication. openStream remains absent and returns CallError(3,22) in a
positive indexed-resource control.

## Pins and generated proof

* LOCAL engine `0x4d432d524553454e554d2d504152454e54000001`, all-nine domain
  `MC-RESOURCE-ENUMERATION-PARENT1`;
* engine348319B/44897B LOCAL384 headroom, SHA256
  `a119cdb383a57e8478d5ec0780e84e70a9d5a5d7e0b9f11832dacd12c59faeba`,
  Keccak `5183113f3979d284a00faf6cd2f3d70b5b613f716758e791fe87d485410250d6`;
* ordinary-CREATE coordinator4146B, Keccak
  `4b516bdd37573efe8eecd65eaafe7401abdeb963c300645e39c57545e7f6caa4`;
*64 bootstraps; accepted320 and all other LOCAL384/LOCAL1B limits unchanged.

Generated ZIP contains real `probe/resource.txt`. EVM proves true/exactly-one, false/
empty, two independent enumerations, distinct but equal URL values/hash/name,
exhaustion/NSEE, LinkedHashSet URL dedupe/growth/incoming-asymmetric-equals and prior
loader/Thread/PrivilegedAction/System/Properties/arraycopy paths. q1/q7/q4096 VOID
at3004J/14I, epochs3004/430/1, machine
`ac491309a15d44a07e28a1369f721e2d268f6a2f1d2cf4bbf6005ee16578ee83`, opaque
SHA `a7842775db8c84c8fbeb2c19a776fdb2a8a7bc54e7b781d560d2d93a0adedba6`.
3435 canonical receipts/reopens pass. Four changed/new raw replacements reject;
missing-loader and unsupported-openStream roots remain unchanged. Whole parent
source-build/generated/original gate: **762.351078s/959352832B**, exit0.

## Original frontier

Fresh unchanged original22 genuinely queries EVM ZI0 twice for
`log4j2.component.properties`; no entry exists, so both real enumerations are empty.
No URL/content object is substituted or opened. q7 reaches epoch297/**2079J/20I**,
CP SHA `e1b7096fa14c2a1d1296bfbd1286360aebbfdc7263eadafbfaa4a35b358b91eb`,
then CallError(3,3). Three q1 checkpoints commit PropertiesUtil/LoaderUtil returns to
raw PropertiesUtil method11 `getStringProperty(String)`, PC3.

Final epoch300/**2082J/20I**,14989B CP SHA
`44d43b7f4e8313093948bbd5c4b2b00a7a55283b4b43466f0f149c216a5a9d0e`,
checkpoint root `0f636bfff90550025e9ee95415abb981e0153e13283300629143ff5df07743f1`,
machine root `71a2ec8007fe2144ca8e0ce4ea58ebcbf11d534c837bd7f2686e98f25c4dbf30`.
Last gas144002518/max146501807. Next q1 repeats CallError(3,3), gas100463235,
Head/root unchanged.300 canonical original receipts pass.

PC3 is exact `System.getProperty(String)String`; caller key is LoaderUtil's
`log4j.ignoreTCL`. Next stage adds a real initially-empty guest Properties state to
System, not a key-specific null. Archive9100 allowlisted files excludes original
JAR/class/pages/LevelDB. No push; no main-body/EULA/listener/world/Done.
