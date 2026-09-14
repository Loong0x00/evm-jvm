# Measured Class.asSubclass preflight

Parent Integer moves unchanged original22 to AbstractLogger.createClassForProperty PC36.
LoaderUtil has returned the canonical raw mirror for
`org/apache/logging/log4j/message/ReusableMessageFactory`; ldc supplies canonical raw
`MessageFactory.class`. Exact invokevirtual
`Class.asSubclass(Class)Class` refuses CallError(3,36), selector d631c3a4.

Replace existing bootstrap Class image only; no append,total71:

* add ordinary public generic `asSubclass(Class)Class`, delegating to exact private-
  static-native `asSubclass0(Class value,Class parent)Class`;
* assign **global native binding10** (String-local split binding10 is a separate
  namespace). Preserve global1..9 and String-local1..10.
* Validate exact Class owner/name/descriptor/private-static-native access, two Class
  reference arguments and Class reference return. Ordinary invokevirtual preserves
  null receiver and Class active-use semantics.
* Native maps both canonical guest Class mirrors uniquely back to immutable Program
  class indexes through owned name/layout fields. Null parent guest-raises NPE kind6.
  Use full `_typeAssignable` (superclass plus interface closure), not only parentLinks.
  On success return the identical first mirror with no initialization/allocation. On
  failure consume arguments and guest-raise existing ClassCastException kind8 through
  normal handlers/terminal state. Do not fake casts or accept forged/noncanonical
  mirrors.

Generated q1/q7/direct/reopen/canonical: raw ReusableMessageFactory.asSubclass(raw
MessageFactory) succeeds with same mirror/loader; interface self; bootstrap Boolean as
Object; nonassignable raw/bootstrap exact CCE and super catch; null parent NPE;
uncaught CCE lifecycle3/kind8; repeated identity/no initialization. Raw Class
replacement and omitted isAssignableFrom/cast/newInstance refuse. Retain Number/NFE/
Integer parse/wrapper/uncaught, java.version/split/OOM, forName/loadClass/CNFE and all
prior controls. No new bootstrap/exception kind; Class compiled genuineJava8-g:none;
other70 images byte-exact, including String/System/Number/NFE/Integer.

Worker no original artifacts. Parent source-builds then NEW original22 q7+q1. Class
newInstance visible later in AbstractLogger is explanatory only. New engine/address/
owner/store/all-nine domains/pins/worlds,LOCAL384; accepted320 unchanged. LOCAL1B/30s/
25Mreserve/20min4GiB,24/262144,128frames,CP4096Code65535,heap/VFS/CP1MiB,Head32768
fixed. No host reflection/class loader, target init, failed recovery, core/ABI/Makefile/
settings,push,main-body/world/Done. Terra/high, one semantic writer,fresh TMPDIR and
persistent whole-process-tree peak.
