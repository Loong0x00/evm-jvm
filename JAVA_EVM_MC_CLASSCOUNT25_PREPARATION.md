# Measured raw-class-count25 preparation — authorization required

Current explicit profile cap is24 raw classes. Parent asSubclass exhausts all24 with
226585/262144 bytes and then unchanged original22 genuinely requires same-JAR
`org/apache/logging/log4j/message/ParameterizedNoReferenceMessageFactory.class`
(1488B) at StatusLogger `<clinit>` PC47. A25-class package would be228073B, still
inside the unchanged byte cap.

The measured minimal amendment is **24→25 classes only**:

* engine `MAX_RAW_CLASSES=25` and the first class-count word in its execution-config
  commitment becomes25; total-byte cap remains262144;
* coordinator fixed decoder/root/size/name arrays and `n` guard become25;
* local durable driver manifest/input guards become25;
* read-only checkpoint diagnostic total-class bound becomes at least96
  (raw25+bootstrap71), not a guest limit;
* append only the measured same-JAR class to the24-name original inventory; no class
  bytes in source/evidence and no host execution path.

All generated controls include exact24 success, exact25 success,26 refusal,25 classes
with262145 bytes refusal, aggregate228073-byte boundary accounting, reordered/package
commitment distinction, q1/q7/direct/reopen/canonical. Retain Class.asSubclass,
Integer, split, CNFE and all prior controls. New engine/coordinator/address/owner/store/
all-nine domains/worlds under LOCAL384; accepted320 and the accepted24 artifacts remain
unchanged. No lazy loading, capacity beyond25, byte-cap change or fabricated class.

Parent then source-builds and starts a NEW original25 world q7+q1. LOCAL1B/30s/25M
reserve/20min4GiB,128frames,CP4096Code65535,heap/VFS/CP1MiB,Head32768 remain fixed.

This file is preparation only. Because24 was an explicit standing limit, do not start
a semantic worker or modify it without user authorization. Alternative lazy archive
Program growth is much broader and is not proposed yet. No main-body/world/Done.
