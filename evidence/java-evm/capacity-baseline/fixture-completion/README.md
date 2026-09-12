# Capacity-baseline fixture completion

**TEST-only fixture/oracle builder.** This is not a runtime, driver, transport,
Solidity patch, execution receipt, accepted capacity profile, or demand-loading
result. Production remains four selected classes / 65536 raw bytes. The proposed
8 / 262144 comparison is unaccepted and parent-owned.

`generate.py` makes fresh ignored output only. It requires the exact local Java
8u504 tools at `/usr/lib/jvm/java-8-openjdk/bin/{javac,java,javap}` and rejects
other versions. It compiles Java source with `-source 8 -target 8 -g:none`,
creates deterministic timestamped opaque ZIP inputs, and separately compiles
and invokes an `Oracle` for every case and argument. Oracle source/class files
are outside every ZIP.

## Reproduce

Run from the repository root, choosing a fresh ignored directory. `TMPDIR` is
also scoped to a new ignored directory; do not pre-create the output argument
(the generator correctly refuses existing output).

```sh
out="$PWD/build/java-diff-mc-capacity-fixtures-$(date +%Y%m%d%H%M%S)"
tmp="${out}-tmp"
mkdir -p "$tmp"
TMPDIR="$tmp" python3 evidence/java-evm/capacity-baseline/fixture-completion/generate.py "$out"
TMPDIR="$tmp" python3 evidence/java-evm/capacity-baseline/fixture-completion/generate.py --verify "$out"
```

The output includes `metadata.json` (all class/ZIP sizes and SHA-256 hashes,
known selected names, entry/mode/oracle results), exact raw oracle captures,
generated chain source, separate oracle source/classes, opaque `zips/*.zip`,
and `classes/` only for TEST construction/verification. Parent execution must
supply a whole ZIP; there is no raw-class execution shortcut in this builder.

## Fixture set

* `baseline4-exact` is the committed `Base0..Base3` four-class chain; and
  `capacity8-exact` is committed `Cap0..Cap7`. Both execute every selected
  successor and its static initializer.
* `big-method-rich` is committed `BigCaller` + `BigEntry`; the generator
  asserts the previously recorded `BigEntry` shape (90874 bytes, CP count 2565,
  2552 methods), both recorded class hashes, and recorded ZIP hash. It is a real
  useful call (`BigCaller.run -> BigEntry.use -> m2549`), not a padding case.
* `chain4`, `chain5`, `chain6`, `chain8`, and `chain9` are source-generated
  transitive static-init/call chains. The 5/6 cases provide real intermediate
  selections; the 8/9 pair is the selection boundary guard. Every class is
  public, listed in metadata, zipped, statically initialized, and called.
* `aggregate65536`, `aggregate65537`, `aggregate262144`, and
  `aggregate262145` contain exactly two selected public classes. `BoundaryEntry`
  is exactly 4097 bytes and calls `BoundaryPad`; an explicit valid unknown
  `CapacityPadding` class attribute sizes both resources to the exact aggregate.
  The 262145 case is deliberately two individually <=262144-byte valid classes,
  so a prospective aggregate refusal cannot honestly be attributed to malformed
  class bytes or an individual DI0-resource limit. These are boundary controls,
  not method-rich performance evidence.

The Java Virtual Machine ignores an unrecognized class attribute by design.
`generate.py` constructs it by adding a UTF-8 constant-pool entry and a correct
class `attribute_info`, then strictly reparses the complete classfile before and
after writing. The verifier also reloads/runs the padded classes on Java 8u504.

`reference/` retains only small durable receipts from a fresh generation:
tool-version/hash metadata and full raw oracle text. It deliberately does **not**
commit the padded binaries; they are reproducible from the committed sources and
recipe.
