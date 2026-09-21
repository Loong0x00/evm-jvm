# Generated-only `IndexOutOfBoundsException(String)` preflight

This is a bounded evidence stage rooted at `parent-aaea6e3ee` (`aaea6e3ee` basis), prepared from generated parent-stage inputs only.  It neither reads nor executes original artifacts, JARs, classes, resources, worlds, or network inputs.  It is not a Minecraft, logger, factory, resource, or Done claim and awaits parent review.

## Exact delta

Only two of the 94 ordered bootstrap leaves change:

| slot | binary class | retained constructor | added Java 8 `-g:none` constructor | image SHA-256 |
| ---: | --- | --- | --- | --- |
| 16 | `java/lang/RuntimeException` | `()V` | `(String)V -> Exception(String)` | `a0305062fca2636aca4ae17927cf84b5b7d25532f1c560fc096a4f82d5c85507` |
| 22 | `java/lang/IndexOutOfBoundsException` | `()V` | `(String)V -> RuntimeException(String)` | `f62b62e31b9b00e3ffb84929e809095c7affde45b9046f4aee81d530e01ee8f6` |

The candidates are 210 and 226 bytes, respectively.  `root-commitment.json` proves that the only changed leaves are 16 and 22: parent root `9e217e600d4bd9f7ecfcbd3d40644677a9f02e4a47d2c17d8af1d5b907cbdf33`, candidate root `7fd833d2d922a772a5d1b1b5d019ab703682d5dac65ed9a29856226097e70d58`.

No `Throwable` overload is added.  The source verifier also pins raw class count/bytes `50/324338`, diagnostic bound `144`, native binding count `13`, all 92 other ordered leaves, retained no-arg constructors, baseline `367235`, and cap `393216`.

## Reproduction and result

From this repository root, with the checked-in stage and the already pinned local `jvmevm/runtime/node_modules`:

```sh
stage=evidence/java-evm/minecraft-entry/index-out-of-bounds-string-constructor-preflight
python3 "$stage/tools/build.py" build/java-diff-mc-index-out-of-bounds-string-constructor-build-REPRO
python3 "$stage/tools/generate_fixtures.py" build/java-diff-mc-index-out-of-bounds-string-constructor-fixtures-REPRO
python3 "$stage/tools/gate.py" \
  build/java-diff-mc-index-out-of-bounds-string-constructor-build-REPRO \
  build/java-diff-mc-index-out-of-bounds-string-constructor-fixtures-REPRO \
  build/java-diff-mc-index-out-of-bounds-string-constructor-gate-REPRO
```

The recorded fresh local full gate completed in **843.586 s** (limit 1200 s): 498 generated-only commands and 12,877 strict canonical receipts.  Rebuilt engine is 367361 bytes (`SHA-256 41e0325576951b56822b5b857192f31d36c040ece16349a60f46de1914e90c9a`, Keccak `a7e59788ca91f964a98e55b1588163056c9634dc3400ab5faf6cfafdb0c874e1`); coordinator remains 5394 bytes (Keccak `23f6896bf51b174bdc4d55bd2076d4ef77a277767c13bf7da21276c600e1e06b`).  Exact build pins are in `build-pins.json`.

The gate establishes q1/q7/direct/reopen equivalence for caught empty, ASCII `index-42`, and null messages; identity with `getMessage()` and `Throwable.getMessage()`; uninitialized non-invocation; uncaught terminal `java/lang/IndexOutOfBoundsException`; and root-unchanged rejection of both omitted `(Throwable)V` and `(String,Throwable)V` RuntimeException overloads (`CallError` selector `0xd631c3a4`, method slots 8 and 10).  Its source and receipt verifiers bind all reported roots, opaque payloads, counters, package reads, and limits.
