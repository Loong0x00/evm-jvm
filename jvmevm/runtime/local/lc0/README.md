# MC-LC0 local continuation runtime

`LC0Interpreter.sol` is the frozen schema-1 LOCAL continuation variant of the
accepted MC-LB0 interpreter. It was derived from `jvmevm/runtime/JVMSubsetInterpreter.sol`
with source SHA-256
`c2fab72e468a951e29fd069d3bf3dfa98ab1513138ed7ae33f219a2588fcea9d`
(the descriptor-precedence fix is included). The old source, runtime artifact,
bootstraps, stock modules, and EVM implementation are not modified.

The contract exposes only `start`, `resume`, `head`, and `validateCheckpoint`.
Start and resume share one real bytecode dispatcher. EVM code parses the exact
ordered raw bundle, selects/rebuilds live methods, executes Java units state, and
emits the 216-byte `JVMELC01` envelope plus compact `LCS1` machine stream.
Checkpoints contain active frames, static fields, allocated heap records, pending
fault state, and intern entries; parse/link/code/layout caches are reconstructed in
EVM. The anchor stores only ownership/CAS commitments and lifecycle.
`validateCheckpoint` checks canonical state/source consistency but does not create
or update provenance.

## Reproducible build

Requirements are Node/npm and the pinned `solc` 0.8.30 package.

```sh
npm ci --ignore-scripts
npm run build
npm run check
```

Compiler settings are optimizer 200 runs, via-IR, Cancun, and disabled appended
metadata/bytecode hash. The checked-in outputs are:

- `LC0Interpreter.runtime.hex`: 206,163 bytes; runtime-byte SHA-256
  `a1820864d8e846be4de8211158778150fdfde0e41e443aa66c44ec17f487e6cd`
- `LC0Interpreter.abi.json`: ABI for the frozen surface and exact `SliceResult`
- `artifacts/LC0Interpreter.json`: checked ABI/runtime/provenance, embedded by Go.

Accepted continuation/restart and parent corrections are recorded in
`JAVA_EVM_MC_LC0_REVIEW.md`; the pure LB0 and stock artifacts remain unchanged.

The runtime is below the separate 256 KiB LOCAL ceiling but far above EIP-170 and
EIP-3860 limits. It is intended for explicit local code installation and
`runtime.Call`; this is not CREATE or standard-chain deployment evidence.

## Bounds and measured smoke evidence

The runtime enforces 1..4 raw classes, at most 64 KiB aggregate raw bytes,
0..8 integer arguments, 1..4096 JVM/internal units per call, a 1 MiB checkpoint,
checked uint64 totals/epochs, and a 25,000,000-gas commit reserve. Historical
budgets are unchanged. Intended harness limits are finite 100,000,000 gas / 30s
ordinary and 1,000,000,000 gas / 120s boundary calls.

### Initial delivery diagnostics (historical, before parent fixes)

The following measurements refer to initial runtime `a77feb66...`, not the
accepted artifact above. Local `runtime.Call` diagnostics against the five pinned
preflight classfiles observed results 15, 36, and 10. Gas/checkpoint/unit results were:

| fixture | gas | checkpoint bytes | JVM units | internal units |
|---|---:|---:|---:|---:|
| call loop (`run(5)`) | 2,157,809 | 451 | 74 | 2 |
| shared heap/String alias | 5,961,316 | 905 | 105 | 3 |
| initialization/handled fault | 3,155,662 | 610 | 18 | 5 |

Actual q1 continuation completed call-loop and initialization cases (76 and 23
committed epochs respectively). A q10 initialization slice captured the required
RUNNABLE pending ArithmeticException at ref 2 / fault PC 15 after advancing the
faulting opcode; its next slice performed an internal unit with no JVM redispatch.
Actual q7 continuation completed the alias case;
its final machine root exactly matched a one-call run despite different checkpoint
history. Emitted alias terminal checkpoint validation also returned its machine
root. These are focused local diagnostics, not the parent acceptance corpus,
durable restart proof, all malformed-stream coverage, Java SE conformance, or
Minecraft execution.
