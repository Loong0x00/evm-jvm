# Class.asSubclass LOCAL preflight

**PARENT RESULT:** accepted unchanged. Original passes asSubclass, fills raw24 and
requires a measured25th same-JAR class at3779J. See
JAVA_EVM_MC_CLASS_AS_SUBCLASS_PARENT_PREFLIGHT.md.


This is an **unaccepted**, evidence-only candidate from `73b3443c3`, based on the
accepted Integer parent source archive
`evidence/java-evm/minecraft-entry/parent-661331e3d/`.  It does not execute an
original JAR/class, Minecraft, a world, or main body.

## Candidate

Only the immutable bootstrap `java/lang/Class` image changes; bootstrap count remains
71 and every other 70 image is byte-identical.  The genuine Java 8 `-g:none` Class
image is 1015 bytes, SHA-256
`8986691ab80193f6958d7560a09f44b9dbacb22a30b317b905c811a2bf440ff7`.

Its ordinary public generic `asSubclass(Class)Class` wrapper calls exact private
static native `asSubclass0(Class,Class)Class`.  Global binding 10 is restricted to
that owner/name/descriptor/access `0x010a`, two Class references, and a Class
reference result; String-local bindings 1..10 are unchanged.

The native scans canonical Class mirrors through the existing owned Class layout,
name and defining-loader fields, rejecting forged/duplicate mirrors.  It first
materializes both hierarchy closures and uses `_typeAssignable`, including interface
closure.  It returns the first mirror unchanged on success.  Null parent raises the
existing NPE kind6; nonassignability consumes both arguments and raises catchable
existing CCE kind8.  It neither initializes a target nor allocates/advances the guest
frontier.

Candidate domain/address/owner are `MC-CLASS-AS-SUBCLASS-PREFLIGHT1`,
`0x4d432d434c4153532d41532d535542434c000001`, and
`0x4d432d434c4153532d41532d4f574e4552000002`.  Engine is 370032 bytes
(SHA-256 `2450cbbc9c011380e673b99ca3fd01691c2bc6ad51724c416448377eef89c7e9`,
Keccak `e9e294779df5565fcdab61fd1b3b2ba676e15501007dc3fedb2837c668c6254f`);
coordinator is 4146 bytes (Keccak
`c07a2fa2acece8ef4907c4ee3aee82bbe43a8ec2ebeefb103e4b58861f1347e7`).
This is below the authorized LOCAL384 cap; accepted320 is unchanged.

## Checks recorded

Focused Java8 raw-interface/interface-self/Boolean-to-Object, caught raw/bootstrap
CCE, superclass catch, null-parent NPE and repeated identity complete with the same
terminal machine root in q1/q7/direct: 84 Java + 5 internal steps, epochs 84/12/1.
A separate no-init target with throwing `<clinit>` completes (9 Java + 2 internal),
showing `asSubclass` did not initialize it.  Uncaught CCE is lifecycle3/kind8 with
matching machine root in q1/q7/direct (6 Java + 3 internal; epochs7/1/1).

Retained q7/direct controls complete at 4951 Java/32 internal (708/2 epochs), and
retained uncaught CNFE is kind13.  Integer/NFE q1/q7/direct replays retain the prior
2676/14 and 372/8 outcomes; the canonical verifier checks 717 retained and 3488
Integer receipt chains.  The inherited parent scripts initially could not resolve
`js-sha3` because this assigned worktree has no local `jvmevm/runtime/node_modules`;
the archived reruns use the pinned absolute `NODE_PATH` and pass.  This is a harness
path caveat, not a semantic failure.

Sources, artifacts, Java classes/resources, receipt/checkpoint archive, exact hashes,
and Go source (not a binary) are under
`evidence/java-evm/minecraft-entry/class-as-subclass-preflight/`.  The receipt archive
contains no LevelDB/state directory.  `tools/rebuild.py` source-builds into a fresh
ignored `build/java-diff-mc-class-as-subclass-*` directory using Java8 and solc
0.8.30 optimizer200/viaIR/Cancun/metadata-off.
