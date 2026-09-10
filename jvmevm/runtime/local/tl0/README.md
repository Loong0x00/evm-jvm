# MC-TL0 local Throwable continuation runtime

`Throwable0Interpreter.sol` is the schema-1 TL0 successor to the accepted MC-LC0
runtime. It was derived directly from accepted LC0 source SHA-256
`f0739b6dedbf3b6f7676c06459b89d12a7b8a90dde297967c32dce0af9655dac`, including
the accepted continuation and codec corrections. LC0, LB0, stock runtimes, and all
27 bootstrap images are not modified.

The contract exposes only `start`, `resume`, `head`, and `validateCheckpoint`.
It retains LC0 owner/epoch/head CAS, rollback, unit accounting, resource limits,
generic dispatcher, EVM metadata reconstruction, and authoritative heap. TL0 adds
ordinary constructor-backed Throwable allocation, dynamically classified
identity-preserving `athrow`, exact custom-class terminal bytes, the narrow
`fillInStackTrace` override guard, and canonical arena-EIIE cause records.
Legitimate initialized receiver references that escape after a super-constructor
remain valid even while a caller still owns UNINIT duplicates; abrupt construction
poisons only those uninitialized aliases.

TLS1 checkpoints use the `JVMTL001` envelope, `TLS1` machine magic, and domains
`JVMEVM:MC:TL0:{ARTIFACT,BOOTSTRAP,CONFIG,MACHINE}:1`. They are intentionally
incompatible with LC0 checkpoints and retain the 1 MiB bound.

## Reproducible build

Requirements are Node/npm and the pinned `solc` 0.8.30 package.

```sh
npm ci --ignore-scripts
npm run build
npm run check
```

Compiler guard/settings are exactly solc
`0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200 runs, via-IR, Cancun,
and disabled appended metadata/bytecode hash. Checked outputs:

- `Throwable0Interpreter.sol`: source SHA-256
  `58315c6ecaa09888cc9c12b996e525137b8489c08950e516873895118cbe48b3`
- `Throwable0Interpreter.runtime.hex`: 212,574 runtime bytes; runtime-byte
  SHA-256 `c1a9a48d598e7efb7eaf636222ee596e767a22e5859384acd33e99314acf2084`
- `Throwable0Interpreter.abi.json`: exact four-method TL0 ABI
- `artifacts/Throwable0Interpreter.json`: combined ABI/runtime/compiler/source
  provenance embedded by package `tl0assets`

The runtime is below the separate 256 KiB LOCAL ceiling but far above EIP-170 and
EIP-3860 limits. It is for explicit local code installation and `runtime.Call`,
not CREATE or standard-chain deployment evidence. Ordinary calls remain bounded at
100,000,000 gas / 30 seconds and dedicated boundaries at 1,000,000,000 gas /
120 seconds, with the unchanged 25,000,000-gas commit reserve and 1..4096 JVM and
internal units per call. Parent acceptance, retained corrections and actual gates
are in `JAVA_EVM_MC_TL0_REVIEW.md`. This is not Java SE, Minecraft startup, VFS,
scheduling, I/O, listeners, or Throwable APIs/stack traces.
