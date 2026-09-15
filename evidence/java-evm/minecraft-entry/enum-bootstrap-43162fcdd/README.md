# Measured `java/lang/Enum` bootstrap 82

Basis: accepted `parent-9453ebd08` (81 images, raw `29/262144`). This LOCAL384-only
preflight appends a Java-8-built 702-byte `java/lang/Enum` image as image 82; every
prior image byte and position is reverse-verified unchanged.

The source is abstract `Enum<E extends Enum<E>> implements Comparable<E>, Serializable`,
with private final `name`/`ordinal`, protected `(String,int)`, final `name()`/`ordinal()`,
direct-field `toString()`, ordinal-subtraction `compareTo(E)`, and javac's
`compareTo(Object)` bridge. It intentionally omits hashCode, clone, finalize, valueOf,
and reflection APIs. Enum has no `<clinit>`. Raw `java/lang/Enum` is now bootstrap
reserved and atomically refuses at binding index 1.

Final reproducible build: engine 390633 bytes (within the fixed 393216 LOCAL384 cap),
SHA-256 `13895e39d5bb530fb98df46a3f70a58a30bca0ddd9823b6e7300428935ee42d8`,
Keccak `d8d4afa829dc5e9301ac37d2fd6afbc7e9358ec3d669542c804b55acb4435e90`;
coordinator remains 4146 bytes. `pins.json` is the authority.

Generated-only results (no original Minecraft JAR/class/world input):

- Enum constructor/field/name/ordinal/direct-toString, Comparable bridge/type/null,
  Serializable, active superclass initialization, raw replacement refusal, canonical
  q1/q7/direct and reopen: 203 canonical receipts. Enum active index is 83 for the
  two-raw-class fixture; total class count is 84.
- Retained 1025-field guest allocation catches the existing guest OOM without changing
  quotas: 12 canonical receipts, q1/q7/direct canonical terminal equality.
- Retained 28/29 class and exact-byte cap matrix passes, including 30-class driver,
  coordinator and engine refusals plus 262144/262145 boundaries.
- Retained ACC_ENUM matrix passes. The genuine Java8 `values()` fixture advances past
  the former absent-superclass `HierarchyError(1,1)` and honestly reaches unchanged
  missing array `clone` `CallError(1,3)` (`0xd631c3a4`) with unchanged root; this is
  not an implementation of clone or values.

`artifacts/`, `logs/`, `fixtures/`, and `gates/` are durable reproducer inputs/results.
No original workload was run and no next original blocker is claimed.
