# Result: generated `TreeMap` SortedMap empty path

- Replaced only image85 TreeMap with a verified Java-8 abstract-bit-stripped
  315-byte image declaring retained image92 `SortedMap`. It exposes only
  `<init>()V` and concrete `isEmpty()Z=true`.
- Fresh typed `SortedMap.isEmpty()` passes q1/q7/direct/reopen: 42 Java / 2
  internal steps, epochs 42/6/1, and identical machine root
  `0xb37cd34c89908bc268d58c5ecce0bbca1195bf590a4d20976a302abc8ffabf63`
  and opaque payload SHA-256
  `499baafd8092dec191b2e05c7594f326d5e80157961a071054202ab47118be09`.
- No mutation API was added. Direct TreeMap.put and typed SortedMap.put both
  finish with exact unsupported `AbstractMethodError` kind11 after ordinary
  construction/type-link (12 Java / 3 internal steps); neither yields a map
  value or mutation. Raw TreeMap replacement remains atomic
  `BootstrapProfileError(1,1)` (`0x6a23ad80`).
- Dynamic 92-image root is
  `32459057504c70e6cc1066ddd5fb4558c1dab4eed1ad86ad9acf07f3fa241b33`.
  Runtime is `391172 / 393216` bytes; raw40/295438, native13, diagnostic132,
  all profile limits, and all unchanged bootstrap leaves remain pinned.
- Fresh generated-only gate passed: 631 commands, 10,485 canonically
  re-encoded public receipts, 630.533 seconds (under 1200 seconds).

No original/JAR/class/resource/world input was used. This adds no general Map,
SortedMap, provider, factory, world, or Done behavior. Parent performs genuine
replay separately.
