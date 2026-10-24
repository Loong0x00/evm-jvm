# Bounded `Arrays.asList` candidate (not accepted)

This candidate contains only the measured Java 8 `Arrays.asList(Object[]):List`
profile and traversal needed by the generated startup probe: a fixed-size,
live view over the supplied array, independent iterators, `hasNext`, `next`,
and iterator exhaustion. Null array input throws `NullPointerException` from
the factory. The view advertises the Java 8 `RandomAccess` and `Serializable`
marker interfaces. It does **not** implement list `get`/`set`, mutation,
`toArray`, or other `Arrays` APIs; those paths are expected to refuse atomically.
This is not a claim of general `List` immutability or snapshot semantics.

## Reproduction / evidence

- `source_audit.py` verifies the 15-file P55 source-only manifest, unchanged
  six Java hierarchy sources and 80 providers, exact 120-image prefix and
  ordered root rows, 123-image tail layout, and canonical config encoding.
- `rebuild_java_images.sh NEW_OUTPUT_DIR` recompiles the three appended
  bootstrap classes with OpenJDK 8 `javac -g:none -source 8 -target 8`, then
  byte-compares against `build/classes-v3`. The tested compiler was
  `javac 1.8.0_504`; the reproducible image hashes/root are in `pins.json`.
- `rebuild_test_fixtures.py NEW_OUTPUT_DIR` regenerates the 150-class positive
  probe, refusal inputs, and runs only the generated fixture's host-JVM oracle.
  Its rebuilt positive ZIP entries were byte-identical to the pinned EVM input.
- `make_pins.py` pins Solidity artifacts, bootstrap images/root, inputs and
  source files. `summarize_evidence.py` summarizes durable EVM receipts.
- Latest EVM receipts use engine runtime SHA-256
  `09f4dc97001895a489f261c44972eb0d51eca024eb5c0d96177243c2bece84b3`,
  coordinator runtime Keccak `eae7b0d67df70a05ed6311d6c12c8ed55094a61e6211c5f1dc043cbfe1ab0061`,
  q1/7/65536, plus seven independent unsupported-API atomic-refusal fixtures.
  Exact roots, epochs, gas and refusal outcomes are in
  `build/results/arrays-as-list-summary.json` and pinned logs/reports.

All files here are a bounded candidate for independent review. These results
are not parent acceptance, a Minecraft execution claim, or permission to merge
or push. No original Minecraft input or parent review material is used here.
