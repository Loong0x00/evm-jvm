# Class.asSubclass preflight (active work)

This isolated LOCAL preflight starts from the accepted parent Integer source snapshot
`evidence/java-evm/minecraft-entry/parent-661331e3d/`.  It replaces only the
bootstrap `java/lang/Class` image and adds global native binding 10 for the
private static primitive below.  The public generic wrapper remains ordinary
Java 8 bytecode.

This directory is evidence-only and is not an accepted runtime change.  It does
not include original server classes, JAR payloads, worlds, LevelDB, or a Go
binary.  The eventual build is constrained to the user-authorized LOCAL 384 KiB
runtime cap and 1B external-call budget; accepted 320 KiB remains unchanged.
