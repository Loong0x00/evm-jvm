# Stock-EVM S1 workload/oracle preflight proposal

**Status: proposal and measured oracle inventory only; no S1 implementation is
frozen.**  This document is based on accepted commit
`a6adae7546564bc1d3abc4488db16e45d42b51fa` (`a6adae7`). Authority remains
`JAVA_EVM_PROGRAM.md`; accepted S0 remains `JAVA_EVM_STOCK_S0_PLAN.md`. A parent
stage contract must choose the production interface, write sets, limits and gas
thresholds before implementation.

This slice did not edit or execute production Solidity, Go tests, fixtures, tools,
the Makefile, or either authoritative plan. It did not download or execute
Minecraft, accept an EULA, open a listener, change geth/EVM rules, or establish a
full-interpreter/MC deployment claim. All extra generated inputs below are trusted,
local, TEST-oracle-only material under ignored
`build/java-diff-stock-s1-oracles/`.

## 1. Reproducible evidence and scope

The authoritative legacy catalogue is every `cases.json` entry whose `stage` is
`m1` or `m2`: **82 entries** (12 M1 + 70 M2), in manifest order. The manifest is
`jvmevm/testdata/differential/cases.json`, schema 1, SHA-256
`a36da915ca07170b6a0ae54f05693c95d2e4c74415268f47b36787dd02dac440`.
The ordered, measured 82-row JSONL catalogue at this revision has SHA-256
`c3b128e46838d2e1e13176dad106b918eb69716b49c17b2c5a8591dbbeb5954c`
(`build/java-diff-stock-s1-oracles/catalogue.jsonl`). This JSONL is evidence, not
a frozen production encoding or on-chain commitment.

Commands actually run:

```sh
javac --release 8 -d build/java-diff-stock-s1-oracles/compiled \
  jvmevm/testdata/differential/OracleMain.java \
  jvmevm/testdata/differential/{Comparisons,Constants,LocalsAndArithmetic,Loops,M1Baseline}.java
python3 build/java-diff-stock-s1-oracles/inventory.py
make java-build
PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py --stage m2 --tier full \
  --artifacts build/java-diff-stock-s1-oracles/legacy-evm
```

