# Result

Generated-only bounded Java 8 `StringBuilder(int)` stage completed from
accepted `parent-7227a13b1`.

- Replaced only bootstrap image84 (`java/lang/StringBuilder`) with the 624-byte
  Java 8 bounded `(I)V` image (SHA-256
  `57eac8ab607a23fbb0a06a6af655321b7cf634b3d8c448d4c36fbaac99994fd9`).
  Nonnegative capacity creates empty logical content; negative capacity raises
  guest `NegativeArraySizeException` through ordinary `newarray`.
- Existing `()V`, `append(String)`, and `toString()` remain. `capacity`,
  `ensureCapacity`, `setLength`, primitive append, and other methods refuse.
  Raw37/282358, 90 images, diagnostic127, native13, resource pipeline, and all
  fixed limits remain pinned.
- Runtime-derived ordered root remains `keccak256(abi.encode(DBOOT,h))`:
  `842464491035a9f67034b5c943f785230649c0d5c59e66532a91826192bc5945`.
  Runtime is 392934 / 393216 bytes; coordinator remains 5394.
- Generated focused+retained gate: 430 commands, 5294 canonical receipts,
  357.671 seconds (cap1200). 0/1/255 positive and negative capacity agree over
  q1/q7/direct/reopen.

No original artifact/JAR/class/resource, provider/factory/world, setLength,
ThreadLocal.set, or Done claim. Parent alone reruns unchanged original37.
Evidence: `evidence/java-evm/minecraft-entry/string-builder-capacity-constructor-preflight/`.
