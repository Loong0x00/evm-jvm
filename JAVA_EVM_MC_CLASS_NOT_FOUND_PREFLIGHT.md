# Catchable `ClassNotFoundException` preflight

This active LOCAL384/LOCAL1B preflight is restricted to an immutable-Program
`ClassLoader.loadClass(String)` miss.  It is not `Class.forName`, archive/JAR
loading, general reflection, a broad loader API, Minecraft main-body execution,
or a Done claim.

The parent `MC-CLASSLOADER-LOADCLASS-PARENT1` checkpoint proves that the first
unchanged original22 miss is the absent binary name `javax.servlet.Servlet`.
The required outcome is a guest Java `ClassNotFoundException` (CNFE) that
`LoaderUtil.isClassAvailable` can catch, not a Solidity `ClassLoaderLoadError`.

Implementation and measured evidence are archived only below
`evidence/java-evm/minecraft-entry/class-not-found-preflight/`.  Prior engine,
coordinator, bootstrap, and resource commitments remain immutable inputs until
the new source build pins them.

## Frozen semantic delta

1. Append, without changing any of the 66 prior bootstrap bytes or positions:
   `java/lang/ReflectiveOperationException extends Exception` at 66, and
   `java/lang/ClassNotFoundException extends ReflectiveOperationException` at
   67.  Both are minimal Java-8 default-constructor images and both names are
   reserved from raw replacement.
2. Make the exception-kind table 14 entries and map kind 13 to
   `throwableBootstrapAt + 62` (the CNFE image). Existing exception hierarchy
   and layout validation plus `_raiseJava` allocation/unwind are mandatory.
3. Binding 8 keeps exact valid unique immutable-Program lookup, canonical class
   mirror identity, no initialization, and guest OOM handling. A missing class
   or invalid dotted binary name consumes its argument and calls `_raiseJava(13)`
   at the native call PC. Internal duplicate/malformed VM state may retain its
   hard error.
4. After either an allocated mirror or a raised exception, publish the arena
   frontier/heap state by the existing mechanism; a miss must never be a fake
   null result or an EVM refusal.

Generated proof must cover present raw/bootstrap mirror identity and
non-initialization; missing and malformed names caught as exact CNFE and as
its reflective-operation superclass; uncaught CNFE terminal lifecycle 3;
q1/q7/direct/reopen/canonical equality; both new raw-reservation refusals; and
all retained Boolean/System/IAE/resource/URL/set/loader/thread/PA/arraycopy
controls.  LOCAL384 is the only allowed build ceiling; accepted 320KiB and all
existing VM/EVM limits remain unchanged.
