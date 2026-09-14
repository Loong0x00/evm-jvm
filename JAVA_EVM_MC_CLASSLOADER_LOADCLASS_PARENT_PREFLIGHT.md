# Parent ClassLoader.loadClass preflight

**In progress; worker is not acceptance.** Worker72b850003/692e0e4d1/77185cca2
implements reviewed binding8 immutable Program lookup and correctly preserved its
first missing-loader, then un-published arena frontier ReferenceError failure. Final
worker publishes nextHandle/heap aliases and generated tests pass, but no whole
compiler+EVM peak exists.

Parent found one additional quota-path mismatch: shared `_classMirrorForTarget` returns
an OOM signal so ldc raises existing guest OOM kind7; worker dynamic lookup instead
converted it to LC0StateError. Parent returns the signal to binding8 and invokes the
same guest `_raiseJava(7)` before publishing state. No observed ordinary success path
is changed. Missing/malformed names remain explicit honest ClassLoaderLoadError.

Parent source-compiles777B abstract ClassLoader, uses new all-nine domains/address,
then runs one LOCAL384/1B20min4GiB combined load-without-init/canonical mirror plus
Boolean/System/resource prior gate and NEW original22 q7+q1. No Thread default or
Class.forName change, failed recovery, host loading, payload archive, push or Done.
Evidence parent-77185cca2.
