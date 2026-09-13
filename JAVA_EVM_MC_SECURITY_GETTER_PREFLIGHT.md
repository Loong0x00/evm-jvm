# System.getSecurityManager preflight

**PARENT RESULT:** source-only build and generated proof pass. Fresh original21
moves from missing System member to missing LoaderUtil inner class; original22
then diagnoses missing java/security/PrivilegedAction. Successful original CPs
remain before LoaderUtil PC0, so no failed-call branch state is credited. See
JAVA_EVM_MC_SECURITY_GETTER_PARENT_PREFLIGHT.md. Worker claims below remain
historical evidence, not the parent proof.

This is a LOCAL-only, unaccepted derivative of the parent-c24d374bc Properties
repair and the authorized LOCAL1B driver basis. It addresses only the next
measured LoaderUtil linkage: `System.getSecurityManager()Ljava/lang/SecurityManager;`.

## Frozen scope

The candidate is materialized only below
`evidence/java-evm/minecraft-entry/security-getter-preflight/`; no repository
runtime, accepted artifact, ABI, quota, core, or original-Minecraft input is
changed. It compiles a minimal Java 8 `java/lang/System` bootstrap that retains
the existing native `arraycopy(Object,int,Object,int,int)` declaration and adds:

```java
private static SecurityManager security;
public static SecurityManager getSecurityManager() { return security; }
```

The field is ordinary guest static state and so has the JVM default null value.
No `SecurityManager` bootstrap class is supplied: the nullable reference
signature is sufficient for this getter. In particular there is no setter,
permission framework, `ClassLoader`, properties, resource enumeration, or
security bypass. A generated call to unsupported `setSecurityManager` is kept
as an explicit refusal control, while the normal generated branch only invokes
the getter and observes null.

All other 47 bootstrap image bytes/order must remain byte-identical to the
parent basis. The isolated build must use solc 0.8.30 viaIR/Cancun metadata-off,
make a new engine/coordinator pin/address/domain, remain at or below the LOCAL
320KiB engine cap, and use only ordinary EVM CREATE in its generated test
worlds. It retains the existing actual `MAX_FRAMES=128`; no frame cap is
changed. The generated-only harness uses the authorized LOCAL 1B external-call
ceiling while retaining 30s/call, 20min/4GiB group, and 25M reserve guards.

## Required evidence

`build_candidate.py` creates a fresh ignored `build/java-diff-mc-security-getter-*`
directory, compiles the bootstrap and candidate contracts, pins all hashes, and
builds an archived exact Go driver copy. `run_generated.py` then compiles only
its generated Java 8 fixtures and exercises null getter/normal branch,
arraycopy/Class/Properties controls, an untaken unsupported security branch,
and a separately executed honest unsupported setter refusal in q1/q7/direct
and fresh-reopen routes. It must validate canonical ABI/receipt and opaque
terminal equivalence. It does not accept or open any original JAR, original
class, resource page, LevelDB payload, or Minecraft world.

## Measured generated-only result

Guarded source rebuild produced a 338-byte System image
`2dbd8eb88dfc0ed82e0bf84e6a1c06e7530b666674c461e857416782e77bf49a`.
The 48-image inventory differs only at System. The resulting 322301-byte engine
is under 320KiB, SHA-256
`4a8aafbfafef9fed3c3fd3106d99b9819a40ecc2eccfe40e234efa448dc038f9`,
Keccak-256 `74609271d2d333b617e12d0c2ddeae2574b7812fc72f719453614acb3cc081ae`,
at `0x4d43534543555249545947455454455200000001`; the new coordinator Keccak is
`113bcbc2b3512af2cbddc90379dbc8cacfb64f7df50ef7ec8f89e1bdfe8ed59a`.

Generated Java 8 host oracles passed. Public EVM q1/q7/direct (4096) and fresh
reopen completed the getter's null branch at 169 Java/4 internal steps with the
same machine root
`0xb31df8efcb017db3178fda3d7d3d5a64a2a65fb09c543f611b757d05e6a70fcc`
and opaque-terminal SHA-256
`4e689631382a97b76ebc18690690416009e9db49ebe448c73234edb84d620727`.
They used 169/25/1 receipts respectively; all 195 canonical ABI/event/checkpoint
and EVM-read receipts verify. The largest slice used 24971680 gas (well within
the authorized 1B supplied-gas ceiling). The explicitly executed unsupported
setter instead retained `CallError(3,1)`, selector `0xd631c3a4`, at 5185129 gas
with unchanged root.

The guarded compiler/process groups completed: largest compiler RSS was
845804KiB (engine build, 194466ms), generated suite maximum 61976KiB and 8956ms
total; all retained 20-minute/4GiB whole-group and 30-second EVM-call limits.
Full sources, pins, receipts, generated checkpoints, logs and watchdog records
are in `evidence/java-evm/minecraft-entry/security-getter-preflight/`; no
LevelDB, Go binary, original JAR/class/resource page or Minecraft world is
archived.

Results are worker preflight evidence only. Parent source-only rebuild/replay
and a new parent-owned original21 probe are still required before any claim
that the original LoaderUtil frontier moved.
