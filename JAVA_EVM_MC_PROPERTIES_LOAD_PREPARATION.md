# Java-on-EVM Minecraft bounded `Properties.load(InputStream)` preparation

Accepted `parent-c96c326bc` genuinely seeds and opens the selected immutable log4j provider resource, advancing unchanged original32 to15713J/43I and2249 canonical receipts. q7/q1 then atomically stop in `PropertiesUtil.loadClose` PC15 on `java/util/Properties.load(Ljava/io/InputStream;)V` (`CallError(3,15)`).

Implement only the measured single-thread guest parser:

1. Replace only existing bootstrap `java/util/Properties`, preserving constructors/getProperty/setProperty/inheritance. Add ordinary Java8 guest `load(InputStream)` with no host parser/native.
2. Read through the supplied guest InputStream and support the measured ISO-8859-1 subset: CR/LF lines, leading whitespace, `#`/`!` comments, `=`/`:`/first-whitespace key separators, surrounding whitespace, and simple non-escaped key/value bytes. Store via genuine inherited Hashtable.put.
3. Bound a line to4096 units. Null input remains catchable guest NPE. Backslash escapes/continuations, `\u` escapes and lines beyond4096 throw guest IOException rather than fabricate values. No synchronization/thread-safety claim.
4. Preserve URL resource packaging, raw32/262144,86 bootstraps,native13,diagnostic118 and every fixed limit/toolchain/outlined tail; runtime<=393216.
5. Generated gates parse exact generated comment/spacing/three-property resource through enumeration->URL->InputStream, verify values/EOF/close/q1/q7/direct/reopen, null and unsupported-escape errors, and retain all URL/Object/cap32/lock/TreeMap/String/EnumSet/queue/OOM/canonical gates.

Parent alone reruns unchanged original32. No provider construction, LoggerContextFactory, world or Done claim before genuine execution.
