# P34 precise/discovery replay controller

This directory contains the isolated performance-controller/helper/test work. It is not an engine, coordinator, Solidity, JVM, runtime-image, gas, or checkpoint-format change. The only source base used is the immutable `../performance-base-p34/` snapshot. Its `SOURCE_MANIFEST.json` must verify before use; the generated-EVM gate performs that verification before reading any other frozen file.

No original JAR, original classes/resources, original binding list, world, checkpoint, or receipt was opened for this work. Tests use only generated Java 8 source/ZIP fixtures and the pinned P34 public Go transport. The parent agent owns any original-input run, independent acceptance, and GitHub synchronization.

## Modes and safety contract

`replay_controller.py --mode precise` is the default. `--action` and every input/output path are required. Precise mode preserves the replay policy: use the explicit starting quantum, halve after any atomic refusal, keep the reduced quantum after the first refusal, and stop only at q1, a genuine terminal guest outcome, the explicit wall/call bound, or a fail-closed transport error. It runs the public reopen verifier once at final precise termination; it does not make per-slice diagnostic calls that would add EVM/counter work.

`--mode discovery` is opt-in and is never an acceptance mode. It can stop early only for the exact canonical `MCEntryMissingClass(uint256,uint256,bytes)` selector `0x555db429` whose dynamic ABI tail re-encodes canonically, whose raw name bytes exactly match the transport diagnostic, and whose refusal proves all of:

- there was a prior successful P34 public-transport checkpoint for this same pinned package;
- the EVM trie root and byte-exact durable Head are unchanged;
- the refusal returned zero checkpoint bytes and no candidate Head/checkpoint/root;
- supplied call gas equals the P34 build pin.

A noncanonical selector/ABI, diagnostic mismatch, generic missing-class text, EVM revert/OOG, transport timeout/watchdog, raw parser failure, or terminal guest outcome is not an early discovery stop. Contradictory root/head/checkpoint evidence aborts. A discovery report always sets `terminalGuestOutcome`, `q1FrontierAcceptance`, and `finalAcceptanceEligible` to false; it never writes a Java result or resumes a failed/candidate checkpoint.

For equivalence continuation, use a new results directory and pass the discovery `summary.json` with `--continue-from` to `--mode precise --action continue`. The controller verifies the exact same package/bindings/fixture/code pins and current successful Head projection, validates the archived canonical refusal, and resumes from that last successfully published checkpoint at `max(1, failedQuantum//2)`. Failed-call output is never an input. The final precise mode still reaches the ordinary q1 or guest-terminal result.

If interrupted before a normal child exit was recorded, reopening with the same state treats any refusal receipt as ambiguous, archives it, and retries the same quantum from the unchanged authenticated Head. A normal child-exit record may consume the associated canonical refusal without rerunning it. Successful committed child Heads can be recovered only from the public successful slice receipt plus the opaque checkpoint hash. Stale/preexisting refusal receipts are archived without overwrite.

## Explicit CLI inputs

The controller requires `--driver`, `--build`, `--fixture-zip`, `--bindings`, `--package-hash`, all four runtime SHA/Keccak pins, `--max-call-gas`, `--wall-limit-seconds`, `--world`, and `--results`. `--bindings` is a small JSON object `{ "schema": 1, "bindings": ["..."], "selectedResource": "" }`; no source or classfile is host-parsed. `--build/pins.json` and the actual deployed-bytecode files must match the explicit code pins. The controller never guesses original paths or consumes an implicit bindings list.

Default `--mode` is `precise`; discovery requires an explicit `--mode discovery`. `--max-quantum` and `--initial-quantum` default from the P34 cap/build and may not exceed the already-pinned Head quantum or P34 limit. The P34 build's call gas remains 1,000,000,000; tests do not raise it.

## Verification and durable result

Fast unit/fail-closed checks:

```sh
python3 evidence/java-evm/minecraft-entry/perf-replay-discovery/test_replay_controller.py
python3 -m py_compile evidence/java-evm/minecraft-entry/perf-replay-discovery/*.py
```

Genuine generated-EVM equivalence gate (all paths explicit; it creates/removes only the given generated-only work directory on success):

```sh
python3 evidence/java-evm/minecraft-entry/perf-replay-discovery/generated_evm_gate.py \
  --repo-root . \
  --frozen-p34 evidence/java-evm/minecraft-entry/performance-base-p34 \
  --work-root evidence/java-evm/minecraft-entry/perf-replay-discovery/work/generated-evm-gate-NEW \
  --evidence-output evidence/java-evm/minecraft-entry/perf-replay-discovery/results/generated-evm-equivalence-NEW.json \
  --budget-seconds 1100 --quantum 64
```

The generated gate compiled the immutable reference transport with one disposable CLI dispatch added for `resume-one-qn`; its audit records source/binary hashes. A separate disposable copy of the legacy precise Python controller replaced only original-only input guards/bindings, gas-label expectations, and the generated test quantum. Frozen reference files remain unchanged. All primary outcome evidence comes from actual public Go-driver EVM executions; no Go output is fabricated.

`results/generated-evm-equivalence-v5.json` records the final run; `results/attempt-history.json` and `results/failures/` preserve earlier harness failures and repairs. At the P34 1B gas pin and generated q64 fixture quantum, the exact missing-type fixture produced a canonical EVM error for `perfcheck/missing/MissingDependency`. New precise and discovery-plus-precise-continuation each matched the legacy precise sequence (22 recorded start/slice/refusal rows), canonical final Head and deterministic counters, exact final checkpoint bytes, and read-only MR01 view. The positive terminal fixture's new precise and discovery runs also matched old precise; discovery reached the actual terminal guest outcome without relabeling it as a discovery stop. The separate discovery-only result stopped at q64 with next precise q32 and explicitly made no terminal/q1/final-acceptance claim. The final gate completed in 14.531 seconds.

Each equivalence row preserves both exact canonical event sequences, both final canonical Head projections (including deterministic counters), the exact MR01 checkpoint bytes as hex, and the read-only MR01 decoded view. The discovery-only record also preserves its exact event sequence, last successful Head and byte-exact atomic refusal receipt so the early-stop predicate can be independently rechecked. Nondeterministic host-time telemetry (`maxCallMs`, `commitMs`) is excluded from canonical counter equality; deterministic EVM/gas/read/write/commit/checkpoint counters, trie and guest roots, lifecycle/result, checkpoint SHA, and all MR01 bytes are retained. This is generated-fixture equivalence only, not original86 performance, Minecraft readiness, P34 acceptance, or parent acceptance.
