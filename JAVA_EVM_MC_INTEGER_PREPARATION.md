# Measured Integer.parseInt bootstrap preflight

Parent java.version/split moves unchanged original22 from2536J to Constants
getMajorVersion PC16. Split has produced first component `"1"`; exact invokestatic
`java/lang/Integer.parseInt(String)I` now fails class resolution:
MissingClass(context0x100b=4107,site16,name=`java/lang/Integer`), selector555db429.

Append Java8 guest bootstraps, all compiled with `/usr/lib/jvm/java-8-openjdk/bin/javac
-source8 -target8 -g:none`:

* index68 `java/lang/Number`: public abstract Serializable Number with protected ctor,
  abstract int/long/float/double value methods and ordinary byte/short delegations;
* index69 `java/lang/NumberFormatException`: public unchecked exception extending the
  existing reserved IllegalArgumentException, with public default constructor;
* index70 `java/lang/Integer`: public-final Number/Comparable/Serializable wrapper,
  final value field, int/String constructors, int/long/float/double/byte/short values,
  equals/hash, compare/compareTo/bridge, MIN/MAX/SIZE/BYTES constants, and ordinary
  static `parseInt(String)I`.

`parseInt` implements Java negative-accumulation decimal parsing: optional +/- only,
null/empty/sign-only/non-digit/positive and negative overflow throw a newly allocated
guest NumberFormatException; valid MIN/MAX and leading-zero forms return exact int.
No host parser, native binding, radix overload, Integer cache/valueOf/toString claim.
Reserve all three bootstrap names against raw replacement. Total68→71; global native
bindings remain1..9, String-local10, exception registry/kinds remain14 because these
exceptions are constructed/thrown by ordinary guest bytecode, not a new native kind.
All prior68 images byte-exact, including parent-restored String constructors and exact
java.version/split images.

Generated q1/q7/direct/reopen/canonical: valid 1,8,+7,-0,MIN/MAX/leading zeros;
invalid cases caught as exact NFE and IAE, uncaught NFE lifecycle3 with decoded class;
Integer wrapper constructor/value/equals/compare/bridge; Number super catches/type;
raw Number/NFE/Integer and omitted radix/valueOf APIs refuse. Retain java.version and
split identity/internal/trailing/null/unsupported/OOM, forName/loadClass/CNFE and all
prior Boolean/System/EVM-ZI0/resource/URL/set/thread/PA/arraycopy controls.

Worker no original. Parent independently rebuilds images/engine and runs NEW original22
q7+q1. New engine/address/owner/store/all-nine domains/pins/worlds,LOCAL384 only;
accepted320 unchanged. LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,128frames,
CP4096Code65535,heap/VFS/CP1MiB,Head32768 fixed. No host parser/JAR loader, failed-
state recovery, core/ABI/Makefile/settings,push,main-body/world/Done. Terra/high, one
semantic writer, fresh absolute TMPDIR; q1 may be successful independent evidence with
fresh q7/direct equivalence inside the20min source/original gate, as measured compiler+
full q1 cannot fit serially but all invocations remain under4GiB/30s.
