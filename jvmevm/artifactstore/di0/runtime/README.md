# MC-DI0 bounded EVM resource decoder runtime candidate

Status: frozen-plan production runtime candidate, **not accepted DI0**. This package
contains the `DI0Resource` Solidity source, pinned reproducible build, exact combined
artifact, and defensive Go embed. It decodes generated/test ZIP method 0 and raw
DEFLATE method 8 resources using accepted AS0/ZI0 EVM dependencies, verifies output
length and CRC32, and publishes immutable EVM-created output pages.

It does not inflate or execute the official server JAR, implement Java/ClassLoader,
run Minecraft, accept an EULA, open a listener, or prove a genuine `Done` marker.
It changes no accepted AS0/ZI0/VFS/core artifact, consensus behavior, opcode,
precompile, gas accounting, or accepted non-DI0 quota.

Build/check from this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm run check
```

Pinned compiler: solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
via-IR, Cancun, `appendCBOR=false`, `bytecodeHash=none`. The build enforces the exact
33-function ABI, constructor/error-only additional ABI entries, no events/fallback/
receive/immutables/links, runtime <=24,576 bytes, and maximum complete init input
(including the 384-byte ABI encoding of a 256-byte name) <=49,152 bytes.

Final candidate build pins (hashes over binary code unless stated otherwise):

- Solidity source: 18,513 bytes, SHA-256
  `682d8243a6a0671f151316c8bce0a220ec1934205ca5bb4144a4d635463b4470`.
- Constructor bytecode: 17,216 bytes; maximum complete init input 17,600 bytes;
  SHA-256 `604d6a515fcb5efb539f998987ddba94c7f1e1d1fe3e712a5b95606bc1dab576`.
- Runtime: 14,978 bytes; SHA-256
  `8c309455d3b0817725cd775f909abc2477b39fed6e18235114737480b05e17b0`;
  Keccak-256 `946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37`.
- Combined artifact file SHA-256:
  `72773d5c53533969a6b0d0a1391513330affb11b4cdf300fa4c115bab23613ca`.

The DI0-only bounds are 256 KiB plaintext, 32 KiB history distance, 32-byte copy
or stored actions, 8,192-byte output pages (at most 32), 4,096-byte reads, requested
step units 1..128 as a gas-aware upper bound, exactly one publish unit, and a fixed
25,000,000-gas reserve before each action after the first. Ordinary and boundary
runtime gates remain 100M/30s and 1B/120s respectively; those are test budgets, not
universal gas claims.

See `evidence/java-evm/di0/runtime-candidate/` for final candidate build and replay
records. Only parent integration and independent final gates may accept DI0.
