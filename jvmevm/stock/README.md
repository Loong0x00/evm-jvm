# Stock-EVM S0 validation boundary

`jvmevm/stock` is a separate, deliberately small stock-EVM architecture slice. It
is **not** a deployment or modularization of the accepted M5d-a interpreter, does
not run the M5d-a 2,231-case corpus, and is not evidence that Minecraft starts or
that a general JVM is available.

S0 deploys three ordinary contracts with ordinary `CREATE`:

1. `ArtifactPage` publishes exactly `STOP || classfile` (one payload of 1–4096
   bytes) and has no writable page API.
2. `TinyJvmStepModule` reparses and predecodes the selected `public static run()I`
   method in EVM. It supports only the frozen straight-line Java `int` opcode
   profile and Java modulo-2^32 arithmetic.
3. `VMCoordinator` pins the page, module and hashes as constructor immutables,
   persists the fixed canonical `Machine`, and commits bounded whole-instruction
   batches with an epoch, total-step count and schema-1 digest.

A module address/hash pair is a configuration commitment, not an attestation.
Acceptance therefore also requires the deployed module bytes to equal the pinned
compiler artifact. The coordinator runtime contains constructor immutables and is
checked against `immutableReferences` plus its getters; the page is checked
byte-for-byte against the original trusted test class.

## Frozen limits

- artifact payload: at most 4 KiB; selected Code: at most 256 bytes
- each contract runtime: at most 12 KiB; each initcode: at most 24 KiB
- `CREATE`: at most 8,000,000 gas; `resume`: at most 2,000,000 gas
- `maxJvmSteps`: 1–16; `maxDirtyWords`: 1–32
- coordinator commit reserve: at least 800,000 gas
- Osaka test block gas limit: 30,000,000; standard transaction cap: 16,777,216

These caps are protocol/test commitments. They must not be raised or bypassed to
make a workload pass. The fixed-state ABI is acceptable only for S0; a later full
heap/class/frame implementation requires paged persistent state rather than large
per-call ABI copies.

## Independent validation

`validation_test.go` intentionally does not use harness execution helpers. It:

- reads and checks the frozen artifact JSON and exact ABI/tuple/event layout;
- funds only a deterministic test EOA at genesis, signs every transaction,
  recovers the sender, calls `TransactionToMessage`, and leaves nonce and
  transaction checks enabled;
- uses ordinary `core.ApplyMessage` `CREATE`/calls under chain ID 1337 with all
  development forks (including Osaka) active and a deterministic block context;
- never injects executable code or storage into genesis and never calls
  `SetCode`, `SetState`, or a privileged page/state mutation shortcut;
- generates only small trusted Java 8 classfile-shaped test inputs and isolated
  mutations. The exact payload bytes are passed to the page unchanged; no host
  parser metadata or host-computed execution result is supplied to production
  contracts;
- checks exact `StockPageError`, `StockClassError`, `StockBytecodeError`, and
  `StockControlError` selectors and arguments, including payload offsets and JVM
  Code-relative PCs;
- checks canonical tagged cells, initialized-local tracking, int32 overflow,
  full selected-code predecode (including unreachable instructions), dirty-word
  accounting, epoch/step/digest/event values, terminal behavior, and rollback;
- distinguishes the coordinator's low-reserve error from actual EVM out-of-gas
  both before the first commit and after nonzero progress. Contract state and logs
  roll back, while normal sender nonce and gas charges do not;
- exercises EIP-170 (24,577-byte runtime) as an EVM creation failure and EIP-3860
  (49,153-byte initcode) plus Osaka EIP-7825 (16,777,217 transaction gas) as
  transaction precheck failures. These are standard protocol limits, not S0
  page/resume budget errors;
- repeats an identical signed direct replay and compares transaction hashes,
  contract addresses, gas, logs, outputs, deployed-code hashes, canonical final
  checkpoint and full state root under the identical explicit context.

The signed simulated-backend/JVM positive driver and fixture regeneration belong
to the sibling harness. This verifier uses no downloaded classes, Minecraft
artifacts, server execution, listeners, credentials, or EULA acceptance.
