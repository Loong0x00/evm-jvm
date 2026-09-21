# Result: generated `Objects.requireNonNull(Object,String)` image93

- Appended only Java-8 `java/util/Objects` image93 (385 bytes, SHA-256
  `fc87c7bfe18107225d3682238f8c1a07d0e66d737f1d26f95edc7d7f9a7698df`).
  Its private constructor and sole generic two-argument `requireNonNull`
  method use the normal guest null branch: non-null returns the original
  reference; null is caught as guest `NullPointerException`. No NPE message
  retention or any other Objects API is asserted.
- The ordered runtime root is dynamically derived; fresh DBOOT root is
  `415b737bc5780358c7bb1d8a8e1c9e27cff1a72ec9c2d177e76f5da831a515f3`.
  Existing 92 leaves, Object image, raw48/314425, native13, and all other
  pinned limits remain unchanged. Diagnostic bound is 141.
- Runtime rebuilt at `390985 / 393216` bytes (2231-byte headroom); coordinator
  is unchanged in size at 5394 bytes. The recorded baseline remains 391172.
- Generated q1/q7/direct/reopen paths agree exactly: non-null exact-reference
  `34/2` Java/internal steps and caught-null-NPE `30/6`. Raw Objects
  replacement is atomically rejected with `BootstrapProfileError(1,1)`;
  omitted `requireNonNull(Object)` is `CallError(3,7)`.
- Fresh generated-only gate passed in `636.6685040730517` seconds (under the
  fixed 1200-second cap): 654 commands and 10599 canonical public receipts.

No original artifact/JAR/class/resource/world was read. This is not a logger
factory, provider construction, world, Minecraft, or Done claim; parent owns
the genuine replay separately.
