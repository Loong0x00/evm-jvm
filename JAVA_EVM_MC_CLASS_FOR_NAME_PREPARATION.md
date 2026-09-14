# Next measured Class.forName(String) preflight

Parent CNFE makes ClassLoader.loadClass's `javax.servlet.Servlet` miss catchable.
Unchanged original22 commits to2283J/25I at raw LoaderUtil.loadClass PC21, exact
fallback `Class.forName(String)Class`; same absent binary-name String remains on stack.

Replace existing guest Class image at bootstrap39 only:

* add public static `forName(String)Class throws ClassNotFoundException` as ordinary
  Java calling exact private-static-native `forName0(Ljava/lang/String;)Ljava/lang/Class;`;
* native binding9 only; preserve1..8. Validate exact Class/name/descriptor/access,
  one String reference argument, Class reference return, active-use initialization
  and stack capacity.

Reuse binding8 dotted immutable-Program lookup, CNFE kind13 and mirror/OOM/frontier
logic. Extend lookup return to include matched target index. Missing or malformed names
raise catchable guest CNFE exactly as loadClass. **Do not fake Java initialization:**
for a present target, binding9 may return its canonical mirror only when target
initializationState is already2; an uninitialized present target must explicitly reject
with a narrow ClassForNameInitializationError until a real dynamic initialization
continuation is measured/implemented. Current original target is absent, so that branch
is not taken. No `forName(String,boolean,ClassLoader)` overload.

Generated q1/q7/direct/reopen/canonical: missing/malformed forName caught as CNFE and
ReflectiveOperationException; pre-initialized raw target returns canonical mirror and
loader identity; uninitialized target honest refusal; absent uncaught terminal kind13.
Retain loadClass present/no-init, Boolean/System/IAE, true/missing EVM resource/URL/set/
loader/thread/PA/arraycopy controls. Raw Class replacement and omitted overload reject.

No images appended,total68; other67 bytes/order,exceptionkind14,native1..8,ClassLoader
mirror/guestOOM/CNFE and ZI0 coordinator remain exact. New engine/address/owner/store/
all-nine domains/pins/worlds under existing LOCAL384 only; no >384 absent actual
failure. Accepted320 unchanged. LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,
128frames,CP4096Code65535,heap/VFS1MiB,1MiBCP,32768BHead fixed.

Worker accesses no original artifacts. Parent independently source-builds then NEW
original22 q7+q1. Further optional class names, real archive class loading or dynamic
initialization are explanatory only. No host loader/catalogue, fake Class, failed-state
recovery, core/ABI/Makefile/settings/push/main-body/world/Done. Terra/high, one semantic
writer, fresh absolute TMPDIR and one persistent true whole process-tree peak.