The compiler was `javac 21.0.9` targeting Java 8 classfiles. The exact same
compiled guest bytes were invoked through `OracleMain` on OpenJDK
`1.8.0_504` and Java `21.0.9`; all 82 returned the same signed int value. The
current oversized local EVM runtime also passed 82/82, runtime 154839 bytes,
SHA-256 `dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
That run's report is
`build/java-diff-stock-s1-oracles/legacy-evm/report.json`, SHA-256
`292a0f55477929ff29122de8da11ff3e460ee0eb8a9ca9b5f71bcd8988e0032e`.
Its per-call gas was 400109..2923901 (sum 45237402) under the unchanged manifest
limits; this is **not stock signed-transaction gas** and not deployment evidence.

Dynamic instruction counts below come from a bounded TEST-only decoder/interpreter
over these five trusted classfiles (100000-instruction guard), with each final
value cross-checked against both JVMs and the existing EVM result. It neither
rewrites the class nor participates in a production path. Evidence is
`inventory.py` SHA-256
`5ff6748af176031593f1cae87355354c9f95e057f373827202ce5194bc3cd790`
and `inventory.json` SHA-256
`4965bcc669f817c8977877c2fe167e490122ca5c801ea64456ca0f2342888b5c`.
A future acceptance test may use this bounded static reference or a trusted
instrumented TEST oracle, but production must derive progress/results in EVM from
unchanged raw guest bytes.

### Source and emitted class identities

There are five committed trusted sources and five generated (not committed)
classfiles. Page size means actual S0-style runtime `STOP || rawClass`.

| Source (under `jvmevm/testdata/differential/`) | Source SHA-256 | Generated class SHA-256 | raw / page bytes | CP count field | methods |
|---|---|---|---:|---:|---:|
| `M1Baseline.java` | `a75eb606dd691cd5cbb69bb07023939af5148448e5cca7f4054456270bffa2b6` | `1e71a54ba434b943b44c8633a1fb9e4c52e4f435eaeffb5ebf47e546c49d0813` | 308 / 309 | 17 | 3 |
| `Constants.java` | `66ef864e5f29cfb6263c5cb727f9347bb7266dbfae6fef001a7579bd8681ec79` | `6b3473ae373a53d0c6a8a2a8df4b00b978a9c2db4890bacf14900717d60701a1` | 824 / 825 | 27 | 13 |
| `LocalsAndArithmetic.java` | `fafa4e9b21ddcac1f88d499a024c7a006d63a49df4045fa38518bba18eff7797` | `423ca06bab0adebb43e8d98df8438840fe4635bfa73e2e6c28b6397d1b195653` | 845 / 846 | 27 | 11 |
| `Comparisons.java` | `0b9cf54b1d4c14eaeba0473c9546ff8ca142a33e1ac91f57f548a5353c10d307` | `5c4a076b97e146ed73e14a5bea4f3722d3a18be284abd23bf0a56a5848d3cb9e` | 1115 / 1116 | 28 | 13 |
| `Loops.java` | `b83e4bb5c85be1ee4c17a64406b8e02d356f38deceee2932597c5cb6dc5d6d09` | `c9043994623a900a6c1f4ed096c9d1c23783842d2e5e1406646deea9db20fa38` | 512 / 513 | 19 | 4 |

All are major 52/minor 0, public ordinary classes with direct Object superclass,
no interfaces, fields, or `<clinit>`. Across the **39 distinct selected roots**:
argument count is 0..4, `max_stack` 1..2, `max_locals` 0..6, and Code length
2..24 bytes. Catalogue argument-count distribution is 0:8, 1:42, 2:25, 3:4,
4:3. Per-class maxima are raw page 1116 bytes and CP count 28, far inside S0's
4097-byte page/CP512 bounds. `genericLocals(IIII)I` really is the local-six
boundary; `sum(100)` really executes 806 bytecodes, and `fibonacci(30)` 368.

### Exact selected instruction profile

The union is 36 opcodes:

- `iconst_m1..iconst_5` (`02..08`), `bipush` (`10`), `sipush` (`11`);
- `iload` (`15`), `iload_0..3` (`1a..1d`), `istore` (`36`),
  `istore_0..3` (`3b..3e`);
- `iadd` (`60`), `isub` (`64`), `iinc` (`84`), `ireturn` (`ac`);
- unary signed branches `ifeq..ifle` (`99..9e`), binary signed int branches
  `if_icmpeq..if_icmple` (`9f..a4`), and `goto` (`a7`).

There are 18 distinct method/PC branch edges. Offsets are signed big-endian s16
and targets are relative to the **branch opcode PC**, not the following PC. The
complete edge inventory is in the method table; notably the real backward edges
are `sum:13 + (-11) -> 2` and `fibonacci:19 + (-15) -> 4`.

## 2. Exact root inventory

| Root | argc | stack | locals | code B | Opcodes | branch edges `pc -> pc+s16` |
|---|---:|---:|---:|---:|---|---|
| `M1Baseline.identity(I)I` | 1 | 1 | 1 | 2 | `iload_0`, `ireturn` | — |
| `M1Baseline.add(II)I` | 2 | 2 | 2 | 4 | `iadd`, `iload_0`, `iload_1`, `ireturn` | — |
| `Constants.minusOne()I` | 0 | 1 | 0 | 2 | `iconst_m1`, `ireturn` | — |
| `Constants.zero()I` | 0 | 1 | 0 | 2 | `iconst_0`, `ireturn` | — |
| `Constants.one()I` | 0 | 1 | 0 | 2 | `iconst_1`, `ireturn` | — |
| `Constants.two()I` | 0 | 1 | 0 | 2 | `iconst_2`, `ireturn` | — |
| `Constants.three()I` | 0 | 1 | 0 | 2 | `iconst_3`, `ireturn` | — |
| `Constants.four()I` | 0 | 1 | 0 | 2 | `iconst_4`, `ireturn` | — |
| `Constants.five()I` | 0 | 1 | 0 | 2 | `iconst_5`, `ireturn` | — |
| `Constants.addByte(I)I` | 1 | 2 | 1 | 5 | `bipush`, `iadd`, `iload_0`, `ireturn` | — |
| `Constants.addNegativeByte(I)I` | 1 | 2 | 1 | 5 | `bipush`, `iadd`, `iload_0`, `ireturn` | — |
| `Constants.addShort(I)I` | 1 | 2 | 1 | 6 | `iadd`, `iload_0`, `ireturn`, `sipush` | — |
| `Constants.subtractShort(I)I` | 1 | 2 | 1 | 6 | `iload_0`, `ireturn`, `isub`, `sipush` | — |
| `Constants.negativeShort()I` | 0 | 1 | 0 | 4 | `ireturn`, `sipush` | — |
| `LocalsAndArithmetic.subtract(II)I` | 2 | 2 | 2 | 4 | `iload_0`, `iload_1`, `ireturn`, `isub` | — |
| `LocalsAndArithmetic.store0(II)I` | 2 | 1 | 2 | 4 | `iload_0`, `iload_1`, `ireturn`, `istore_0` | — |
| `LocalsAndArithmetic.store1(II)I` | 2 | 1 | 2 | 4 | `iload_0`, `iload_1`, `ireturn`, `istore_1` | — |
| `LocalsAndArithmetic.store2(III)I` | 3 | 2 | 3 | 6 | `iadd`, `iload_0`, `iload_1`, `iload_2`, `ireturn`, `istore_2` | — |
| `LocalsAndArithmetic.store3(IIII)I` | 4 | 2 | 4 | 8 | `iadd`, `iload_0`, `iload_1`, `iload_2`, `iload_3`, `ireturn`, `istore_3` | — |
| `LocalsAndArithmetic.genericLocals(IIII)I` | 4 | 2 | 6 | 16 | `iadd`, `iload`, `iload_0`, `iload_1`, `iload_2`, `iload_3`, `ireturn`, `istore` | — |
| `LocalsAndArithmetic.increment(I)I` | 1 | 1 | 1 | 5 | `iinc`, `iload_0`, `ireturn` | — |
| `LocalsAndArithmetic.decrement(I)I` | 1 | 1 | 1 | 5 | `iinc`, `iload_0`, `ireturn` | — |
| `LocalsAndArithmetic.increment127(I)I` | 1 | 1 | 1 | 5 | `iinc`, `iload_0`, `ireturn` | — |
| `LocalsAndArithmetic.decrement128(I)I` | 1 | 1 | 1 | 5 | `iinc`, `iload_0`, `ireturn` | — |
| `Comparisons.equalZero(I)I` | 1 | 1 | 1 | 8 | `iconst_0`, `iconst_1`, `ifne`, `iload_0`, `ireturn` | `1->6(+5)` |
| `Comparisons.notEqualZero(I)I` | 1 | 1 | 1 | 8 | `iconst_0`, `iconst_1`, `ifeq`, `iload_0`, `ireturn` | `1->6(+5)` |
| `Comparisons.lessThanZero(I)I` | 1 | 1 | 1 | 8 | `iconst_0`, `iconst_1`, `ifge`, `iload_0`, `ireturn` | `1->6(+5)` |
| `Comparisons.greaterOrEqualZero(I)I` | 1 | 1 | 1 | 8 | `iconst_0`, `iconst_1`, `iflt`, `iload_0`, `ireturn` | `1->6(+5)` |
| `Comparisons.greaterThanZero(I)I` | 1 | 1 | 1 | 8 | `iconst_0`, `iconst_1`, `ifle`, `iload_0`, `ireturn` | `1->6(+5)` |
| `Comparisons.lessOrEqualZero(I)I` | 1 | 1 | 1 | 8 | `iconst_0`, `iconst_1`, `ifgt`, `iload_0`, `ireturn` | `1->6(+5)` |
| `Comparisons.equal(II)I` | 2 | 2 | 2 | 9 | `iconst_0`, `iconst_1`, `if_icmpne`, `iload_0`, `iload_1`, `ireturn` | `2->7(+5)` |
| `Comparisons.notEqual(II)I` | 2 | 2 | 2 | 9 | `iconst_0`, `iconst_1`, `if_icmpeq`, `iload_0`, `iload_1`, `ireturn` | `2->7(+5)` |
| `Comparisons.lessThan(II)I` | 2 | 2 | 2 | 9 | `iconst_0`, `iconst_1`, `if_icmpge`, `iload_0`, `iload_1`, `ireturn` | `2->7(+5)` |
| `Comparisons.greaterOrEqual(II)I` | 2 | 2 | 2 | 9 | `iconst_0`, `iconst_1`, `if_icmplt`, `iload_0`, `iload_1`, `ireturn` | `2->7(+5)` |
| `Comparisons.greaterThan(II)I` | 2 | 2 | 2 | 9 | `iconst_0`, `iconst_1`, `if_icmple`, `iload_0`, `iload_1`, `ireturn` | `2->7(+5)` |
| `Comparisons.lessOrEqual(II)I` | 2 | 2 | 2 | 9 | `iconst_0`, `iconst_1`, `if_icmpgt`, `iload_0`, `iload_1`, `ireturn` | `2->7(+5)` |
| `Loops.sum(I)I` | 1 | 2 | 2 | 18 | `goto`, `iadd`, `iconst_0`, `ifle`, `iinc`, `iload_0`, `iload_1`, `ireturn`, `istore_1` | `3->16(+13)`<br>`13->2(-11)` |
| `Loops.fibonacci(I)I` | 1 | 2 | 4 | 24 | `goto`, `iadd`, `iconst_0`, `iconst_1`, `ifle`, `iinc`, `iload_0`, `iload_1`, `iload_2`, `iload_3`, `ireturn`, `istore_1`, `istore_2`, `istore_3` | `5->22(+17)`<br>`19->4(-15)` |
| `Loops.select(III)I` | 3 | 1 | 4 | 13 | `goto`, `ifne`, `iload_0`, `iload_1`, `iload_2`, `iload_3`, `ireturn`, `istore_3` | `1->9(+8)`<br>`6->11(+5)` |

## 3. Exact 82-entry outcome and step catalogue

Every outcome shown as `JVM 8 / JVM 21`; both columns used the identical class
SHA listed above. `original gas` is retained manifest metadata, never a proposed
stock transaction budget.

| # | Existing ID | Root | Args | JVM 8 / JVM 21 | Steps | original gas |
|---:|---|---|---|---:|---:|---:|
| 1 | `m1-identity-zero` | `M1Baseline.identity(I)I` | `[0]` | 0 / 0 | 2 | 2000000 |
| 2 | `m1-identity-positive` | `M1Baseline.identity(I)I` | `[123456789]` | 123456789 / 123456789 | 2 | 2000000 |
| 3 | `m1-identity-negative` | `M1Baseline.identity(I)I` | `[-987654321]` | -987654321 / -987654321 | 2 | 2000000 |
| 4 | `m1-identity-max` | `M1Baseline.identity(I)I` | `[2147483647]` | 2147483647 / 2147483647 | 2 | 2000000 |
| 5 | `m1-identity-min` | `M1Baseline.identity(I)I` | `[-2147483648]` | -2147483648 / -2147483648 | 2 | 2000000 |
| 6 | `m1-add-basic` | `M1Baseline.add(II)I` | `[20,22]` | 42 / 42 | 4 | 2000000 |
| 7 | `m1-add-zeroes` | `M1Baseline.add(II)I` | `[0,0]` | 0 / 0 | 4 | 2000000 |
| 8 | `m1-add-mixed-sign` | `M1Baseline.add(II)I` | `[-200,75]` | -125 / -125 | 4 | 2000000 |
| 9 | `m1-add-negative` | `M1Baseline.add(II)I` | `[-1000000,-2000000]` | -3000000 / -3000000 | 4 | 2000000 |
| 10 | `m1-add-overflow-positive` | `M1Baseline.add(II)I` | `[2147483647,1]` | -2147483648 / -2147483648 | 4 | 2000000 |
| 11 | `m1-add-overflow-negative` | `M1Baseline.add(II)I` | `[-2147483648,-1]` | 2147483647 / 2147483647 | 4 | 2000000 |
| 12 | `m1-add-max-pair` | `M1Baseline.add(II)I` | `[2147483647,2147483647]` | -2 / -2 | 4 | 2000000 |
| 13 | `m2-constant-minus-one` | `Constants.minusOne()I` | `[]` | -1 / -1 | 2 | 4000000 |
| 14 | `m2-constant-zero` | `Constants.zero()I` | `[]` | 0 / 0 | 2 | 4000000 |
| 15 | `m2-constant-one` | `Constants.one()I` | `[]` | 1 / 1 | 2 | 4000000 |
| 16 | `m2-constant-two` | `Constants.two()I` | `[]` | 2 / 2 | 2 | 4000000 |
| 17 | `m2-constant-three` | `Constants.three()I` | `[]` | 3 / 3 | 2 | 4000000 |
| 18 | `m2-constant-four` | `Constants.four()I` | `[]` | 4 / 4 | 2 | 4000000 |
| 19 | `m2-constant-five` | `Constants.five()I` | `[]` | 5 / 5 | 2 | 4000000 |
| 20 | `m2-bipush-add` | `Constants.addByte(I)I` | `[23]` | 123 / 123 | 4 | 4000000 |
| 21 | `m2-bipush-add-overflow` | `Constants.addByte(I)I` | `[2147483600]` | -2147483596 / -2147483596 | 4 | 4000000 |
| 22 | `m2-bipush-negative` | `Constants.addNegativeByte(I)I` | `[-23]` | -123 / -123 | 4 | 4000000 |
| 23 | `m2-sipush-add` | `Constants.addShort(I)I` | `[1234]` | 31234 / 31234 | 4 | 4000000 |
| 24 | `m2-sipush-add-overflow` | `Constants.addShort(I)I` | `[2147480000]` | -2147457296 / -2147457296 | 4 | 4000000 |
| 25 | `m2-sipush-subtract` | `Constants.subtractShort(I)I` | `[-1234]` | -31234 / -31234 | 4 | 4000000 |
| 26 | `m2-sipush-negative` | `Constants.negativeShort()I` | `[]` | -20000 / -20000 | 2 | 4000000 |
| 27 | `m2-subtract-basic` | `LocalsAndArithmetic.subtract(II)I` | `[100,58]` | 42 / 42 | 4 | 4000000 |
| 28 | `m2-subtract-negative` | `LocalsAndArithmetic.subtract(II)I` | `[-200,75]` | -275 / -275 | 4 | 4000000 |
| 29 | `m2-subtract-overflow-positive` | `LocalsAndArithmetic.subtract(II)I` | `[2147483647,-1]` | -2147483648 / -2147483648 | 4 | 4000000 |
| 30 | `m2-subtract-overflow-negative` | `LocalsAndArithmetic.subtract(II)I` | `[-2147483648,1]` | 2147483647 / 2147483647 | 4 | 4000000 |
| 31 | `m2-store-local-zero` | `LocalsAndArithmetic.store0(II)I` | `[11,-22]` | -22 / -22 | 4 | 4000000 |
| 32 | `m2-store-local-one` | `LocalsAndArithmetic.store1(II)I` | `[-33,44]` | -33 / -33 | 4 | 4000000 |
| 33 | `m2-store-local-two` | `LocalsAndArithmetic.store2(III)I` | `[100,23,-999]` | 123 / 123 | 6 | 4000000 |
| 34 | `m2-store-local-three` | `LocalsAndArithmetic.store3(IIII)I` | `[10,20,12,-999]` | 42 / 42 | 8 | 4000000 |
| 35 | `m2-generic-locals-basic` | `LocalsAndArithmetic.genericLocals(IIII)I` | `[10,20,30,40]` | 100 / 100 | 12 | 4000000 |
| 36 | `m2-generic-locals-wrap` | `LocalsAndArithmetic.genericLocals(IIII)I` | `[2147483647,1,-2,3]` | -2147483647 / -2147483647 | 12 | 4000000 |
| 37 | `m2-iinc-one` | `LocalsAndArithmetic.increment(I)I` | `[41]` | 42 / 42 | 3 | 4000000 |
| 38 | `m2-iinc-one-overflow` | `LocalsAndArithmetic.increment(I)I` | `[2147483647]` | -2147483648 / -2147483648 | 3 | 4000000 |
| 39 | `m2-iinc-minus-one` | `LocalsAndArithmetic.decrement(I)I` | `[-41]` | -42 / -42 | 3 | 4000000 |
| 40 | `m2-iinc-minus-one-overflow` | `LocalsAndArithmetic.decrement(I)I` | `[-2147483648]` | 2147483647 / 2147483647 | 3 | 4000000 |
| 41 | `m2-iinc-positive-127` | `LocalsAndArithmetic.increment127(I)I` | `[1000]` | 1127 / 1127 | 3 | 4000000 |
| 42 | `m2-iinc-positive-127-overflow` | `LocalsAndArithmetic.increment127(I)I` | `[2147483600]` | -2147483569 / -2147483569 | 3 | 4000000 |
| 43 | `m2-iinc-negative-128` | `LocalsAndArithmetic.decrement128(I)I` | `[-1000]` | -1128 / -1128 | 3 | 4000000 |
| 44 | `m2-iinc-negative-128-overflow` | `LocalsAndArithmetic.decrement128(I)I` | `[-2147483600]` | 2147483568 / 2147483568 | 3 | 4000000 |
| 45 | `m2-unary-eq-zero-true` | `Comparisons.equalZero(I)I` | `[0]` | 1 / 1 | 4 | 4000000 |
| 46 | `m2-unary-eq-zero-false` | `Comparisons.equalZero(I)I` | `[7]` | 0 / 0 | 4 | 4000000 |
| 47 | `m2-unary-ne-zero-true` | `Comparisons.notEqualZero(I)I` | `[7]` | 1 / 1 | 4 | 4000000 |
| 48 | `m2-unary-ne-zero-false` | `Comparisons.notEqualZero(I)I` | `[0]` | 0 / 0 | 4 | 4000000 |
| 49 | `m2-unary-lt-zero-true` | `Comparisons.lessThanZero(I)I` | `[-1]` | 1 / 1 | 4 | 4000000 |
| 50 | `m2-unary-lt-zero-false` | `Comparisons.lessThanZero(I)I` | `[0]` | 0 / 0 | 4 | 4000000 |
| 51 | `m2-unary-ge-zero-true` | `Comparisons.greaterOrEqualZero(I)I` | `[0]` | 1 / 1 | 4 | 4000000 |
| 52 | `m2-unary-ge-zero-false` | `Comparisons.greaterOrEqualZero(I)I` | `[-1]` | 0 / 0 | 4 | 4000000 |
| 53 | `m2-unary-gt-zero-true` | `Comparisons.greaterThanZero(I)I` | `[1]` | 1 / 1 | 4 | 4000000 |
| 54 | `m2-unary-gt-zero-false` | `Comparisons.greaterThanZero(I)I` | `[0]` | 0 / 0 | 4 | 4000000 |
| 55 | `m2-unary-le-zero-true` | `Comparisons.lessOrEqualZero(I)I` | `[0]` | 1 / 1 | 4 | 4000000 |
| 56 | `m2-unary-le-zero-false` | `Comparisons.lessOrEqualZero(I)I` | `[1]` | 0 / 0 | 4 | 4000000 |
| 57 | `m2-binary-eq-true` | `Comparisons.equal(II)I` | `[-2147483648,-2147483648]` | 1 / 1 | 5 | 4000000 |
| 58 | `m2-binary-eq-false` | `Comparisons.equal(II)I` | `[1,2]` | 0 / 0 | 5 | 4000000 |
| 59 | `m2-binary-ne-true` | `Comparisons.notEqual(II)I` | `[1,2]` | 1 / 1 | 5 | 4000000 |
| 60 | `m2-binary-ne-false` | `Comparisons.notEqual(II)I` | `[7,7]` | 0 / 0 | 5 | 4000000 |
| 61 | `m2-binary-lt-true` | `Comparisons.lessThan(II)I` | `[-2147483648,2147483647]` | 1 / 1 | 5 | 4000000 |
| 62 | `m2-binary-lt-false` | `Comparisons.lessThan(II)I` | `[2,1]` | 0 / 0 | 5 | 4000000 |
| 63 | `m2-binary-ge-true` | `Comparisons.greaterOrEqual(II)I` | `[2147483647,-2147483648]` | 1 / 1 | 5 | 4000000 |
| 64 | `m2-binary-ge-false` | `Comparisons.greaterOrEqual(II)I` | `[-2,-1]` | 0 / 0 | 5 | 4000000 |
| 65 | `m2-binary-gt-true` | `Comparisons.greaterThan(II)I` | `[1,-1]` | 1 / 1 | 5 | 4000000 |
| 66 | `m2-binary-gt-false` | `Comparisons.greaterThan(II)I` | `[-1,1]` | 0 / 0 | 5 | 4000000 |
| 67 | `m2-binary-le-true` | `Comparisons.lessOrEqual(II)I` | `[-1,1]` | 1 / 1 | 5 | 4000000 |
| 68 | `m2-binary-le-false` | `Comparisons.lessOrEqual(II)I` | `[1,-1]` | 0 / 0 | 5 | 4000000 |
| 69 | `m2-sum-0` | `Loops.sum(I)I` | `[0]` | 0 / 0 | 6 | 20000000 |
| 70 | `m2-sum-1` | `Loops.sum(I)I` | `[1]` | 1 / 1 | 14 | 20000000 |
| 71 | `m2-sum-10` | `Loops.sum(I)I` | `[10]` | 55 / 55 | 86 | 20000000 |
| 72 | `m2-sum-25` | `Loops.sum(I)I` | `[25]` | 325 / 325 | 206 | 20000000 |
| 73 | `m2-sum-100` | `Loops.sum(I)I` | `[100]` | 5050 / 5050 | 806 | 20000000 |
| 74 | `m2-fibonacci-0` | `Loops.fibonacci(I)I` | `[0]` | 0 / 0 | 8 | 20000000 |
| 75 | `m2-fibonacci-1` | `Loops.fibonacci(I)I` | `[1]` | 1 / 1 | 20 | 20000000 |
| 76 | `m2-fibonacci-2` | `Loops.fibonacci(I)I` | `[2]` | 1 / 1 | 32 | 20000000 |
| 77 | `m2-fibonacci-10` | `Loops.fibonacci(I)I` | `[10]` | 55 / 55 | 128 | 20000000 |
| 78 | `m2-fibonacci-20` | `Loops.fibonacci(I)I` | `[20]` | 6765 / 6765 | 248 | 20000000 |
| 79 | `m2-fibonacci-30` | `Loops.fibonacci(I)I` | `[30]` | 832040 / 832040 | 368 | 20000000 |
| 80 | `m2-select-zero` | `Loops.select(III)I` | `[0,42,-42]` | 42 / 42 | 7 | 4000000 |
| 81 | `m2-select-nonzero-positive` | `Loops.select(III)I` | `[7,42,-42]` | -42 / -42 | 6 | 4000000 |
| 82 | `m2-select-nonzero-negative` | `Loops.select(III)I` | `[-7,42,-42]` | -42 / -42 | 6 | 4000000 |

The 82 executions total 2213 Java bytecodes. At exact instruction quanta 1, 3,
7 and 16, terminal resume counts would be 2213, 771, 354 and 195 respectively;
maxima are 806, 269, 116 and 51, always `m2-sum-100`. These counts are planning
references, not a host-provided production termination oracle.

## 4. Why accepted S0 rejects these unchanged entries

This is a workload gap, not evidence that S0 failed its frozen profile.

1. **All 82 fail root selection first.** `TinyJvmStepModule._parse` selects only
   literal `run` with descriptor `()I`. None of the five classes declares a
   method named `run`, so each page reaches `StockClassError(5,
   methodCountOffset)`. Even the eight no-argument entries have other names.
2. **Arguments are absent in S0.** 74 entries require 1..4 int arguments. The S0
   coordinator always starts with initialization mask zero and has no committed
   argument vector or descriptor-derived local initialization. Renaming is not
   allowed and wrapping/AOT generation would violate unchanged input.
3. **A real local boundary exceeds S0.** Both `genericLocals` entries declare
   `max_locals=6`; S0 caps at 4 and stores only four locals. This was verified,
   not inferred from source.
4. **Branches are outside S0.** 38 entries (all 24 comparison and all 14 `Loops`
   entries) select one or more `99..a7` opcodes. S0 predecode rejects each as
   `StockBytecodeError(6, pc)`. The other 44 selected bodies use S0-supported
   arithmetic/local opcodes, but still fail points 1/2 and cannot be claimed.
5. **The S0 progress predicate is too strong for loops.** S0 coordinator rejects
   a successful step when PC and `done` are unchanged. In unchanged `sum(10)`,
   budget 8 starts the second resume at PC10 and completes one eight-instruction
   loop cycle back at PC10 while locals change; budgets 8 and 16 repeat this.
   `fibonacci(2)` similarly returns PC14 to PC14 with budget 12. Same PC after a
   nonzero quantum is therefore legitimate progress. Even a valid `goto 0` can
   consume an instruction with identical machine values; `executed>0` and
   monotonic total steps/epoch, not PC inequality, are the safe progress proof.
6. **Repeated parsing is not a migration architecture.** S0 reparses/predecodes
   the full raw class on every step. It was an accepted bounded compromise for
   eight tiny roots, but `sum(100)` needs 51 resumes even at quantum16. Reusable,
   EVM-derived parse/code state is an S1 gate, not permission to raise gas or use
   a host parser.

No class exceeds S0's raw class, CP, max-stack, or Code-size cap; apart from local
six and the explicit root/args/branch gaps, those are not rejection reasons.

## 5. Recommended S1 execution boundary and commitments (not frozen)

### EVM-derived reusable parse/code path

The parent should freeze a small generic profile, not a five-class recognizer:

1. Deploy each exact `STOP || rawClass` page by ordinary CREATE, byte-for-byte.
2. A generic parser/index factory reads that page with `EXTCODECOPY`, validates
   the class inside EVM, resolves the declared class and methods, predecodes code,
   and deploys an immutable canonical index/code page by ordinary CREATE. The
   host must not supply offsets, starts, branch targets, extracted code, stack
   summaries, or a class-specific executable. The EVM-produced page must commit
   its schema, raw payload/page hashes and complete encoded contents.
3. A generic executor reads the immutable index/code page. It must not whitelist
   these five hashes/names or return catalogue values. Exact hashes identify
   test inputs; they are not permission for a fake class filter. Unsupported
   input fails generically.
4. A coordinator pins module code hashes, raw page hash, EVM-produced code-page
   hash and a root-entry commitment, then owns canonical persistent state. Every
   resume executes whole Java instructions and commits atomically.

An acceptable candidate root-entry commitment is
`keccak256(abi.encode(schema, rawPayloadHash, declaredClassNameBytes,
methodNameBytes, descriptorBytes, int32Args, maxTotalSteps))`. Method name and
0..4 arguments may be ABI-packaged by the host, as today, but class/method/Code
resolution and descriptor checking occur in EVM. For this catalogue descriptors
are exactly `()I`, `(I)I`, `(II)I`, `(III)I`, `(IIII)I`; overload ambiguity and
non-public/non-static/non-int roots fail. Do not commit an expected result into
the production execution request.

The state digest should additionally bind an explicit state schema, all module
hashes, raw and code-page hashes, root-entry commitment, machine, epoch and total
steps. A candidate finite S1 machine has PC, SP, at least eight tagged-int stack
cells, six tagged-int locals, a six-bit initialization mask, done and int32
result. Constructor setup copies arguments to locals `0..argc-1`, marks exactly
those bits initialized, and leaves all other locals/cells canonical zero. A
future wider JVM state cannot reuse this schema number.

Selected-code validation must cover all instructions, including unreachable
bytes: complete widths, legal opcode profile, local indices, signed branch math,
and branch targets at instruction starts. A CFG verifier should enforce int
operand heights and initialization at reachable joins (join initialization is
the predecessor intersection), with runtime checks retained as defense. Pauses
occur only between complete instructions. Allow same PC/machine after a nonzero
step result; monotonic `totalSteps`/epoch makes the checkpoint distinct. Commit a
caller-independent `maxTotalSteps` (1024 is sufficient for all measured entries,
whose maximum is 806); reaching it is an explicit stock resource failure, never
a fabricated Java return/OOM. Caller quantum changes only checkpoint count and
epoch/digest, not Java result or terminal machine.

This is still a one-class, one-frame integer profile. Reusable indexing should
make later method/class work possible, but S1 acceptance must not claim that
calls, statics, initialization, heap, exceptions, the full 2231 profile, or
Minecraft have been partitioned/deployed.

### Catalogue completeness commitment

Before implementation the parent should freeze a canonical ordered leaf encoding
for all 82 rows. Each leaf must bind index, case ID, raw class hash, declared class,
root name/descriptor and exact int32 argument words; an ordered root/count binds
all leaves. The harness independently derives it from the authoritative manifest
and requires indices 0..81 exactly once. Outcome is compared with JVM oracle data,
not fed to production. A stage may share five immutable raw/code pages, but still
must create and execute 82 distinct committed roots; deduplicating 39 method bodies
must not drop argument vectors. Filtering only supported-looking classes on the
host, substituting wrappers named `run`, or counting only unique roots is failure.

## 6. Finite signed deployment/resume ladder and separate gas accounting

Recommended parent freeze ladder, all on chainID1337/current all-dev rules with
Osaka, 30M block gas, signed EOA transactions, ordinary CREATE, no injected
code/state and no listeners:

| Gate | Required positive evidence | Exact finite workload |
|---|---|---|
| S1-O | Regenerate raw classes and catalogue; JVM8/JVM21/current EVM oracle agreement | 82 rows, 5 classes, 39 roots; already measured here |
| S1-D | Deploy pinned generic modules, all five exact raw pages and all EVM-derived index/code pages; verify actual bytes/code hashes and root/count commitment | finite artifact/page set chosen by parent; all 5 raw hashes and all 82 leaves required |
| S1-R16 | Fresh coordinator per row, signed run to terminal with quantum16 | 82 coordinator CREATEs + 195 resumes = 277 case-specific successful tx, plus separately reported shared setup |
| S1-R7 | Repeat every unchanged row with quantum7 | 82 coordinator CREATEs + 354 resumes = 436 case-specific successful tx, plus shared setup |
| S1-P | Per-instruction pause/argument/local/branch boundaries on nine existing rows: identity-min, add-overflow-positive, bipush-negative, sipush-add, generic-locals-wrap, binary-lt-true, sum-1, fibonacci-1, select-zero | quantum1, 72 resumes total; plus `sum-10` quantum8 (11) and `fibonacci-2` quantum12 (3) to require legitimate same-PC checkpoints |
| S1-X | Replay the exact signed S1-R16 transactions twice through `core.ApplyMessage` with identical explicit contexts | same calldata/nonces; gas, code hashes, events, checkpoints and final state root equal; signed backend VM state/gas equal without pretending wall-time block hashes equal |
| S1-N | Independent malformed/state/gas matrix below | 46 isolated failures; use nonzero-argument progress where specified |

For S1-R7/R16, every terminal result and machine must match across quantum, while
epoch/checkpoint batching is expected to differ. Exact executed counts must sum
to the measured instruction count, but the host count is only an assertion. No
host result, PC, branch decision or stop decision is accepted by production.

Do **not** reuse or edit the manifest's 2M/4M/20M `gas_limit` fields. Those remain
legacy one-call EVM-oracle budgets (12/59/11 entries respectively). Add a separate
stock report with at least: artifact/page/index/coordinator CREATE gas, parse/index
gas, each resume gas, positive aggregate gas, failed gas, successful/failed tx
counts and amortized-vs-per-case totals. Recommended provisional hard ceilings,
subject to parent measurement before freeze:

- each generic artifact runtime <=12KiB and initcode <=24KiB; raw/generated page
  runtime <=4097 bytes unless the parent documents a smaller bounded page family;
- each artifact/page/index/coordinator CREATE or parse-finalization tx <=8M gas;
- each resume <=2M gas and every transaction below Osaka `2^24` MaxTxGas;
- shared setup <= `8M * actualSetupTxCount` and each case <=
  `8M + 2M*ceil(actualSteps/quantum)`. Thus the explicit loose ceilings are 110M
  for `sum(100)` at quantum16, 1.046B for all S1-R16 case-specific transactions,
  and 1.364B for all S1-R7 case-specific transactions. Report actual gas, which
  should be materially lower; exceeding a per-tx ceiling triggers refactoring or
  parent re-freeze, not a manifest-budget change.

Negative gas is separate and never hidden in positive aggregate. Failed signed
tx still consume EOA gas/nonce even when coordinator/code-page state and logs
roll back.

## 7. Additional bounded trusted positive oracle probes

A candidate **16-invocation** TEST-only probe class was compiled locally with
`javac --release 8 -g:none` and run byte-for-byte on both JVMs. It is deliberately
ignored/not frozen: source
`build/java-diff-stock-s1-oracles/S1OracleProbes.java` SHA-256
`f88376791e213a9acb362ea9aaab5140433593ef84122f2a8dd4c9b3fa6de831`;
471-byte class SHA-256
`15fba012daf62d693ace9a639a2810e48c5c8943f8f3794eafcac77d94a49a54`;
report `probes.json` SHA-256
`0d51f3eb235862a9c7f6db93e8efa08a3e8dc2d989d8b6476d0a1d6d774cbd3a`.
Its `sixLocals` method independently compiles to max_locals6. Parent may adopt or
replace these only when freezing fixtures.

| Family | Exact args -> Java8 / Java21 outcomes |
|---|---|
| signed branch | `(MIN,MAX)->-1/-1`; `(MAX,MIN)->1/1`; `(-1,-1)->0/0` |
| counted loop/int32 | `(0,0)->0/0`; `(0,1)->1/1`; `(0,8)->-1635069824/-1635069824`; `(MAX,3)->2147454850/2147454850` |
| initialized branch join | `(0,MIN,MAX)->-2147483647/-2147483647`; `(-7,MIN,MAX)->MIN/MIN`; `(1,7,MAX)->MIN/MIN` |
| local-six | `(10,20,30,40)->100/100`; `(MAX,1,-2,3)->-2147483647/-2147483647` |
| int32 add | `(MAX,1)->MIN/MIN`; `(MIN,-1)->MAX/MAX`; `(MAX,MAX)->-2/-2`; `(-200,75)->-125/-125` |

If adopted, run these unchanged raw bytes signed at quantum1 and quantum16 and
compare JVM8/JVM21/stock results. Same-PC behavior is already more strongly tied
to unchanged production-target inputs by `sum` quantum8 and `fibonacci` quantum12.
The 16 are a separate proposed-probe count, not part of the 82.

## 8. Independent negative catalogue (46 isolated failures)

The parent should assign exact selectors/codes only when freezing the S1 ABI. The
following IDs freeze test intent, not error numbers. Each mutation isolates one
defect and asserts offending branch PC where applicable.

### Branch/predecode B01..B14

| ID | Mutation / required failure |
|---|---|
| B01 | conditional/goto opcode at Code end: both s16 bytes absent -> truncated instruction |
| B02 | only the high s16 byte present -> truncated instruction |
| B03 | branch at a nonzero PC with raw offset `0x8000` (-32768) -> target below zero, no Solidity panic |
| B04 | branch at PC0 with raw `0xffff` (-1) -> target below zero |
| B05 | valid `goto` raw `0x0000` -> same-PC instructions consume the committed 1024 cap, then hard resource failure, never a Java result |
| B06 | raw `0x0001` -> target the branch's first operand byte/non-start |
| B07 | raw `0x7fff` (+32767) -> target above Code |
| B08 | independently construct target exactly -1 from a later PC -> reject before unsigned cast |
| B09 | target exactly `code_length` -> out of range |
| B10 | target `code_length+1` -> out of range |
| B11 | target byte 1/2 of a `sipush` -> non-start |
| B12 | target operand byte of `iinc` or another branch -> non-start |
| B13 | malformed target in structurally unreachable code -> predecode rejection |
| B14 | unsupported opcode in structurally unreachable code -> predecode rejection, not ignored after an early return |

These cover raw s16 boundaries `-32768,-1,0,+1,+32767`. Target arithmetic is
`branchOpcodePC + signExtend16(raw)` in a signed/check-before-cast domain, never
`nextPC + offset`. Positive controls are the exact real edges `13-11=2` and
`19-15=4`, plus forward targets at the last legal instruction start.

### Operand/local/control-flow O01..O12

| ID | Mutation / required failure |
|---|---|
| O01 | unary conditional with empty operand stack -> underflow |
| O02 | binary conditional with zero operands -> underflow |
| O03 | binary conditional with one operand -> underflow |
| O04 | either branch path pushes beyond declared max_stack -> capacity error |
| O05 | generic local index `max_locals` (with `max_locals-1` positive control) -> range error |
| O06 | compact `iload_n`/`istore_n` at or above max_locals -> range error |
| O07 | nonzero-arg root loads the first extra, uninitialized local -> initialization error |
| O08 | local initialized on only one predecessor then loaded after join -> verifier initialization error |
| O09 | reachable join has different stack heights -> verifier shape error |
| O10 | fall out of Code -> fallthrough error |
| O11 | `ireturn` with zero cells -> return-shape/underflow error |
| O12 | `ireturn` with two cells -> return-shape error |

Positive controls compare MIN/MAX/-1/0/1 as signed int32 (never tagged uint32
ordering), initialize a join local on both predecessors, and pause immediately
before/after branches and 2/3-byte instructions. Pauses never commit a partial
immediate or operand pop; taken and untaken conditionals consume operands.

### Commitment/epoch/dirty/OOG C01..C20

| ID | Mutation / required failure |
|---|---|
| C01 | wrong raw page/payload hash before execution |
| C02 | wrong EVM-produced code-page hash |
| C03 | wrong executor/parser module hash |
| C04 | wrong declared-class component in root commitment |
| C05 | missing/wrong/ambiguous method name |
| C06 | wrong descriptor or descriptor/argc mismatch |
| C07 | one nonzero int32 argument bit differs from committed args |
| C08 | wrong schema or catalogue count/root |
| C09 | stale epoch before first resume of a nonzero-arg root |
| C10 | stale epoch after nonzero-arg progress |
| C11 | stale epoch after a legitimate same-PC checkpoint |
| C12 | dirty cap too small on first argument-bearing checkpoint |
| C13 | dirty cap too small after nonzero-arg progress |
| C14 | dirty cap too small on terminal return |
| C15 | actual signed-tx OOG during parse/index CREATE -> no partial page/index |
| C16 | actual module OOG after nonzero-arg progress -> empty nested failure remains OOG identity |
| C17 | actual tx OOG during commit after nonzero-arg progress -> prior checkpoint/storage/logs retained |
| C18 | explicit pre-call/post-call reserve failure -> structured control error distinct from C16/C17 |
| C19 | resume after terminal -> terminal control error, no new run |
| C20 | committed 1024-step cap reached -> resource control error, not pause/return/OOM |

For C09..C18, assert failed retry does not alter argument locals, PC, epoch,
totalSteps, digest, code-page/coordinator storage, or checkpoint logs; retry with
adequate epoch/dirty/gas reaches the same JVM result. Separately assert ordinary
sender nonce and gas effects of failed signed transactions, which do not roll
back. Empty nested OOG data must not be relabelled as a structured Java outcome.

Mutation helpers may parse trusted test bytes in the verifier only. Production
must discover offsets/targets from raw bytes itself. Each case asserts exact
selector/code/PC or exact empty OOG identity after the parent freezes the ABI.

## 9. Partition risks and parent freeze recommendations

1. **Code-page provenance is the critical new trust edge.** Host-built metadata
   would violate the execution boundary. Require EVM construction, immutable
   deployed bytes, schema/hash binding and independent recomputation in tests.
2. **Parser reuse versus completeness.** Indexing only the requested happy path
   can miss unreachable unsupported code or malformed branches. Predecode all
   selected Code bytes and bind the starts/CFG data. Define how unused methods and
   nested attributes are structurally scanned without claiming full verification.
3. **State growth.** Fixed stack8/local6 is acceptable only for this S1 profile.
   Full frames, heap, class state and exceptions need paged persistent state; do
   not extrapolate S1 ABI copying to the 2231-profile migration.
4. **Module calls and gas.** Bound STATICCALL gas while reserving commit gas;
   prevent reparsing CP/class data on every instruction. Measure cold/warm page
   access, code deposit, argument initialization and same-PC loops separately.
5. **Atomicity/replay.** Pin code hashes and root input; no upgrades or
   caller-supplied machine. Validate module output canonically, allow PC equality,
   require `1<=executed<=quantum`, and update one epoch per successful resume.
6. **Step-cap semantics.** 1024 covers this measured corpus but is not a Java
   semantic limit or arbitrary-program claim. Resource exhaustion remains stock
   control failure. Static counts are assertions only.
7. **Capability accounting.** S1 positive fixture count is **82**, separate from
   accepted S0's **8** and the old full-runtime **2231**. Do not advertise 90,
   2313, or the additional 16 candidate invocations as one conformance total.

Recommended freeze gate: parent reviews this inventory, chooses a generic EVM-built
index/code-page format and exact error/state ABI, prototypes worst cases
`Comparisons` (largest class/CP), `genericLocals` (locals6), `sum(100)` (806 steps,
same-PC quantum) and `fibonacci(30)` (368 steps), then freezes measured gas and
worker write sets. A monolithic full-profile port, Minecraft execution, host Java
evaluation, class-specific generated runtime, or any EVM/core/limit change is out
of S1 scope.
