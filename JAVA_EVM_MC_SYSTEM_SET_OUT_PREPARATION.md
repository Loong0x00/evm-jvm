# Java-on-EVM Minecraft `System.setOut(PrintStream)` preparation

Accepted `parent-1b178a6eb` adds bounded native `System.setErr` and advances unchanged original52 to83786J/68I. Atomic q1 at PC75 refuses exact static `java/lang/System.setOut(Ljava/io/PrintStream;)V`, confirmed by fresh-domain EVM CP diagnostics.

Add only canonical public static native `System.setOut(PrintStream)` and exact global native binding15->16. After ordinary initialization/descriptor/assignability checks, binding16 updates only canonical initialized System.out to the supplied guest reference (null allowed); System.err and all other statics remain unchanged. Keep out public static final in class metadata; native VM mutation is the sole exception. No SecurityManager permission, host output, console/file/forwarding/provider claim.

Generated tests cover replacement identity, err unchanged, null/reset, subclass PrintStream, exact-native raw replacement refusal, q1/q7/direct/reopen plus retained direct/reopen<=1200s. Preserve raw52/329162,diagnostic146,94 images,String-local11,all caps/toolchain and runtime-derived root. Runtime<=393216 (baseline375425). Commit only changed System leaf and binding16 path. Worker no originals/JAR/classes/resources/network/other worktrees. Parent alone replays original52. No world/EULA/Done claim.
