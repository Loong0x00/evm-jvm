# Parent System.getProperty preflight

**Parent-verified LOCAL384 initially-empty guest property state.** Not host System
properties, mutable launch options, full Java SE or Minecraft startup. Evidence:
`evidence/java-evm/minecraft-entry/parent-b6d030f95/`.

## Parent correction

Worker b101bc564/f2b983a2c/b6d030f95 correctly replaced fixed System image with:
private nullable SecurityManager, private static `new Properties()`, native arraycopy,
getSecurityManager and getProperty. getProperty dereferences key.length (null=>NPE),
throws default IAE for empty, then calls genuine Properties.getProperty. No property
names/host values are hard-coded; no-D local launch starts empty. No setters,
getProperties, clear or security mutation.

But worker's empty-key test supplied IllegalArgumentException as an ordinary raw input.
The unchanged original22 bundle does not bind that class, so its claimed behavior was
not self-contained. Parent appends exact159B public IAE/RuntimeException image as
bootstrap65 and reserves it. The same empty-key EVM test then passes without raw IAE.
Worker System image remains byte-exact704B/SHA
`6a5720789022cc778afa5c9d7606934d9a5988add0cd8dbc719cb495b1901689`;
IAE SHA `3f99eea34cd5183c2d11ecc9079247e7043513b55061844559306d32106bebcb`.

## Pins and generated proof

* LOCAL engine `0x4d432d53595350524f502d504152454e54000001`, domain
  `MC-SYSTEM-PROPERTY-PARENT1` in all nine embeds;
* engine348423B/44793B LOCAL384 headroom, SHA256
  `03914b83a8c060ac78a97417f1fbee5ee173538c694e374678e32aa6bc9683fb`,
  Keccak `0d7f266fba7395a3c251125826d6eee3a76ae740dddddc0e163929b6cbdfbe82`;
* ordinary-CREATE coordinator4146B, Keccak
  `9f5a910a69e1cb90b17cd1be876c4f1edc00bc50a3dcb175ab5184977cd5c1f2`.

Generated combined fixture performs missing/repeated getProperty, null NPE, empty IAE,
System clinit/security/arraycopy/independent Properties, genuine present+missing EVM
ZI0 resource/URL, ordered-set growth/asymmetric equality and loader/thread/PA paths.
q1/q7/q4096 are VOID3156J/18I, epochs3156/451/1, machine
`6b8bae662ab720fc3bac57a88574337d86d6f9810479f5b9c76fdc4a2da7ea2a`, opaque
SHA `9f11b9332230079d3ed98c8326f4bbf45e16932e195e95cb7f988fcf4e640897`.
3608 canonical receipts/reopens pass. get/set/clearProperties and URL.openStream remain
exact CallError refusals; raw System and bootstrap IAE replacement reject. Whole gate
**812.172270s/957775872B**, exit0. Initial parent build correctly compiled engine but
its driver replacement expected worker-final rather than reproducible resource-basis
domain; assertion failed215.644610s/951451648B and is preserved, not credited.

## Original frontier

Fresh unchanged original22 uses the real empty guest table to return null for
`log4j.ignoreTCL`, then follows LoaderUtil's default false branch. q7 reaches
**epoch315/2205J/22I**,14992B CP SHA
`119bebc835a7ba6f6169627a3142c2cec959bfa833af51d5601abfda4765e89f`,
checkpoint root `8a4a17450f5e8f44f701e3c378c4e0e0928ea1d1c172671d050408671e60e7ed`,
machine root `489bef23771c1ece6ac9fddd9e6fc2cf5cac8c03f37e2bffd1ed847890338a0b`.
Last successful gas147115920/max150774184.

Both q7 and next q1 fail unchanged with
`MCEntryMissingClass(4107,37,java/lang/Boolean)`, gas101395992. Frame is raw
LoaderUtil method8 isIgnoreTccl PC37, exactly `Boolean.valueOf(false)`; no failed-state
recovery and no q1 checkpoint. Next append minimal canonical Boolean TRUE/FALSE/
valueOf/booleanValue wrapper. Archive9552 allowlisted files excludes original payload/
LevelDB. Accepted320/LOCAL384/LOCAL1B and all other limits unchanged. No push, no
main-body/EULA/listener/world/Done.
