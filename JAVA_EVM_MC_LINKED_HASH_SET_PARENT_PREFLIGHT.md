# Parent LinkedHashSet preflight

**Parent-verified LOCAL384 bounded ordered-set family.** Not full Collections,
resource contents or Minecraft startup. Evidence:
`evidence/java-evm/minecraft-entry/parent-7625023ff/`.

## Parent correction and scope

Worker commits6c7a5a950/4735e71b4/7625023ff appended nine images after the
byte-identical prior52: Iterator, Collection, Set, AbstractCollection, AbstractSet,
HashSet, LinkedHashSet, package HashSetIterator and NoSuchElementException. All
nine names reject raw replacement. The actual Java8 public hierarchy is retained.

Parent found worker HashSet used `old.equals(item)`. Java8 HashMap.putVal, which
backs HashSet, tests incoming `key.equals(stored)`. Parent changed the one source/
image to `item.equals(old)` and proved it with equal-hash asymmetric Old/New
objects on Java8 and EVM. Worker image SHA24c876... becomes corrected HashSet
SHA `0500daf6cbbb519e65f90aeda5affb794e14b2fceaa8f119239ff8d532850b4a`;
the other eight generated images are byte-identical to worker pins.

The minimal set stores Object[] linearly, allows one null, rejects reference or
incoming-virtual-equal duplicates, grows via genuine System.arraycopy, preserves
insertion order and creates independent iterators; exhausted next throws the
real guest NSEE. Only add/size/isEmpty/iterator/hasNext/next plus ()/(I)
constructors are claimed. remove remains CallError(3,8), root unchanged.

## Pins and generated proof

* LOCAL engine address `0x4d432d4c48532d504152454e5400000000000001`,
  domain `MC-LINKED-HASH-SET-PARENT1` in all nine engine domains;
* engine340269B (52947B LOCAL384 headroom), SHA256
  `3f47b7ee723f037ef63d595917abc53d85917dae476502a3ad799de611daa917`,
  Keccak `a12d5acd97e7d1237027d4f9f3dec49a460dd6578a0cd82138fa0310cd9e18db`;
* ordinary-CREATE coordinator3547B, Keccak
  `bb7fc9ea7cae11881f2f0a7e43831709ab067824f0e18e57b550410d3c85795e`;
*61 bootstrap +24 raw max; accepted320 remains unchanged. LOCAL1B/30s/25M
  reserve,20min/4GiB,128frames,262144rawbytes and all other caps unchanged.

Parent generated fixture covers noarg/int0/int2, two growths, ordered/equal/null/
asymmetric uniqueness, Collection/Set dispatch, two cursors, exhaustion/NSEE,
and prior canonical system/defining loader, Thread, PrivilegedAction, System,
Properties and arraycopy paths. q1/q7/q4096 all VOID at2768J/13I, epochs
2768/396/1, machine root
`902bcb248914be610d58bc162e59c9382543c86f44ce5b0a2dff5f6d56faebc3`,
opaque SHA `25b0908b3e62f28b75e778131917945baebebd11b25f82db85afc82d6c5c1e44`.
3165 canonical receipts and every fresh-process reopen pass; all nine replacement
controls reject BootstrapProfileError(1,1).

Worker preserved two development failures: missing fixture hashCode and stale
coordinator engine address/MR0Error(3). Parent transparently preserves three
harness failures: first omitted continue.py (477.585675s/944553984B), second
continue.py imported the old <=76 diagnostic parser (476.414133s/950116352B), and third reused
an existing smoke output after a successful203.923729s/948387840B source build.
A shell invocation typo `bash Lash` is also preserved (0.106449s). These are not
semantic/EVM acceptance. Final fresh execution gate succeeds in
336.933069s/162369536B using that exact independently built engine.

## Genuine original frontier

Fresh unchanged original22 q7 reaches epoch264/**1848J/19I**, CP SHA
`2bc630db65662731f27edffe2d9bc18f312581bb5f4f73465883d8acfb960a5e`,
then `CallError(3,74)`. This means LinkedHashSet allocation/initialization and loop
setup succeeded; no ClassLoader resource answer occurred. After preserving q7,
two q1 checkpoints commit:

*1849J: findUrlResources frame PC73 with loader reference on stack;
*1850J: PC74 with loader and resource-name String, immediately before invokevirtual
 `ClassLoader.getResources(String)Enumeration`.

Final epoch266,13895B CP SHA
`1ebdaac1c28bd24fa85343ff19d6d64874b3a11b632ade0c1bb69e68e18acb35`,
checkpoint root `62615a3cfb8f7fe3dbdba3fae84a05080faa0a4ca4e5a2fdb446ce4ef4a0fce8`,
machine root `d11af7c32928e85deeb241eff27d6f2129f811ad81074ac7087493b0f4664339`.
Last gas128927814/max133920837. Next q1 repeats exact CallError(3,74), gas91705847,
root/Head unchanged.266 canonical original receipts pass.

Next stage must query the genuine EVM ZI0 index via coordinator for resource
presence and provide real Enumeration/URL guest identity; it must not hard-code
absence. The current requested `log4j2.component.properties` is absent from the
pinned JAR according to parent host inventory, but only an EVM lookup may govern
execution. URL.openStream/content decode remains later measured work. No original
payload/LevelDB in archive, no push, no main-body/EULA/listener/world/Done.
