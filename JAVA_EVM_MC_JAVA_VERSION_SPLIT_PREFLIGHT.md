# Java version property and bounded String split preflight

Local-only continuation from `d183da5ab`, scoped to the preflight evidence at
`evidence/java-evm/minecraft-entry/java-version-split-preflight/`.  This replaces
only the existing guest System and String images: System constructs a real guest
Properties and inserts `java.version=1.8`; String adds its exact public native
`split(String)String[]` surface through a String-local binding 10.  It does not
provide host properties, a regex engine, a JAR loader, or general Java support.

The bounded split accepts exactly Java's `"-|\\."` UTF-16 regex units. It splits on
literal `-` and `.`, retains internal empty strings, drops trailing empty strings,
and gives no-match and empty-input their receiver identity as required by
`String.split(regex)` limit zero. Derived pieces are fresh, non-interned Strings
with owned char arrays and a rank-one String array. Null receiver/regex dispatches
as guest NPE kind 6; profile/quota refusal must preserve roots.

All engine/coordinator images, bootstrap Java8 source builds, generated receipts,
checksums and process logs are archived beneath this evidence directory. The
accepted 320 KiB profile is unchanged; this candidate is measured at the explicitly
authorized LOCAL 384 KiB and LOCAL 1B external budget only. No original JAR/classes,
Minecraft main body, world, EULA, or Done claim is part of this preflight.
