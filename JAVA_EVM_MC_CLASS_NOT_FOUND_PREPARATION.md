# Next measured catchable ClassNotFoundException preflight

Parent loadClass reaches binding8 in unchanged original22. Successful checkpoint
decoding proves requested binary name is exactly `javax.servlet.Servlet`; parent ZIP
inventory confirms that class is absent from the pinned vanilla server JAR. Current
loaded-Program search correctly reports no match, but its explicit
ClassLoaderLoadError is not catchable Java. LoaderUtil.isClassAvailable requires real
ClassNotFoundException to return false for optional APIs.

Append exact minimal Java8 hierarchy after prior66:

* index66 `java/lang/ReflectiveOperationException extends Exception`;
* index67 `java/lang/ClassNotFoundException extends ReflectiveOperationException`.

Reserve both names. Default constructors suffice for VM-owned exception allocation;
ClassNotFoundException may expose standard getException/getCause null state, but do not
build reflection or full Throwable messages. Extend exception-kind registry from13 to14
and map kind13 to bootstrap67 using its pinned offset from Throwable. Reuse existing
VM exception allocator/unwind/catch machinery.

Change binding8 lookup status only: valid unique match still returns canonical mirror
without initialization; allocator quota still raises guest OOM; missing or malformed
binary name raises guest kind13 at the native call PC after consuming its argument.
No null/fake Class, host/JAR loading, explicit Solidity missing error or failed-state
continuation. Existing custom ClassLoaderLoadError may remain only for impossible
internal duplicate/malformed-state conditions.

Generated q1/q7/direct/reopen/canonical must catch CNFE for absent and malformed names,
verify exact/subclass catch identity/null legacy cause if exposed, and separately prove
present raw/bootstrap loadClass mirror identity/non-initialization. Uncaught CNFE must
commit genuine Java terminal exception rather than EVM refusal. Retain combined
Boolean/System/resource/URL/set/loader/thread/PA controls and all reservations; raw
replacement of both new classes rejects.

Append two images,total68; prior66 bytes/order,ClassLoader777B,binding1..8,mirror
frontier/OOM repair and ZI0 coordinator remain exact. New engine/address/owner/store/
all-nine domains/pins/worlds under current LOCAL384 only; no >384 absent failure.
Accepted320 unchanged. LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,128frames,
CP4096Code65535,heap/VFS1MiB,1MiBCP,32768BHead fixed.

Worker no original artifacts. Parent independently source-builds then NEW original22
q7+q1. Expected further optional checks or actual not-yet-loaded archive class are
explanatory only; do not implement Class.forName, lazy Program growth or broader loader
now. No fake output, host catalogue, failed recovery, core/ABI/Makefile/settings/push/
main-body/world/Done. Terra/high, one semantic writer, fresh absolute TMPDIR and one
persistent true whole process-tree peak.
