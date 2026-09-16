# Generated bounded `Properties.load(InputStream)` source stage

This stage derives only from accepted URL parent `parent-c96c326bc`. It replaces
bootstrap slot 47 (`java/util/Properties`) with a Java 8 ordinary
`load(InputStream)` body. Constructors, both `getProperty` overloads,
`setProperty`, defaults traversal, and the inherited `Hashtable` storage path
remain guest Java. The parser uses no host parser, native binding, decoded
resource callback, or resource-specific values.

The measured ISO-8859-1 surface reads individual guest `InputStream` bytes,
handles CR/LF (including CRLF), leading space/tab/form-feed, `#`/`!` comment
lines, `=`/`:`/first-whitespace separators, separator-adjacent whitespace, and
simple non-escaped key/value bytes. It copies exact char-array slices into guest
Strings and calls inherited `Hashtable.put`. It does not close the supplied
stream. A null stream follows the ordinary invokevirtual NPE route. A backslash
(including continuations or `\u` syntax) and a 4097th unit in one line raise a
catchable guest `IOException`; 4096 units are accepted. This is not a complete
Properties parser or a synchronization/thread-safety claim.

The engine delta is otherwise exactly a fresh domain and slot-47 image. The
accepted scalar selected-resource pipeline remains unchanged: generated ZIP
bytes go only through EVM AS0 → ZI0 → DI0, then seed one read-only VFS path.
The coordinator and raw-byte driver retain that pipeline and its scalar
selection; neither parses ZIP data or property text. Fixed limits remain raw
`32/262144`, 86 bootstrap images, 13 global natives, diagnostic bound 118,
128 frames, 1 MiB checkpoint, 32768-byte Head, 25M reserve, 1B external LOCAL
gas and engine runtime ≤393216 bytes.

`tools/verify_source.py` pins exactly four accepted URL-parent source inputs,
rebuilds the Java 8 Properties image, proves all other engine bytes are
unchanged, and checks the selected-resource/coordinator/driver constraints.
`tools/generate_fixtures.py` uses only trusted generated Java 8 sources and
ZIPs. The gate retains the URL/Object/cap32/lock/TreeMap/String/EnumSet/queue/
OOM/reopen/canonical corpus and adds resource enumeration → URL → InputStream →
Properties.load values/EOF/close, null, escape, and 4096/4097-line cases.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/properties-load-preflight/tools/build.py build/java-diff-mc-properties-load-build-LOCAL
python3 evidence/java-evm/minecraft-entry/properties-load-preflight/tools/generate_fixtures.py build/java-diff-mc-properties-load-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/properties-load-preflight/tools/gate.py build/java-diff-mc-properties-load-build-LOCAL build/java-diff-mc-properties-load-fixtures-LOCAL build/java-diff-mc-properties-load-gate-LOCAL
```

No original artifact, JAR, class, resource, checkpoint, provider, factory,
world, Minecraft run, or Done claim is part of this stage. Parent alone may run
unchanged original32.
