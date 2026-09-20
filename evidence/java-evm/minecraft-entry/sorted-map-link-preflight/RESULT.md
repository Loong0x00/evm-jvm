# Result: generated `SortedMap` link

- Appended Java-8 image 92: 198-byte empty `SortedMap<K,V>` extending the
  retained `Map<K,V>` image. It is bootstrap-owned; raw replacement is
  atomically rejected with `BootstrapProfileError(1,1)` (`0x6a23ad80`).
- The link-only null `checkcast` probe completes at 12 Java / 2 internal steps.
  q1/q7/direct/reopen agree on one machine root and opaque checkpoint payload
  (epochs 12/2/1); `SortedMap` remains uninitialized.
- Constructor-only `TreeMap` remains unchanged. Its own mutation control is
  still `CallError(3,13)`. The historical typed `SortedMap.put` control now
  resolves the interface and refuses the non-implementing `TreeMap` receiver
  with `ReferenceError(2,13)` / `0xfe0674d5`, root unchanged.
- Runtime is `390931 / 393216` bytes; 92-image ordered root is
  `d7dd6b101c64ad66314e7d36dc5e36ea20e60369d31dd89a3edce39a9c04a308`.
  Raw40/295438, native13, limits commitment, and all retained controls remain
  pinned.
- Fresh generated-only gate: 147 rows, 620 commands, 10436 canonically
  re-encoded public receipts, 625.807 seconds (under 1200 seconds).

No original/JAR/class/resource/world input was used. This is a platform link
only; no `SortedMap` implementation or Minecraft/provider/factory/world/Done
claim is made. Parent performs any genuine replay separately.
