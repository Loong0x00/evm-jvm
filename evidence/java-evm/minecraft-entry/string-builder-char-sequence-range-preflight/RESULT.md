# Result: bounded `StringBuilder.append(CharSequence,int,int)`

- Replaced only bootstrap image84 from `parent-baeda70ed` with the 914-byte
  Java 8 image `22ca3088c0cebccc5714beefd40cf187dbaebe5930477559e20ab8709249ffa4`.
  It retains both constructors, `append(String)`, copy-producing `toString()`,
  and exact-zero `setLength(int)`, then adds only String-backed valid-range
  CharSequence append. Null, non-String, and invalid ranges throw guest IAE
  without mutation; other CharSequence/append APIs remain absent.
- Raw37/282358, all 90 image positions, diagnostic127, native13/string-local10,
  exception kinds14, gas/reserve, frames/checkpoint/Head caps, compiler, and
  runtime-derived bootstrap root remain pinned. Root:
  `cd603ccfebe00cbc0df9b81f65165af6c411d18470cf2839e00ff08abde524fb`.
- Parent baseline was 393206 / 393216 bytes. Bounded counter layout cleanup
  yields runtime 393185 bytes (31-byte headroom), SHA-256
  `6fd885e700a28076b44eac81b35faaff3276cced18718c0c0431487054d56b1a`;
  coordinator remains 5394 bytes.
- Valid empty/middle/full prefix range and null/non-String/invalid controls each
  pass q1/q7/direct/reopen. The generated focused-plus-retained gate completed
  465 commands, 8268 canonical receipts, in 513.225 seconds (cap1200).

No original artifact/JAR/class/resource input, arbitrary CharSequence/provider
factory/world, or Done claim. Parent alone performs accelerated replay.
