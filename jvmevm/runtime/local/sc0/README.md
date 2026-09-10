# MC-SC0 local String continuation runtime

`String0Interpreter.sol` is the schema-1 SC0 successor to accepted MC-TL0. It is
derived from accepted TL0 source SHA-256
`58315c6ecaa09888cc9c12b996e525137b8489c08950e516873895118cbe48b3`; no
accepted runtime is modified.

SC0 retains TL0's four-method ABI, continuation codec widths, Throwable identity,
wrapper-cause records, quotas and finite execution controls under the distinct
`JVMSC001`/`SCS1` namespace. It substitutes only the pinned 984-byte String image,
adds genuine Java bytecode `String(char[])` and `String(String)` construction, and
content-based receiver insertion for `intern()`. String allocation enforces the
exact no-callback `Object.<init>:()V` profile. Checkpoint validation reconstructs
String layout and checks partial construction, reachability, immutable backing
aliases, intern ordering and hashes without executing Java or repairing state.

Pinned bootstrap inputs:

- `bootstrap/java/lang/String.java`: SHA-256
  `95542f5d4b869cc96ee395c322f8368a275fe3338ae60c7810afded6d4b81f2e`
- decoded `String.class.hex`: 984 bytes, SHA-256
  `7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad`
- reproduction: `javac --release 8 -g:none` (using the build's Java-base patch
  arrangement), with the class bytes cross-checked against embedded Solidity.

## Reproducible Solidity build

```sh
npm ci --ignore-scripts
npm run build
npm run check
```

The build pins solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
via-IR, Cancun and disabled metadata. The runtime ceiling is 256 KiB and checkpoint
ceiling is 1 MiB. This oversized runtime is for explicit LOCAL code installation,
not CREATE or standard-chain deployment evidence. Calls retain 100M ordinary / 1B
boundary gas and the 25M commit reserve. This runtime is not an SC0 acceptance,
Java SE, Minecraft startup, VFS, I/O, scheduling, listeners or EULA execution claim.
