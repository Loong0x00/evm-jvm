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

The source archive pins Java8 `/usr/lib/jvm/java-8-openjdk/bin/javac` images:
String 815B SHA-256 `c0ce987a...`, System 825B `fd3898b3...`, and the parent-corrected
Class 670B `0e3d4ea7...`. The 68 bootstrap comparison proves only System and String
changed; the other 66 are byte-exact. Reproducible solc 0.8.30/viaIR/Cancun output is
361345B (SHA-256 `e251139f...`, Keccak `6e7ab3b2...`), below the 384 KiB LOCAL cap;
the coordinator is 4146B. The accepted 320 KiB profile is unchanged.

This commit deliberately does **not** claim the required generated EVM q1/q7/direct/
reopen receipts, durable owner/store deployment, or an original22 continuation: those
whole-process gates have not yet been run. No original JAR/classes, Minecraft main
body, world, EULA, or Done claim is part of this preflight.
