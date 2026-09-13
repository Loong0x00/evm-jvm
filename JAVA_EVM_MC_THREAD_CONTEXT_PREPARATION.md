# Next measured platform path: current Thread and context loader getter

Parent ClassLoader type profile commits original22 to1752J/14I. Its next exact
q1 error is missing owner `java/lang/Thread` at original
LoaderUtil$ThreadContextClassLoaderGetter.run PC0:

```
Thread.currentThread();
thread.getContextClassLoader();
```

Create an isolated **single guest thread** bootstrap, not a concurrency system:
a canonical guest Thread object returned by exact static currentThread, with a
nullable guest ClassLoader field returned by exact getContextClassLoader. The
profile has no installed/context loader, so ordinary guest default is null and
the original LoaderUtil fallback executes. This pair is one contiguous measured
original path; do not add setters, start/join/interrupt, ThreadLocal, scheduling,
AccessController, Class.getClassLoader, loader methods or fake resources.
Unsupported Thread APIs remain honest refusals. No original branch substitution.

Append after prior50 images, preserving all bytes/order and rejecting caller
replacement. Keep minimal ClassLoader type/constructor, PrivilegedAction,
System getter/arraycopy and Properties fix exact. New engine/address/all nine
domains/store/pins, no old-code CP. LOCAL initial-state engine only; other
contracts/resources ordinary CREATE.

Use authorized LOCAL1B,30s/call,25Mreserve,20min/4GiB and unchanged24/262144,
128frames,CP4096Code65535heap/VFS/1MiBCP/32768BHead/320KiB cap. Current engine
323026B leaves4654B; preserve any genuine cap failure, no silent increase.

Generated singleton identity, default-null context loader, repeated currentThread,
ClassLoader/PrivilegedAction/System/Properties/arraycopy controls, q1/q7/direct/
reopen/canonical receipts and explicit unsupported setter/start refusal. Worker
uses no original artifacts. Parent independently rebuilds and starts NEW original22
q7 then q1, credits only successful checkpoints. Expected later Class.getClassLoader
is explanatory only, not permission to implement it now. No host class evaluator,
failed-state recovery, accepted/core/ABI/Makefile/settings/push/Done claim.
DefaultTerra/high, one semantic writer, fresh absolute TMPDIR/no group escape.
