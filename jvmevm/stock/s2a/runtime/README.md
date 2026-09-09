# Stock S2a runtime

This directory contains the pinned Solidity-only Stock S2a implementation. It is
versioned separately from S0, S1, and the oversized monolithic interpreter.

`S2aClassParser` reads unchanged `STOP || classfile` pages and creates immutable
schema-3 metadata through ordinary `CREATE`. The schema retains S1's exact
six-header/four-word-method/packed-eight-byte-literal layout and uses the S2A
class/program/input hash domains. Ineligible methods retain zero Code-derived
metadata, so an unused Code body over 256 bytes or a method with more than the
eligible aggregate literal allowance does not reject or contaminate an otherwise
valid class.

`S2aStepModule` is a stateless, registry-bound, one-frame executor. In addition
to S1 instructions it implements `idiv`, `irem`, `ishl`, `ishr`, `iushr`,
`iand`, `ior`, `ixor`, `i2b`, `i2c`, and `i2s`. A validated zero divisor commits
a terminal `JAVA_FAULT` kind 1 while preserving the pre-instruction PC, operands,
and locals. `S2aCoordinator` stores the exact 23-word `MachineV3`, enforces the
1..4096 total-step cap, validates fault provenance against immutable Code, and
keeps the 800,000-gas commit reserve and 1..32 conservative dirty-word bound.
Return or Java fault at the exact cap wins over `STEP_LIMIT`.

This is only the frozen scalar integer/fault slice: it has no calls, frame store,
call records, private/void/six-argument execution, stack-overflow execution,
heap, arrays, statics, handlers, or host metadata/result/evaluation fallback.
Raw pages deliberately reuse the accepted S0 `ArtifactPage` unchanged.

## Reproducible build

```sh
cd jvmevm/stock/s2a/runtime
npm ci
npm run build
npm run check
```

The closed build reads only the six Solidity files listed in `build.js`. Settings
are solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, via-IR,
Cancun, with compiler metadata disabled.

| Artifact | Init bytes / SHA-256 | Runtime bytes / SHA-256 | Runtime keccak256 |
|---|---|---|---|
| `S2aMetadataPage` template | 339 / `728282836fee88ff7739d925d991ef2c26f50e21794ee1c1af002d598f957a4f` | 3 / `0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438` | `3c55237b3869f93f3e570793afec9785f20a4ee7cd0a7798a418838c833228e0` |
| `S2aClassParser` | 15685 / `7309868e22cbafbec5c921066ab1da5d43b71d5623e45ce8a8f98aafd31baa2a` | 15659 / `8ae89c4943c83f7a138440a1227a094415a107f87bcf7a7e814bc4f911453b7d` | `9746182e3ecdfeace27d26210aaf92997c1b8a74ae34f987bc2a4955433eae6e` |
| `S2aStepModule` | 9496 / `6c13f3f52ac9ef5bc95ff148a3d6ebc6cf699606cbd8932cc4b1cefb9ec90262` | 9470 / `0f4e6a75ab95b7e289bd91ad8f587b63f9d5b2503934b10fbca5b498dd99129f` | `d004fc0eae66bbf550a65449528b8ff2d96c7f46b5caeed9177b8a68b0164226` |
| `S2aCoordinator` | 13140 / `a215165f52922752d099646feeb2ca4bc90a6dc47b191322e6c248fbd4e6a42f` | 7694 / `e464b3a2237b598de447d369f1cdcb9af568ba7eba2a06168ee1e12a44292212` | `82bbb59342eaeedd9ee649102ed3d70917cafc9f7ec68417669cbe9f41658cc5` |

The metadata template's maximum ABI-padded constructor input is 8595 bytes and
its maximum runtime is 8192 bytes. Parser runtime is below 16 KiB; other runtime
templates are below 12 KiB; all initcode templates are below 24 KiB.

## Bounded implementation probe

An ignored local probe under `build/java-diff-stock-s2a-runtime/` compiled one
trusted Java-52 class with `javac --release 8`, then used signed transactions on
an in-process chain (chain ID 1337, Osaka rules, 30M block gas) and ordinary
`CREATE`; it did not inject code or storage. It exercised all eleven added
opcodes, including `MIN_VALUE / -1`, `MIN_VALUE % -1`, signed and unsigned
shifts, bitwise operations, narrowings, and a genuine zero-divisor terminal
fault. Measured gas was parser CREATE 3,438,259; module CREATE 2,101,166; raw-page
CREATE 411,413; class registration 1,230,550; maximum coordinator CREATE
1,977,254; and maximum resume 257,427. These focused measurements satisfy the
8M setup and 2M resume ceilings but are not a 201-row acceptance claim and do not
replace the parent harness/verifier gates.
