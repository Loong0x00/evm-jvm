# Measured java.version + String.split preflight

Parent forName advances unchanged original22 to Constants.getMajorVersion PC9. Guest
System properties are still empty: ldc `java.version`; getProperty returns null; ldc
`-|\\.`; exact invokevirtual `String.split(String)String[]` is unresolved and reports
StringProfileError(1,9). Java Constants' exception table begins at PC13, so merely
reordering dispatch to produce null-receiver NPE would fail class initialization and
is not useful startup semantics.

Replace only existing System and String bootstrap images (no append,total68):

* System remains a real private static guest Properties table, but `<clinit>` now
  inserts exactly `java.version`=`1.8` with ordinary `Properties.setProperty` bytecode.
  No host/`-D` channel or any other names. Existing absent/null/empty semantics stay.
* String retains fields, constructors and native methods1..9; append public-native
  exact `split(String)String[]` as **String-local binding10** (global native bindings
  remain1..9). Native metadata and descriptor/access must be exact.
* Binding10 accepts only regex units `-|\\.`. Other regexes explicitly refuse a
  narrow StringProfileError code; no Pattern/regex claim. Null receiver and null regex
  guest-raise NPE kind6 by Java invocation precedence.
* For the accepted regex, split UTF-16 receiver on literal `-` or `.`, preserve empty
  internal components, discard all trailing empty components (limit0), return the
  receiver in a one-element String[] when no delimiter matches, and return one empty
  receiver element for empty input. Allocate non-interned substring String objects
  with owned char[] backings plus a rank1 String[]; enforce MAX_OBJECTS/ARRAYS/
  ARRAY_LENGTH/ELEMENTS/FIELD_SLOTS/HANDLES before writes where practical and guest-
  raise OOM kind7. Publish arena heap/frontier exactly. Do not put derived substrings
  in the intern pool or fake identity.

Generated q1/q7/direct/reopen/canonical: System java.version exactly1.8; split gives
[1,8], internal empties/trailing removal, no-match receiver identity and empty-input
shape; null receiver/regex catch guest NPE; unsupported regex/root-atomic refusal;
quota-edge OOM kind7 if harness permits. Retain forName caught/initialized identity/
uninitialized refusal/uncaught kind13, loadClass, Boolean/System absent+IAE, genuine
EVM-ZI0 resource/URL/set/loader/thread/PA/arraycopy, raw System/String and omissions.

Worker no original artifacts. Parent independently source-builds Java8 `-g:none`, then
NEW original22 q7+q1. Further Integer.parseInt (visible at Constants PC16) is
explanatory only until measured after split. New engine/address/owner/store/all-nine
domains/pins/worlds,LOCAL384 only; accepted320 unchanged. LOCAL1B/30s/25Mreserve/
20min4GiB,24/262144,128frames,CP4096Code65535,heap/VFS/CP1MiB,Head32768 fixed.
No host properties/regex/JAR loader, failed-state recovery, core/ABI/Makefile/settings,
push, Minecraft main-body/world/Done. Terra/high, one semantic writer, absolute fresh
TMPDIR and one persistent whole-process-tree peak.
