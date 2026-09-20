# Result

- Image84 only: generated Java 8 `StringBuilder.append(char)` retains UTF-16
  NUL/ASCII/surrogate code units and existing prefix through the existing
  `append(String)` copy path.
- Source-derived 926-byte image strips only four ignored Code-local
  `StackMapTable` attributes (64 bytes); all Code bytes/non-StackMap structure
  are retained and verified.
- Runtime: 393208/393216 bytes; baseline 393191; 8-byte headroom.
- Focused q1/q7/direct/reopen: identical 1044 Java / 2 internal steps,
  machine root `0x51fbf1223732ae7fd08e992d70aed0c06cbea61e0d8bb1b6e75dd2ead6ba896d`.
- Full focused-plus-retained gate: 591.456s, 9711 canonical receipts.

No original/JAR/resource/provider/world/Done input or claim; no other append
overload is added.
