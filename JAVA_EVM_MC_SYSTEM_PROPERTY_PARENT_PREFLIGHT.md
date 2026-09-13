# Parent System.getProperty preflight

**In progress; worker is not acceptance.** Worker b101bc564/f2b983a2c/b6d030f95
correctly replaces System with private initialized Properties and exact getProperty,
but its empty-key proof supplies IllegalArgumentException as an ordinary raw class.
The unchanged original bundle has no such raw binding, so worker's claimed Java8
empty-key behavior is not self-contained. Parent appends the direct minimal IAE
class as reserved bootstrap65 and proves the same EVM fixture without raw IAE.

Parent otherwise preserves worker System image semantics: null key dereference NPE,
empty IAE, real initially-empty guest Properties lookup, security null and native
arraycopy. No key hard-code, host/-D source, property setter/getProperties/clear or
other System surface. Other64 images stay exact; new all-nine domains/address/store.

Generated combined actual-ZI0 resource, URL/Set/loader/prior controls plus System
missing/repeated/null/empty paths run q1/q7/direct/reopen/canonical; unsupported
System APIs/openStream and raw System/IAE replacements refuse. One LOCAL384/
LOCAL1B20min4GiB gate then NEW original22 q7+q1. No failed recovery, payload archive,
core/ABI/Makefile/push/Done. Evidence parent-b6d030f95.
