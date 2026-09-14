# Bounded `Class.forName(String)` evidence

Generated-only LOCAL384 preflight from basis `e90909eae`.  The source changes only
bootstrap39 `java/lang/Class` (770 bytes, SHA256
`d63783800a1906528d2064fc40f740aaaceb616af8212c4d1a8db1da21791061`) and native
binding9.  The public Java wrapper calls private-static-native `forName0(String)`;
private fields/constructor/getters remain ordinary Java code.

Binding9 reuses dotted Program lookup. Missing/malformed names consume their argument
and raise guest CNFE kind13. For a present target it checks `initializationState == 2`
before allocating/returning a canonical mirror; otherwise it reverts the explicit
`ClassForNameInitializationError(target, pc)`, with no synthesized initialization.
No three-argument overload, archive loading or host class lookup exists.

`verify_source.py` proves all 67 other bootstrap image hex bodies are unchanged and
that all nine engine commitments are repinned to `MC-CLASS-FOR-NAME-PREFLIGHT1`.
`pins.json` records engine `359004B` (34212B beneath LOCAL384), coordinator and fixed
LOCAL address/owner hashes. The accepted320 profile is unchanged.

Generated direct tests cover missing, malformed, CNFE-super catch, initialized raw
mirror/loader identity, initialized Boolean bootstrap/null loader, uncaught kind13,
and explicit uninitialized/raw-replacement/omitted-overload refusals. Reopened q1/q7
receipts show terminal machine roots equal to direct for missing, initialized target
and uncaught CNFE. `monitor-*.json` observes a 39,424,000-byte maximum single-process
RSS; every invocation remains under the 20-minute/4GiB LOCAL guard. Receipts include
only generated checkpoints and no LevelDB, original payload, or Go binary.

This is not dynamic class initialization, lazy archive loading, original-JAR execution,
Minecraft main-body execution, world creation, or Done.
