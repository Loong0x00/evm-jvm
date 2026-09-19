# Result: bounded Java 8 `StringBuilder(int)`

- Replaced only bootstrap image84 (`java/lang/StringBuilder`) from
  parent-7227a13b1 with a 624-byte Java 8 image, SHA-256
  `57eac8ab607a23fbb0a06a6af655321b7cf634b3d8c448d4c36fbaac99994fd9`.
- Nonnegative `0`, `1`, and `255` create empty logical content under the
  accepted exact-content `char[]` representation. Negative capacity reaches
  ordinary guest `newarray` and catchable `NegativeArraySizeException`.
  Default construction, `append(String)`, and `toString()` remain present.
- `capacity`, `ensureCapacity`, `setLength`, primitive `append`, and all other
  omitted members reject atomically. Raw37/282358, 90 ordered images,
  diagnostic127, native13, and all fixed limits are unchanged.
- The complete root is runtime-derived over ordered image hashes:
  `keccak256(abi.encode(DBOOT, h))` =
  `842464491035a9f67034b5c943f785230649c0d5c59e66532a91826192bc5945`.
  Runtime is 392934 / 393216 bytes (282-byte headroom); coordinator is 5394.
- Focused plus retained generated gate: 430 commands, 5294 canonical receipts,
  357.671 seconds (cap1200). Positive capacity cases agree at 171 Java/2
  internal steps and q1/q7/direct epochs 171/25/1; negative agrees at 16/3 and
  16/3/1.

No original artifact/JAR/class/resource, provider/factory/world, setLength,
ThreadLocal.set, or Done claim. Parent alone reruns unchanged original37.
