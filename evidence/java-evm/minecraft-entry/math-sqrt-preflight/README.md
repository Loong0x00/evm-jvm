# MC Math.sqrt preflight

Generated-only implementation of `java/lang/Math.sqrt(D)D`, global native binding 18.

- Raw limits remain 71 classes / 471911 bytes; bootstrap count 96; diagnostic bound 167.
- Global bindings 1..17 and String-local 12 are retained; only the Math leaf (slot 89) changes.
- The kernel normalizes raw guest binary64 bits, runs fixed 52/53 iteration integer loops, and rounds from the exact integer remainder. It does not use host floating point, math precompiles, or external calls.
- `results/` is a durable generated gate record. `tools/verify_source.py` reconstructs the exact source delta and independently folds the ordered bootstrap root; `tools/verify_results.py` checks durable summaries.

No original class/JAR/resource/network input is opened. Parent genuine replay is deferred.
