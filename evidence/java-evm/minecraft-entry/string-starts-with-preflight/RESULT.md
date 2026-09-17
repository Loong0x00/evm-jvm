# Result: ordinary bounded `String.startsWith(String)`

**Status:** completed generated-only stage from accepted Properties parent
`parent-1fc13ef12`. This is not an original artifact/JAR/class/resource,
provider/factory, Minecraft, world, EULA, or Done claim.

## Exact delta

- Replaced only bootstrap `String` slot **26** with Java-8 `-g:none` image
  `dc5dd53175b630ed9ffdf7ca5f86936c9d299596424cba94043d56d582180eae`
  (1315 bytes). The image preserves all earlier fields, constructors, ten local
  natives, `lastIndexOf(String)`, and `split(String)` and adds ordinary
  offset-zero `startsWith(String)`.
- `startsWith` calls `prefix.length()` before receiver length and compares
  `charAt` UTF-16 units at equal indices. Empty/exact/prefix/longer/absent,
  BMP, surrogate-pair and lone-high-surrogate prefix witnesses pass; null is a
  catchable guest NPE. No offset overload, native binding, substring, host
  comparison, or broader String API was added.
- The source verifier proves exact accepted-P2 engine replacement (fresh domain
  plus slot 26 only), then coordinator/driver derived pins. All other 85
  bootstrap images, Properties/resource pipeline, raw `32/262144`, 86
  bootstraps, 13 global natives, diagnostic 118, 128 frames and fixed caps stay
  pinned.

## Built pins and generated gate

- Runtime: **392076 / 393216 bytes**; SHA-256
  `674fd77832458387075945d962ea38fe7458bfe134ea91a24ea9ef6714d92779`,
  Keccak `f05ec4279b8ec94cc8dcd7569906ffc248522d204cb9897d2e1ce3242848d659`.
  Coordinator is 5394 bytes, Keccak
  `de264c857477be68704fb4bbce94d5d051935c9e19bfc535e2d1464cab3b2aea`.
- One fresh source build plus full generated gate passed in **99.363 s**
  (cap 1200 s): 77 result rows, 252 commands and 599 independently canonical
  ABI/event/checkpoint receipts.
- All eleven startsWith/null fixtures complete q1/q7/direct/reopen with equal
  machine roots, opaque terminal payloads, Java/internal counts. Focused paths
  span 10–62 Java steps and q1/q7/direct epochs 10–62 / 2–9 / 1.
- Retained Properties, lastIndexOf, StringBuilder, System.err, failed-init,
  raw32/33, byte boundary, EnumSet, queue, OOM, resource and reopen controls
  passed direct/reopen. The no-use `String[]` root leaves slot 26 uninitialized;
  raw String replacement remains an atomic refusal.

Durable compact build, fixture, gate, canonical-receipt and source-verification
records are adjacent to this file. Parent alone may run unchanged original32.
