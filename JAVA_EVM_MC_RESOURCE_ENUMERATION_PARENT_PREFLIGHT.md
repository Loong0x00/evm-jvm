# Parent EVM-index resource enumeration preflight

**In progress; worker failed prototype is not acceptance.** Worker
c604c4095/e1d8c0a90/fdc55a341 compiled the narrow bridge but its probe called
getSystemClassLoader before any raw Class mirror had materialized the canonical
VMClassLoader. The resulting LC0StateError(7,0) is correct missing-loader rejection,
not a resource/state implementation failure. Parent independently reproduced it,
then a diagnostic-only generated variant first called its raw class's getClassLoader
and reached VOID266J/6I with static253: actual indexed present/missing paths work.
Failed worker state is never reused.

Parent also found worker source accidentally changed ClassLoader from public abstract
to concrete. Parent restores ACC_ABSTRACT and recompiles all four Java images;
ordinary instance getResources + exact private-static-native resourceExists binding7
remain. It independently reviews bounded guest String conversion,1M-gas staticcall,
exact bool ABI, coordinator ENGINE guard and ZI0 code/phase/finalRoot/owner/lookup.

Parent uses new all-nine domains/address/store and LOCAL384. Generated positive ZIP
contains a real non-class resource and covers raw-mirror loader materialization,
positive/absent Enumeration, URL identity/hash/string, duplicate Set behavior,
exhaustion, prior set asymmetric equals/growth and all earlier blockers. Changed/
new raw replacements, missing-loader and unsupported openStream are negative gates.
Then only a NEW original22 q7+q1 is permitted. No hard-coded absence, host catalogue,
content decoder, openStream, broad URL/network, failed recovery, push or Done.
Evidence: evidence/java-evm/minecraft-entry/parent-fdc55a341/.
