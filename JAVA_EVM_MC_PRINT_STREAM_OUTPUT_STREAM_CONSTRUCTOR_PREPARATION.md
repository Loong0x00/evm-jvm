# Java-on-EVM Minecraft `PrintStream(OutputStream)` preparation

Accepted `parent-3aa2fed0a` makes canonical PrintStream a direct OutputStream subtype and advances unchanged original52 to83748J/68I. Atomic q1 at PC2 refuses exact `java/io/PrintStream.<init>(Ljava/io/OutputStream;)V`, measured by a fresh-domain EVM CP diagnostic in raw class index51 constructor.

Add only this public constructor to canonical PrintStream. For a non-null guest OutputStream it chains to retained OutputStream construction and initializes the existing guest-only sink object; do not speculate FilterOutputStream inherited fields, forwarding, encoding, auto-flush, files or host output. Null may throw the canonical guest NPE to match bounded Java behavior. Preserve no-arg constructor, direct subtype, write(int) low-byte sink, print(char), println(String).

Generated probes cover non-null constructor, null exception, subclass super-call, sink retention, raw replacement/uninitialized controls, q1/q7/direct/reopen plus retained direct/reopen<=1200s. Preserve raw52/329162,diagnostic146,94 images,native14,String-local11,System out/err,all caps/toolchain and runtime-derived ordered root. Runtime<=393216 (baseline373704). Commit only changed PrintStream image/root leaf. Worker no originals/JAR/classes/resources/network/other worktrees. Parent alone replays original52. No provider/world/EULA/Done claim.
