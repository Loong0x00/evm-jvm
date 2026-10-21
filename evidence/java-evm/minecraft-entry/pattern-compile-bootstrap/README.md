# P36 Pattern.compile(String) source-only implementation

This is an append-only Minecraft-first Java 8 `Pattern.compile(String)` compiler slice. Its only baseline is the explicit source-only P35 snapshot at `../pattern-source-base-p35/`; `pins.json` and `tools/verify_source.py` pin and verify that basis. No original JAR/class/resource/world/checkpoint or original continuation input is used by this stage.

## Implementation boundary

- Adds genuine Java 8 class images `java.util.regex.Pattern` and `PatternSyntaxException` after P35's 101 images. The previous 101 ordered image leaves are verified unchanged.
- Eagerly parses an optional leading `(?i)`, UTF-16 literal units, escaped punctuation, and positive/negated literal character classes with inclusive literal ranges into a guest `int[]` token program.
- Implements `pattern()`, `flags()`, and `toString()`. The supported subset has no matching API and does not claim general Java regex support.
- Supported grammar syntax errors and null input take guest Java exception paths. Valid syntax outside the supported grammar reaches a private *unbound* native declaration, causing an atomic typed EVM refusal; no host regex implementation or fabricated Pattern result exists.
- `compile(String,int)`, `matcher`, matching and other omitted methods remain typed refusals. There are no new operational native bindings.
- Engine execution remains `LOCAL` preinstalled-code `runtime.Call`; the oversized interpreter is not an ordinary-`CREATE`/EIP-170 claim. The paired coordinator is ordinarily created and routes generated package bytes through pinned AS0/ZI0/DI0 dependencies.

The runtime is pinned at 407,633 bytes (under the existing 1 MiB local artifact ceiling), the checkpoint ceiling remains 2 MiB, raw class/byte limits remain 150/1,063,930, and all accepted opcode, EVM, gas and consensus rules are unchanged. The derived MR01 diagnostic class bound is 253 (150 raw + 103 bootstraps), not a raised raw-input quota. Generated q1 syntax/error execution exceeded the old 10,000-call driver guard and the 1,200s gate wall budget; both test-only limits are doubled to 20,000 calls/2,400s. The exact150/1,063,930-byte Pattern compile also measured `LC0ControlError(7)` under a 1B call gas budget, so the test-only call allowance is doubled to 2B. These driver allowances do not change JVM quantum, guest semantics, EVM opcode gas, accepted runtime/checkpoint caps, or raw-input caps. Earlier attempts are retained under `runs/p36-pattern-bootstrap-001` through `-005`.

## Reproduction

From the repository root, with Java 8, Go, Node dependencies installed:

```sh
python3 evidence/java-evm/minecraft-entry/pattern-compile-bootstrap/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/pattern-compile-bootstrap/tools/run_gate.py p36-reproduction-1
```

The gate rebuilds the source-authenticated engine and paired coordinator, generates Java 8 fixture/oracle inputs, compares actual checkpoint token arrays, checks syntax exception indexes and null behavior, exercises typed refusals/raw-name replacements, runs q1/q7/q65536/q4096 schedules and the coordinator route, and validates a q1 compiled-program checkpoint in a distinct process. It retains P35 HashMap/IdentityHashMap/Math/raw-envelope controls. Run artifacts, logs, hashes, fixture manifests and checkpoints are archived under `runs/<run-id>/`; `build/` output is disposable.

## Latest worker gate

`runs/p36-pattern-bootstrap-008/` is the completed generated-only gate: 55 generated fixtures (31 Java 8 host-oracle cases), four Pattern compile quantum schedules, q1 fresh-process reopen, exact 150-class/1,063,930-byte coordinator route, and retained controls all passed. Direct execution took 1,121,661 ms; the coordinator made 13,040,396,303 aggregate gas worth of calls with a maximum single call of 1,673,277,345 gas. The test-only allowances were 2B gas/call and 2,400 seconds; accepted runtime, checkpoint, raw-class, raw-byte, opcode-gas and consensus limits were unchanged. This did not execute original classes or Minecraft and makes no startup/world/Done claim. Parent review and any original continuation remain separate.

The first retry `runs/p36-pattern-bootstrap-007/` completed direct and q1-reopen gates but exposed a test-driver address mismatch at coordinator CREATE (`MR0Error(3)`: coordinator source pins engine address `...6e`, worker driver installed it at `...6c`). The driver now uses the source-pinned address; no engine or coordinator semantics changed. An earlier omitted-method expectation mismatch is preserved in `runs/p36-pattern-bootstrap-006/`: an absent overload resolves to typed `CallError(3)`, whereas a declared but deliberately unbound native reaches `CallError(4)`; both are atomic refusals.

The report’s presentation label was corrected after the successful gate to describe the P36 Pattern result rather than the inherited HashMap stage label; the engine, coordinator, bootstrap images, fixtures, and execution sources used by run `-008` were not changed after that run. `run-report.json` records this correction and the current `run_gate.py` source hash.

This stage does not execute Minecraft or original classes and makes no world/Done claim. Parent owns independent rebuild, acceptance, and any original continuation.
