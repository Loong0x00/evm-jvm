# System.getSecurityManager preflight

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

Results are worker preflight evidence only. Parent source-only rebuild/replay
and a new parent-owned original21 probe are still required before any claim
that the original LoaderUtil frontier moved.
