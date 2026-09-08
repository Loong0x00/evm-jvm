# Stock S1 runtime

This directory is the pinned Solidity-only Stock S1 implementation. It is
separate from the accepted S0 contracts and from the oversized monolithic Java
interpreter.

`S1ClassParser` reads an unchanged `STOP || classfile` page, parses and verifies
the frozen Java-52 integer profile in EVM, and creates one immutable
`S1MetadataPage` through ordinary `CREATE`. The append-only parser registry is
the provenance boundary for `S1StepModule` and `S1Coordinator`. Method offsets,
instruction starts, branch targets and integer literal records are never supplied
by the host. Metadata uses the exact schema-2 six-header/four-method-word/packed
8-byte-literal format in `JAVA_EVM_STOCK_S1_PLAN.md`.

The stateless step module executes 1..128 complete instructions from the selected
raw Code. The coordinator commits the parser/class/method/module/input roots,
initializes 0..4 tagged `int32` arguments, stores an eight-stack/eight-local
`MachineV2`, and enforces the immutable 1..4096 total-step cap. A return at the
cap wins; otherwise cap exhaustion commits lifecycle `STEP_LIMIT`. Equal-PC and
equal-machine loop batches are valid progress when `executed` is nonzero.

Raw class pages continue to use the accepted S0 `ArtifactPage`; it is deliberately
not rebuilt or copied here.

## Reproducible build

```sh
cd jvmevm/stock/s1/runtime
npm ci
npm run build
npm run check
```

Pinned settings are solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer
200, via-IR, Cancun, with compiler metadata disabled. The closed build input is
only the six Solidity files listed in `build.js`. Artifacts contain ABI, init and
runtime bytecode, compiler immutable references, and all source SHA-256 pins.

| Artifact | Init bytes / SHA-256 | Runtime bytes / SHA-256 | Runtime keccak256 |
|---|---|---|---|
| `S1MetadataPage` template | 461 / `f1e2b84dc69f1a3bf22ff3dc6f2ad0ae95b1f047ba78c1ab1321c64e72995092` | 3 / `0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438` | `3c55237b3869f93f3e570793afec9785f20a4ee7cd0a7798a418838c833228e0` |
| `S1ClassParser` | 15419 / `e1e33ded624ed235a386074f44f733b2ceac8e80b6be95673bd4597d5ccf54a9` | 15393 / `395432e7fac77737298c50ee6c6ec51ac8136458a19ce97af991b69ad0fb5ef8` | `1a4b537b2c0543eeb4630a69e6e4c9d02f07540c0ac2553fed07d03879d23152` |
| `S1StepModule` | 8434 / `aee17e251279c7f8b12f6a3962045b1864fc38a457ac9c11ae894b61952d9704` | 8408 / `9c70f525c57139efdae676555ada7fc28dfc307be1694376f7e525a675dcee35` | `25f120b421ba7ce996ebbc61debf109dc4567b2947933daf51082fc02d06af21` |
| `S1Coordinator` | 11661 / `9360d22ecde4336b17df12902771c4bf3c0375eb4ac7612f55d79bb8a605a5c8` | 6328 / `957472808404f19124cb5b5f8440e5186d8d3f7eec60da9451fb150a2a37e9f8` | `057b718f8b13b64082b73c99d40012d1635a111ef5e26523cee5b248ddfbc060` |

The metadata template returns dynamic runtime `STOP || payload`; its maximum
constructor input is 8717 bytes and maximum runtime is 8192 bytes. All executable
and initcode limits in the frozen plan are met.

## Bounded implementation probes

Ignored local probes under `build/java-diff-stock-s1-runtime/` regenerated the
five trusted classes with `javac --release 8` and exercised ordinary EVM CREATE
and calls. A full direct-runtime matrix passed all **82** unchanged M1/M2 rows,
all JVM final values, and the exact total of 2213 executed instructions at budget
128. Its largest resume used 468014 EVM gas. This direct matrix excludes signed
transaction intrinsic gas and is not an acceptance substitute.

A separate signed `TransactionToMessage`/`core.ApplyMessage` probe used nonce and
transaction checks, chain ID 1337 all-dev rules, ordinary CREATE, and no code or
storage injection. Actual registration gas was: Comparisons 1837095, Constants
1490883, LocalsAndArithmetic 1474137, Loops 858374, and M1Baseline 553739. The
created metadata runtimes were respectively 1857, 1857, 1601, 705, and 577 bytes.
`sum(100)` at budget 64 returned 5050 after 13 resumes; signed resume gas ranged
193829..285628 and coordinator CREATE used 1634492 gas. A trusted `goto 0`
probe committed `STEP_LIMIT` with unchanged PC at exact caps 1 and 128 (executed
1 and 128 respectively), rather than tripping a same-PC guard. A CP512/Code256
boundary registered in 2416325 gas and returned its cached `ldc_w` value in two
128-step resumes; a separate exact 32-declared-method boundary registered in
2766135 gas. Parser and module CREATE used 3380422 and 1871498 gas. These measurements fit the frozen 8M setup and 2M
resume limits, but they do not replace the parent's independent signed 82-row,
negative, rollback, gas-threshold, and replay gates.
