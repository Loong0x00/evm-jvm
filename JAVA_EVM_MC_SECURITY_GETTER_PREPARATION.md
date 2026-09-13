# Next measured member: System.getSecurityManager

User authorized LOCAL1B external call budget and continued execution; see
JAVA_EVM_MC_LOCAL_BUDGET_AMENDMENT.md. Properties construction now genuinely
completes. Original21 reaches1715J12I and refuses CallError(3,0) while preparing
LoaderUtil's initializer; its first instruction is
System.getSecurityManager:()Ljava/lang/SecurityManager;.

Create an isolated derivative from parent-c24d374bc's repaired engine/coordinator
and local-budget-1b's actual1B bounded driver. Add the exact static getter to the
owned System bootstrap. Represent the VM's **no installed security manager**
default as genuine guest state (e.g. a private nullable static reference plus a
Java getter), not a replacement for original LoaderUtil or permission checks.
Java8 without an installed manager returns null; original ifnull branches then
execute normally. Unsupported setter/permission/security APIs must refuse, not
silently pretend installation or bypass checks. Do not implement a full security
manager, permission framework, ClassLoader, Thread, resource search or System
properties in anticipation. Avoid adding a SecurityManager class placeholder if
null reference descriptors already work; if actual generated linkage requires a
minimal type, document its exact required surface and preserve honest refusals.

Keep native System.arraycopy bytecode declaration and binding/arity intact;
retain all other47 bootstrap image bytes/order, Properties super.get repair,
actual128 runtime frame cap, class24/262144 and other limits. New engine/address/
domain/store/pins because bootstrap code changes; old-code CPs cannot be reused.
Engine is exact LOCAL initial state only; controllers/resources ordinary CREATE.
Gas budget1B is NOW authorized for LOCAL tests and original probes, still30s/call,
25Mreserve,20min/4GiB,320KiBengine and other existingcaps. Do not fall back to old
100M budget or ask permission again. Accepted/core/consensus artifacts untouched.

Generated Java8 TEST oracle, getSecurityManager null/default and branch behavior,
q1/q7/direct/reopen, real sentinels/events/canonicalCP/opaque equivalence plus
arraycopy/Class/Properties controls. Preserve genuine missing-API refusals.
No runtime worker handles original JAR/classes/worlds. Parent independently
rebuilds/replays before NEW original21. Own only new security-getter preflight
source/evidence/doc and fresh ignored builds. DefaultTerra/high, one semantic
writer, early commits, absoluteTMPDIR, no processgroup escape/LevelDB payload
archive/settings/push. Continue actual blockers, not broader JVM completion.
