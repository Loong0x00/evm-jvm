# System.getProperty preflight input

This is a LOCAL384, unaccepted bounded guest-System preflight.  It begins from
`parent-fdc55a341`'s source-only EVM-ZI0 resource engine.  The only bootstrap
image replaced in its fixed 64-image sequence is `java/lang/System`.

`System` retains nullable private `SecurityManager`, `getSecurityManager`, and
native `arraycopy`; it adds a private initialized `Properties` object and
`getProperty(String)`.  `key.length()` gives Java's ordinary null dereference;
an empty key constructs `IllegalArgumentException`, and every other key is sent
to the already-pinned guest `Properties.getProperty`.  No host values, `-D`
input, setters, clear/getProperties APIs, or key-specific behavior exist.

The empty-key branch references Java 8 `IllegalArgumentException`, which is not
one of the fixed 64 bootstrap images.  The generated fixture provides its own
ordinary raw Java 8 definition solely to exercise that branch; this does not
change bootstrap count/order and its name is not a reserved bootstrap name.

`artifacts/` contains the reproducibly built engine/coordinator/ABI and generated
classes (never a Go executable). `results/` contains compressed generated-only
full receipts and checkpoints, with no LevelDB state, plus `SHA256SUMS`. The
process-tree monitor records the bounded property-control gate separately.
