# Next measured java.lang.Boolean preflight

Parent self-contained System.getProperty reaches unchanged original22 epoch315/
2205J/22I. Exact next q1 is
`MCEntryMissingClass(4107,37,java/lang/Boolean)` in LoaderUtil.isIgnoreTccl PC37,
immediately after real initially-empty System properties returned null for
`log4j.ignoreTCL`. Bytecode requires Boolean.valueOf(false), caches the object, then
later booleanValue().

Append one genuine bounded Java8 Boolean image after prior65 and reserve its name.
Preserve actual public-final hierarchy implementing Serializable and Comparable<Boolean>.
Required core:

* public static final canonical TRUE/FALSE initialized by clinit;
* public Boolean(boolean), static valueOf(boolean), booleanValue();
* standard equals, hashCode1231/1237, instance/static toString, compare/compareTo if
  included to preserve the small wrapper contract and bridge behavior.

Do not implement parseBoolean/getBoolean/String constructor/TYPE primitive mirror or
full wrapper/runtime. Generated tests must verify TRUE/FALSE/valueOf identity,
constructor distinctness/equality, primitive values, hashes/strings, Comparable bridge
if present, clinit/reopen, and raw replacement refusal. Retain System missing/repeated/
null/empty with bootstrap IAE, positive/missing EVM-index resource+URL, ordered set
asymmetry, loader/thread/PA/security/Properties/arraycopy controls; q1/q7/direct/
reopen/canonical. Unsupported omitted methods remain honest.

New engine/address/owner/store/all-nine domains/pins/worlds. Existing LOCAL384 only;
record runtime/headroom, do not exceed384 absent actual failure. Accepted320 unchanged.
LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,128frames,CP4096Code65535,
heap/VFS1MiB,1MiBCP,32768BHead fixed. Append Boolean at65; other65 images/order,
native1..7,ZI0 coordinator,ClassLoader abstract,HashSet/System repairs remain exact.
Coordinator ordinary CREATE with new pin/domains; engine LOCAL initial state.

Worker accesses no original artifacts. Parent independently source-builds generated
controls then NEW original22 q7+q1. No host Boolean substitution, fake output, broad
Java SE, failed-state recovery, core/ABI/Makefile/settings/push/main-body/world/Done.
DefaultTerra/high, one semantic writer, absolute fresh TMPDIR and one persistent true
whole process-tree peak.
