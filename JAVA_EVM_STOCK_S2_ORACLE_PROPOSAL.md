# Stock-EVM S2 workload/oracle preflight proposal

**Status: measured proposal/oracle evidence only; nothing here freezes S2.** Base is
accepted Stock S1 commit `1b5150dd74eb9cb292c81b10fd562cd4bb3b0539`
(`1b5150d`) and `JAVA_EVM_STOCK_S1_PLAN.md`. Program authority remains
`JAVA_EVM_PROGRAM.md`. This document recommends the smallest coherent next stock
migration; a parent plan must still freeze architecture, ABI, limits, write sets,
and measured thresholds.

Only this document and ignored `build/java-diff-stock-s2-oracles/` were produced.
No production/runtime/test/fixture/Make/tool/accepted-plan file was changed. No
Minecraft or downloaded Java was run, no EULA accepted, no listener opened, no
agent spawned, and no EVM/core/consensus/gas/limit/global setting was changed.
There was no `SetCode`/`SetState`, push, or peer-worktree write. This is not a
standard-deployment result, M5d-a migration, full JVM, Throwable/handler, library,
or Minecraft-startup claim. S0's 8, S1's 82, and the monolith's 2,231 counts stay
separate.

## 1. Recommendation

Choose **integer completion alone** as the next candidate stock slice: migrate all
119 unchanged `m2b` rows, cumulatively all 201 M1/M2/M2b rows. Do **not** combine
M3a static calls into that first freeze.

This is the smallest semantic increment because S1 already parses/caches integer
constants and executes `imul` and `ineg`; M2b needs only `idiv`, `irem`, `ishl`,
`ishr`, `iushr`, `iand`, `ior`, `ixor`, `i2b`, `i2c`, and `i2s`, plus a persistent
terminal `ArithmeticException` outcome. It keeps one active Java frame, the
existing stack8/local8 envelope, current metadata shape, and the existing
max-step/dirty ceiling scale.

Adding the 67 M3a rows at once is coherent semantically but not small
architecturally. It requires private and overloaded helper metadata, `(I...)V`,
six-argument descriptors, exact Methodref resolution, persistent push/pop frames,
`invokePC`, frame-local stacks/locals, a 128-frame StackOverflow terminal path,
and a module/state boundary that does not ABI-copy 128 frames each resume. Those
are independently reviewable architecture changes. The M3a inventory below is
therefore the exact next dependency, not a proposed shortcut or excluded row set.

## 2. Reproducible bounded evidence

The source of truth is `jvmevm/testdata/differential/cases.json`, schema 1, SHA-256
`a36da915ca07170b6a0ae54f05693c95d2e4c74415268f47b36787dd02dac440`.
Actual stage counts are M1 12 + M2 70 = 82 (accepted S1), then M2b **119** =>
**201**, then M3a **67** => **268**. The cumulative set has 94 distinct public
root signatures in 14 classes; the two increments add 9 classes and 55 roots.
No row, source list, argument, expected kind, timeout, or old gas limit was edited.

Commands actually run from `1b5150d`:

```sh
/usr/lib/jvm/jdk-21.0.9/bin/javac --release 8 -d \
  build/java-diff-stock-s2-oracles/classes21 \
  jvmevm/testdata/differential/OracleMain.java \
  jvmevm/testdata/differential/{M1Baseline,Constants,LocalsAndArithmetic,Comparisons,Loops,IntegerArithmetic,IntegerBitwise,IntegerConstants,IntegerConversions,IntegerShifts,WideIntegerConstant,M3aFrames,M3aRecursion,M3aStaticCalls}.java
go build -o build/java-diff-stock-s2-oracles/jvmevm ./cmd/jvmevm
PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py --stage m3a --tier full \
  --evm-bin build/java-diff-stock-s2-oracles/jvmevm \
  --artifacts build/java-diff-stock-s2-oracles/legacy-evm
PYTHONDONTWRITEBYTECODE=1 timeout 600s \
  python3 build/java-diff-stock-s2-oracles/inventory.py
```

`inventory.py` invokes the **same javac-21-generated raw class bytes** separately
on OpenJDK8 and Java21 as:

```text
java -Xmx64m -Xss512k -XX:-OmitStackTraceInFastThrow -Xverify:all \
  -cp classes21 OracleMain CLASS METHOD ARGS...
```

Each subprocess has the unchanged manifest timeout (all are 10s; additionally
bounded by 20s in the driver). All 536 JVM invocations exited zero; no timeout,
host OOM, or unexpected host SOE occurred. The only recursive-until-SOE execution
was the already-trusted `m3a-recursive-stack-overflow`; no new infinite loop or
host-OOM case was introduced. OpenJDK8 is `1.8.0_504-b01`/VM 25.504-b01;
Java21 is `21.0.9+7-LTS-338`. The two compilers produce different debug-bearing
class bytes, so the Java8 compiler output is diagnostic only: every reported hash
and both JVM outcome runs use the exact Java21 `--release 8` bytes used by the
current differential runner.

The TEST-only class decoder/tracer has a 1,000,000-dispatch guard and a modelled
stock frame cap of 128. It parses unchanged raw bytes, resolves same-class calls,
and checks every final value/exception against both JVMs and the monolith. Its
counts are reference assertions only; none may enter parser/module/coordinator
calldata or decide production stopping, branching, calls, or results. For a
terminal Java fault, `dispatches` includes the faulting `idiv`/`irem` or failed
129th-frame `invokestatic`; `successful_before_terminal=dispatches-1` is retained
in JSONL.

Evidence identities:

| File | SHA-256 |
|---|---|
| `build/.../inventory.py` | `a23bce055f996224ebe052cd6a2f90b44f3f9b2e6284f0998f9f24f5c94cb806` |
| `build/.../inventory.json` | `27aeff525832ba7f156da4e54f8b1205af2260bdc48faf3c205fbc7ca003bdca` |
| ordered `build/.../catalogue.jsonl` | `77d8000e5533803a7113f51dbf9db9eb1fa0cc2a566fc4e6852fa18581486d55` |
| bounded Java8 records | `6c041a003d370b3c8a21be6129703630a952a9fd736b6efa0a651978e1d2ab30` |
| bounded Java21 records | `be024e527ed7dc63fd0f62c528d6defffe7c5b34981fcc168ead78d982f38dd9` |
| 268-row monolith report | `0304174103fe148c89f1c786be6591f5b28ebf87b12f64a673efa5dfad274306` |

The monolith run passed **268/268** with runtime 154,839 bytes, SHA-256
`dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
Its current local-call gas is 400,109..7,338,674, sum 169,759,879. For M2b alone
it is 414,025..1,433,315, sum 53,083,954; for M3a alone
651,696..7,338,674, sum 71,438,523. This is `runtime.Execute` oracle gas, not
ordinary deployment, signed transaction, or proposed stock gas.

## 3. Exact source/classfile inventory

All nine increment classes are major 52/minor 0, ordinary public classes directly
extending `java/lang/Object`, with zero fields/interfaces/`<clinit>`. `methods`
includes the ordinary javac constructor. `CP` is the classfile `constant_pool_count`
field. Page bytes would be raw bytes + one `STOP` prefix.

| Stage | Source | source SHA-256 | raw class SHA-256 | raw/page B | CP | methods |
|---|---|---|---|---:|---:|---:|
| M2b | `IntegerArithmetic.java` | `4f2322ce65e9dd5beddf852fddff4c2507660b18352fc0e0e65eecc7284156d7` | `69c6a01e0045efc1caa3e2a9c598a4dd75530fe74f5b4e2c378689feb1c27d43` | 431/432 | 19 | 5 |
| M2b | `IntegerBitwise.java` | `420d8a9cf36936335fda4649ad4a022f1aec5e87cb4d14707541fc0a65e36b93` | `8cece8e7b75cf657b146eade5cd73d8616826f73ac14427e8e1f0c51fa9dc018` | 353/354 | 17 | 4 |
| M2b | `IntegerConstants.java` | `9b05406fc043593ab44aa0f7bd7fe866ab2f9fd61d31be5ca06854bb4f8e7ef6` | `189ac9b47a7f09a080a64be3e662aba0045440ca78a6d65674256e0cb0aaf0fd` | 633/634 | 29 | 8 |
| M2b | `IntegerConversions.java` | `4c6efb52f1492885ccb6a438bd772c270844cf46fdaeded70c9e052e9504db90` | `ba383508690bf9aab643b26af435077cc002d8b4ccd61cd6b52b734a82e7fd08` | 368/369 | 17 | 4 |
| M2b | `IntegerShifts.java` | `24836881a83da8c896fbb50811228ddff33d9b23af367d76fc9696c9b6359b16` | `1cd887856a8e6922e14c5246c3c563dd5914d499511b0be0fc9b35178d9df2bc` | 380/381 | 17 | 4 |
| M2b | `WideIntegerConstant.java` | `a6c1d3ccb405c21a3c351fefb45df43f5db04fd91c4d255dec11c473fef1ca37` | `fbf7d7498a50fa0ed8adba88ef74f702cdd4bc82fdab94ba75c8e54a77eb9137` | 3469/3470 | 277 | 3 |
| M3a | `M3aFrames.java` | `f24ad6306f3497440a504e152d990f4ed685f26e862fe3424ee2881524fe4a44` | `c1807e5289b9981e4804e1bc37575fd44dff1feebb914a235dbd5a32d173d5ad` | 1601/1602 | 55 | 20 |
| M3a | `M3aRecursion.java` | `ac481d50accb972d3e9496a701b5cd6807004e5192570d18a3c0f25fe59ba1ec` | `3bfec29278c225bb553daf4bd242f61fafe6e7ea1c3a4e31c1fd699c912ac842` | 1390/1391 | 47 | 16 |
| M3a | `M3aStaticCalls.java` | `886729985ed4366ea8e21376191eea4e395a6d87b2e43a55f3fc27e55e3c7fef` | `316f4878ac2fc59113ee81d20e76304f5eaa32575b3931088b1b1da1adb21156` | 2169/2170 | 73 | 31 |

M2b has 6 classes, 21 selected roots, root stack 1..2, locals 0..2, Code 3..5.
Root signatures are `()I`:7, `(I)I`:5, `(II)I`:9; the 119 row/argument
distribution is 0:7, 1:33, 2:79.
`WideIntegerConstant.populateIntegerPool()I` is intentionally unentered Code 793
with 522 static instructions; `loadWide()I` is Code 4 and executes genuine
`ldc_w` at CP index >255. This validates S1's policy of retaining an ineligible
unused method record instead of rejecting the whole class. Largest M2b class is
3,469 bytes/CP277, within raw4096/CP512; all selected roots fit Code256,
stack8/local8, methods32, and literal256 caps.

M3a has 3 classes, 34 roots, 64 entered static int/void methods, 51 static call
sites (30 distinct Methodref CP entries), root stack 1..6, locals 0..6, Code 4..25.
Its 34 root signatures are `()I`:1, `(I)I`:17, `(II)I`:10, `(III)I`:5,
`(IIIIII)I`:1; the 67 row/argument distribution is 0:1, 1:40, 2:15, 3:9,
6:2. Cumulatively 268 row argument counts are 0:16, 1:115, 2:119, 3:13,
4:3, 6:2. The largest class is 2,169 bytes/CP73; the tight class cap is
`M3aStaticCalls` with 31 declared methods under S1's <=32 cap.

### Exact entered opcode profiles and dynamic counts

M2b's 119 runs dispatch 429 instructions:
`i2b:8 i2c:8 i2s:8 iadd:2 iand:5 idiv:12 iload_0:112 iload_1:79
imul:10 ineg:7 ior:5 irem:12 ireturn:117 ishl:10 ishr:10 iushr:10
ixor:5 ldc:8 ldc_w:1`. It has no calls and every run has frame depth 1.
The two zero divisors terminate at dispatch 3; all values terminate in 2..4.

M3a's 67 runs dispatch 4,060 instructions and 512 dynamic calls:
`bipush:46 iadd:324 iconst_0:5 iconst_1:574 iconst_2:127 iconst_3:18
iconst_4:12 iconst_5:11 idiv:4 if_icmpgt:240 ifgt:14 ifne:67 iload:10
iload_0:1021 iload_1:97 iload_2:35 iload_3:18 imul:84 invokestatic:512
irem:8 ireturn:431 istore:2 istore_0:4 istore_1:12 istore_2:16
istore_3:12 isub:330 ldc:3 pop:4 return:10 sipush:9`.
There are 62 values, four propagated ArithmeticExceptions, and one
StackOverflowError. Maximum successful depth is 33 (`mutualParity(31)`); the
trusted SOE reaches the exact model cap 128 and terminal dispatch 510. Largest
finite trace is `recursiveFibonacci(10)`, 1,592 dispatches, depth 11, 177 calls.
Across cumulative 268 rows there are 6,702 model dispatches (S1 2,213 + M2b 429
+ M3a 4,060).

### Exact M2b/M3a static method inventory

The table includes every increment static method accepted by the integer/call
profile, including the deliberately unentered wide-pool method. Call PCs are
method-relative opcode PCs and targets are exact name+descriptor.

| Class.method descriptor | access | max stack / locals | Code B / static instructions | static `invokestatic` sites | corpus role |
|---|---:|---:|---:|---|---|
| `IntegerArithmetic.multiply(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerArithmetic.divide(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerArithmetic.remainder(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerArithmetic.negate(I)I` | public static | 1 / 1 | 3 / 3 | — | root + entered |
| `IntegerBitwise.and(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerBitwise.or(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerBitwise.xor(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerConstants.positiveLdc()I` | public static | 1 / 0 | 3 / 2 | — | root + entered |
| `IntegerConstants.negativeLdc()I` | public static | 1 / 0 | 3 / 2 | — | root + entered |
| `IntegerConstants.maxLdc()I` | public static | 1 / 0 | 3 / 2 | — | root + entered |
| `IntegerConstants.minLdc()I` | public static | 1 / 0 | 3 / 2 | — | root + entered |
| `IntegerConstants.highBitPattern()I` | public static | 1 / 0 | 3 / 2 | — | root + entered |
| `IntegerConstants.alternatingBits()I` | public static | 1 / 0 | 3 / 2 | — | root + entered |
| `IntegerConstants.addLdc(I)I` | public static | 2 / 1 | 5 / 4 | — | root + entered |
| `IntegerConversions.toByte(I)I` | public static | 1 / 1 | 3 / 3 | — | root + entered |
| `IntegerConversions.toChar(I)I` | public static | 1 / 1 | 3 / 3 | — | root + entered |
| `IntegerConversions.toShort(I)I` | public static | 1 / 1 | 3 / 3 | — | root + entered |
| `IntegerShifts.shiftLeft(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerShifts.shiftRight(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `IntegerShifts.shiftRightUnsigned(II)I` | public static | 2 / 2 | 4 / 4 | — | root + entered |
| `M3aFrames.alterLocals(II)I` | private static | 3 / 4 | 21 / 20 | — | entered helper |
| `M3aFrames.rewriteParameter(I)I` | private static | 2 / 1 | 8 / 8 | — | entered helper |
| `M3aFrames.noOp()V` | private static | 0 / 0 | 1 / 1 | — | entered helper |
| `M3aFrames.consume(I)V` | private static | 2 / 2 | 9 / 9 | — | entered helper |
| `M3aFrames.nestedVoid(I)V` | private static | 1 / 1 | 8 / 4 | 1→consume(I)V, 4→noOp()V | entered helper |
| `M3aFrames.ignoredResult(I)I` | private static | 2 / 1 | 8 / 6 | — | entered helper |
| `M3aFrames.ignoredNested(I)I` | private static | 2 / 1 | 7 / 5 | 3→ignoredResult(I)I | entered helper |
| `M3aFrames.combine(II)I` | private static | 2 / 3 | 9 / 8 | — | entered helper |
| `M3aFrames.divideAndDiscard(II)V` | private static | 2 / 3 | 5 / 5 | — | entered helper |
| `M3aFrames.callerLocalIsolation(II)I` | public static | 3 / 5 | 25 / 18 | 6→alterLocals(II)I | root + entered |
| `M3aFrames.parameterIsolation(I)I` | public static | 2 / 2 | 12 / 9 | 1→rewriteParameter(I)I | root + entered |
| `M3aFrames.voidNoArgs(I)I` | public static | 2 / 1 | 7 / 5 | 0→noOp()V | root + entered |
| `M3aFrames.voidOne(I)I` | public static | 2 / 1 | 8 / 6 | 1→consume(I)V | root + entered |
| `M3aFrames.nestedVoidCall(I)I` | public static | 2 / 1 | 8 / 6 | 1→nestedVoid(I)V | root + entered |
| `M3aFrames.discardInt(I)I` | public static | 2 / 1 | 10 / 7 | 1→ignoredResult(I)I | root + entered |
| `M3aFrames.discardNested(I)I` | public static | 2 / 1 | 10 / 7 | 1→ignoredNested(I)I | root + entered |
| `M3aFrames.prefixAndCall(III)I` | public static | 3 / 3 | 8 / 6 | 3→combine(II)I | root + entered |
| `M3aFrames.prefixAcrossTwoCalls(II)I` | public static | 3 / 2 | 12 / 8 | 2→combine(II)I, 7→combine(II)I | root + entered |
| `M3aFrames.voidDivide(II)I` | public static | 2 / 2 | 9 / 7 | 2→divideAndDiscard(II)V | root + entered |
| `M3aRecursion.sumTo(I)I` | private static | 3 / 1 | 15 / 11 | 10→sumTo(I)I | entered helper |
| `M3aRecursion.factorial(I)I` | private static | 3 / 1 | 16 / 12 | 11→factorial(I)I | entered helper |
| `M3aRecursion.fibonacci(I)I` | private static | 3 / 1 | 21 / 15 | 10→fibonacci(I)I, 16→fibonacci(I)I | entered helper |
| `M3aRecursion.even(I)I` | private static | 2 / 1 | 13 / 9 | 9→odd(I)I | entered helper |
| `M3aRecursion.odd(I)I` | private static | 2 / 1 | 13 / 9 | 9→even(I)I | entered helper |
| `M3aRecursion.gcd(II)I` | private static | 3 / 2 | 14 / 10 | 10→gcd(II)I | entered helper |
| `M3aRecursion.carryThroughFrames(II)I` | private static | 3 / 4 | 22 / 18 | 14→carryThroughFrames(II)I | entered helper |
| `M3aRecursion.recurseForever(I)I` | private static | 2 / 1 | 7 / 5 | 3→recurseForever(I)I | entered helper |
| `M3aRecursion.recursiveSum(I)I` | public static | 1 / 1 | 5 / 3 | 1→sumTo(I)I | root + entered |
| `M3aRecursion.recursiveFactorial(I)I` | public static | 1 / 1 | 5 / 3 | 1→factorial(I)I | root + entered |
| `M3aRecursion.recursiveFibonacci(I)I` | public static | 1 / 1 | 5 / 3 | 1→fibonacci(I)I | root + entered |
| `M3aRecursion.mutualParity(I)I` | public static | 1 / 1 | 5 / 3 | 1→even(I)I | root + entered |
| `M3aRecursion.recursiveGcd(II)I` | public static | 2 / 2 | 6 / 4 | 2→gcd(II)I | root + entered |
| `M3aRecursion.recursiveFrameIsolation(II)I` | public static | 2 / 2 | 6 / 4 | 2→carryThroughFrames(II)I | root + entered |
| `M3aRecursion.unboundedRecursion(I)I` | public static | 1 / 1 | 5 / 3 | 1→recurseForever(I)I | root + entered |
| `M3aStaticCalls.assemble3(III)I` | private static | 3 / 3 | 13 / 10 | — | entered helper |
| `M3aStaticCalls.zeroValue()I` | private static | 1 / 0 | 3 / 2 | — | entered helper |
| `M3aStaticCalls.privateTransform(I)I` | private static | 2 / 1 | 7 / 6 | — | entered helper |
| `M3aStaticCalls.overloaded(I)I` | private static | 2 / 1 | 5 / 4 | — | entered helper |
| `M3aStaticCalls.overloaded(II)I` | private static | 3 / 2 | 9 / 8 | — | entered helper |
| `M3aStaticCalls.overloaded(III)I` | private static | 3 / 3 | 12 / 10 | — | entered helper |
| `M3aStaticCalls.leaf(I)I` | private static | 2 / 1 | 6 / 6 | — | entered helper |
| `M3aStaticCalls.middle(I)I` | private static | 2 / 1 | 9 / 7 | 3→leaf(I)I | entered helper |
| `M3aStaticCalls.outer(I)I` | private static | 2 / 1 | 9 / 7 | 3→middle(I)I | entered helper |
| `M3aStaticCalls.mix6(IIIIII)I` | private static | 3 / 6 | 25 / 22 | — | entered helper |
| `M3aStaticCalls.divide(II)I` | private static | 2 / 2 | 4 / 4 | — | entered helper |
| `M3aStaticCalls.remainder(II)I` | private static | 2 / 2 | 4 / 4 | — | entered helper |
| `M3aStaticCalls.divideThrough(II)I` | private static | 2 / 2 | 6 / 4 | 2→divide(II)I | entered helper |
| `M3aStaticCalls.multiArgumentOrder(III)I` | public static | 3 / 3 | 7 / 5 | 3→assemble3(III)I | root + entered |
| `M3aStaticCalls.multiArgumentPermutation(III)I` | public static | 3 / 3 | 7 / 5 | 3→assemble3(III)I | root + entered |
| `M3aStaticCalls.zeroArgumentCall(I)I` | public static | 2 / 1 | 6 / 4 | 1→zeroValue()I | root + entered |
| `M3aStaticCalls.zeroOnly()I` | public static | 1 / 0 | 4 / 2 | 0→zeroValue()I | root + entered |
| `M3aStaticCalls.privateHelperCall(I)I` | public static | 1 / 1 | 5 / 3 | 1→privateTransform(I)I | root + entered |
| `M3aStaticCalls.overloadOne(I)I` | public static | 1 / 1 | 5 / 3 | 1→overloaded(I)I | root + entered |
| `M3aStaticCalls.overloadTwo(II)I` | public static | 2 / 2 | 6 / 4 | 2→overloaded(II)I | root + entered |
| `M3aStaticCalls.overloadThree(III)I` | public static | 3 / 3 | 7 / 5 | 3→overloaded(III)I | root + entered |
| `M3aStaticCalls.nestedCall(I)I` | public static | 1 / 1 | 5 / 3 | 1→middle(I)I | root + entered |
| `M3aStaticCalls.deepNestedCall(I)I` | public static | 1 / 1 | 5 / 3 | 1→outer(I)I | root + entered |
| `M3aStaticCalls.callerPrefix(III)I` | public static | 3 / 3 | 15 / 10 | 7→overloaded(II)I | root + entered |
| `M3aStaticCalls.twoCallPrefix(II)I` | public static | 2 / 2 | 10 / 6 | 1→privateTransform(I)I, 5→privateTransform(I)I | root + entered |
| `M3aStaticCalls.sixArguments(IIIIII)I` | public static | 6 / 6 | 12 / 8 | 8→mix6(IIIIII)I | root + entered |
| `M3aStaticCalls.returnedArithmetic(I)I` | public static | 2 / 1 | 10 / 7 | 1→privateTransform(I)I | root + entered |
| `M3aStaticCalls.calleeDivide(II)I` | public static | 2 / 2 | 6 / 4 | 2→divide(II)I | root + entered |
| `M3aStaticCalls.calleeRemainder(II)I` | public static | 2 / 2 | 6 / 4 | 2→remainder(II)I | root + entered |
| `M3aStaticCalls.callThroughDivide(II)I` | public static | 2 / 2 | 6 / 4 | 2→divideThrough(II)I | root + entered |
| `WideIntegerConstant.populateIntegerPool()I` | public static | 1 / 1 | 793 / 522 | — | unentered |
| `WideIntegerConstant.loadWide()I` | public static | 1 / 0 | 4 / 2 | — | root + entered |

## 4. Why M2b is the smallest coherent stock migration

S1 already supports `ldc`/`ldc_w` CONSTANT_Integer, `imul`, and `ineg`. Its parser,
metadata provenance, literal records, one-frame MachineV2, arguments up to four,
stack/local bounds, signed branches, replay commitments, and loop-safe checkpoint
protocol cover every structural M2b requirement. Current code rejects the ten
remaining opcodes generically, and it has no persisted Java-exception lifecycle.
Thus M2b is a real semantic migration, not a parser rewrite or class recognizer.

A parent freeze should use a **new schema/domain**, without mutating S1 history:

* EVM-derived immutable metadata remains class-generic and keeps all declared
  method records. Predecode and flow effects add exactly the ten missing opcodes.
  `idiv`/`irem` pop two ints and push one only on success; shifts mask distance
  with 31; `ishr` sign-fills; `iushr` zero-fills; narrowing returns tagged int.
* A MachineV3-like state adds terminal lifecycle `THREW` and `exceptionKind=1`
  (`java.lang.ArithmeticException`) plus exact `faultPC`. `RETURNED` and
  `STEP_LIMIT` remain distinct. A guest arithmetic fault should be a successful,
  signed terminal checkpoint, not an EVM revert whose state disappears. Unknown
  payloads, malformed classes, component failures, OOG, and control errors remain
  EVM failures and must never be decoded as Java outcomes.
* For the proposed one-frame S2 profile, frame cap is exactly **1**,
  `maxTotalSteps=1024`, per-resume step request 1..128, and dirty request 1..32.
  The module counts the terminal faulting instruction once. Reaching 1024 while
  runnable is finite `STEP_LIMIT`, never Java return/ArithmeticException/OOM.
  Returned/faulted state is canonical and cannot resume.
* Keep S1 stack8/local8 and root argc0..4. Every M2b root is argc<=2. Preserve
  exact int tags and all inactive/uninitialized-zero invariants. There is no
  host-provided expected value, Code offset, start map, literal, fault decision,
  instruction count, or terminal decision.
* All Java instructions above execute in ordinary deployed EVM modules from the
  unchanged raw pages. No class/hash/name/result switch, specialized generated
  executable, monolith fallback, host parser, or host Java execution exists on
  the production path.

This requires a parser/module/coordinator artifact revision and new commitments;
it must not overwrite S1 parser registry semantics or call a schema-2 state
schema 3. Whether layouts are source-shared is an implementation decision for the
parent; accepted S0/S1 bytecode, ABI, artefacts, tests, catalogue, and counts stay
unchanged.

## 5. Exact finite signed ladder and separate budgets

Candidate acceptance ladder (not frozen) uses chain ID 1337/current all-dev rules,
30M block gas, Osaka per-transaction cap `2^24`, funded TEST EOA, ordinary CREATE,
signed transactions/receipts and direct signed replay. It uses no listener,
code/storage injection, or old `gas_limit` as a stock allowance.

| Gate | Exact positive work | Step/frame/dirty budget |
|---|---|---|
| S2-O | Rebuild and bind all 11 cumulative classes; JVM8/JVM21/monolith agreement for all 201 ordered rows | host timeout10s, Xmx64m, Xss512k; TEST trace guard1,000,000 |
| S2-D | Deploy pinned generic parser/module, 11 exact `STOP||raw` pages, and register 11 EVM-derived metadata pages | proposed shared setup 24 successful tx; each CREATE/register <=8M; parser runtime<=16KiB, other executable runtime<=12KiB, initcode<=24KiB, metadata runtime<=8KiB and all stock EIP-170/3860 limits |
| S2-R64 | Fresh coordinator for every one of 201 rows, run terminal | maxTotalSteps1024, frame cap1, quantum64, dirty request32; exactly 201 CREATE +226 resume successes |
| S2-R128 | Fresh coordinator for every row, independent run | cap1024/frame1/quantum128/dirty32; exactly 201 CREATE +211 resumes |
| S2-F1 | All 119 M2b rows at quantum1, including both fault PCs | exactly 429 resumes; cap1024/frame1/dirty32 |
| S2-X | Replay exact R64 signed transaction bytes twice under identical explicit contexts | code/metadata/program/input roots, gas, receipts/checkpoints and final canonical state agree; wall-time headers are not claimed equal |
| S2-N | Isolated negative matrix below, each failed mutation followed by valid retry | request dirty=`actual-1` must roll back; dirty=`actual` and <=32 succeeds |

Every transaction remains <=8M proposed stage ceiling and every resume <=2M,
subject to actual prototype measurement before a freeze; never raise a ceiling or
an old row's gas to hide a failure. Report artifact/page/registration/coordinator/
each-resume gas, positive and failed totals, success/failure transaction counts,
and isolated versus shared/amortized setup. The manifest's original M2b budgets
remain exactly 118 rows at 6M and one at 20M; they are monolith invocation limits,
not stock deployment/resume limits. Failed signed transactions consume sender
gas/nonce while VM contract writes/logs roll back.

For later M3a evaluation, the equally finite cumulative reference is 268 rows,
6,702 dispatches, maxTotalSteps4096, frame cap128: quantum64 requires 268
coordinators +336 resumes; quantum128 requires 268+297. A prospective frame-aware
dirty request of 64 is only a measurement candidate, not a recommendation or cap
freeze. It must be replaced by actual per-push/per-pop/per-terminal slot counts;
no M3a implementation should start from an unmeasured whole-frame-array ABI.

## 6. Exact arithmetic and control negative intent

These are isolated TEST mutations of trusted local class bytes, not new guest
corpus or host metadata supplied to execution. A parent plan should assign/freeze
selectors and numeric codes while retaining S1's established class/method/
bytecode/control precedence.

| ID | Exact requirement |
|---|---|
| I01 | `MIN / -1` returns `MIN`; no Solidity panic. |
| I02 | `MIN % -1` returns zero; no Solidity panic. |
| I03/I04 | `idiv` and `irem` divisor zero at PC2 persist `THREW`, kind1, faultPC2, dispatch3; no `RETURNED`, revert, OOG, or host synthesis. |
| I05 | Positive/negative dividend and divisor combinations truncate division toward zero and give remainder the dividend sign. |
| I06 | `ishl/ishr/iushr` mask distances `-1,0,1,31,32,33,INT_MAX` with 31; distinguish sign-fill from zero-fill and preserve 32-bit wrap. |
| I07 | `iand/ior/ixor` operate on exact low32 bit patterns including MIN/MAX, all-ones and alternating bits. |
| I08 | `i2b` boundaries 127/128/255/256 sign-extend 8 bits; `i2s` 32767/32768/65535/65536 sign-extends 16; `i2c` zero-extends 16. |
| I09 | Truncated operands for `ldc_w`, `iinc`, and every new opcode with operands fail at exact opcode PC; no partial state/checkpoint. |
| I10 | `ldc/ldc_w` index zero/out of range/wrong CP tag and malformed CP structure retain exact parser/bytecode failure, never a value. Genuine selected CP>255 remains positive. |
| I11 | New unary/binary operations on empty/one-cell stack fail exact underflow PC; declared max-stack overflow and bad tags fail exact bytecode domain. |
| I12 | Local index=`max_locals`, uninitialized local, `max_locals<argc`, malformed descriptor/access, and args mismatch retain exact method/bytecode precedence. |
| I13 | Wrong return shape/kind, fallthrough and incoming non-start PC fail exactly; unreachable malformed/new-unsupported opcode is still rejected at registration. |
| I14 | Exact return on dispatch1024 wins over cap; still-runnable dispatch1024 becomes `STEP_LIMIT`; resume after RETURNED/THREW/STEP_LIMIT fails terminal control. |
| I15 | Stale epoch, wrong page/payload/metadata/parser/module/root hash, malformed module response, dirty=`actual-1`, reserve failure and nested OOG are distinct; failed retry preserves prior checkpoint. |

Expected results are never weakened: the 117 M2b values and two exact
ArithmeticExceptions all remain mandatory, as do all 82 S1 rows. An EVM OOG,
opaque revert, timeout, malformed output, wrong exception, or `STEP_LIMIT` is not
a passing Java outcome.

## 7. M3a call/frame preflight and exact gaps

### S1 metadata/profile gaps

1. S1 marks non-public methods ineligible and clears Code-derived fields; M3a
   requires same-class private static helpers. Root selection remains public,
   but entered helper access is independently validated.
2. S1 accepts only `(I{0..4})I`. M3a requires exact `(I{0..6})(I|V)` internally,
   roots through six ints, two six-arg rows, one zero-arg root, private `()V`,
   `(I)V`, `(II)V`, and exact int-vs-void return transfer.
3. S1 predecode rejects `invokestatic`, `pop`, and `return`. It caches no
   Methodref/Class/NameAndType relationships or call-site target. A new metadata
   schema must derive call records in EVM from raw CP: caller method+PC, symbolic
   owner, exact name+descriptor, resolved declared target, argc and return kind.
4. Existing MachineV2 is one frame and its module ABI copies that one machine.
   M3a needs independently persistent caller/callee stack, locals, initialization,
   method and PC, active depth, and return continuation. Copying all 128 frames
   through `STATICCALL` every resume is rejected; use measured coordinator-owned
   chunked frames with code-hash-pinned sibling `DELEGATECALL`, or another reviewed
   bounded state-page protocol. Module calls must not recurse in EVM.
5. Keep `invokePC` (the caller's invoke opcode PC) separately from nextPC before
   pushing. Arithmetic abrupt completion from a callee is attributed to that
   invokePC for eventual handler compatibility, although this slice has no
   handlers. Safepoints are only after a complete call push, return pop, or
   terminal outcome; no half-transferred arguments/frame.

### Required call/return behavior

Private helpers and overloads resolve by exact owner+name+descriptor, not root
name rules or declaration order. Arguments pop descriptor-right-to-left and land
in callee locals 0..argc-1 in declaration order; caller prefix operands, locals,
and remaining stack persist. Int return pushes exactly one tagged int; void
return pushes none; `pop` discards one category-1 int. Every frame owns its own
PC/SP/initialized mask/stack/locals. Same-class `CONSTANT_Methodref` only is
positive; no external/interface/virtual/special call promise.

At exactly 128 active Java frames (root included), another push produces persisted
terminal `java.lang.StackOverflowError`; it is not OpenJDK stack-cap equivalence.
The existing trusted recursion model reaches depth128 and dispatch510. A low-gas
run must remain OOG, never SOE. Callee divide/remainder zero propagates terminal
ArithmeticException through current frames; no catch lookup/unwind/Throwable API
is claimed. A future handler stage must use saved invokePC and cannot reinterpret
an already-advanced caller PC.

### Exact future call negatives

Retain the accepted M3a semantic error contract as the candidate separation:

| ID | Exact required failure/outcome |
|---|---|
| C01 | Invalid/truncated `invokestatic` CP index or malformed Methodref/Class/NameAndType/Utf8 chain: call error 1 at caller invokePC. |
| C02 | owner name not this ordinary class, or InterfaceMethodref: call error 2 at invokePC. |
| C03 | no unique exact target name+descriptor (including wrong overload): call error 3 at invokePC. |
| C04 | target non-static, forbidden native/abstract/synchronized/access, malformed/non-int descriptor, missing/multiple/unusable Code, or locals<argc: call error 4 at invokePC. Same-class private static is a positive control. |
| C05 | `ireturn` in V target or `return` in I target: call error 5 at the entered callee's exact return PC. |
| C06 | argument underflow at invokePC is bytecode underflow, not call error; six-arg order and preserved caller prefix are positive controls. |
| C07 | caller/callee stack or local capacity/tag/init corruption fails exact current frame/PC and rolls back the whole resume. |
| C08 | push from active depth128 persists SOE; depth128 itself is legal. Frame cap must be checked before allocation/argument mutation and before gas-derived failure can be relabelled. |
| C09 | callee `idiv/irem` zero persists ArithmeticException with callee faultPC plus caller invokePC provenance; it is not return, call error, generic revert, or handler support. |
| C10 | wrong int/void return transfer, `pop` underflow, stale epoch during push/pop, and dirty=`actual-1` preserve all prior frame slots/depth/digest/logs. |
| C11 | exact finite return at maxTotalSteps wins; otherwise runnable state becomes `STEP_LIMIT`, not SOE/ArithmeticException/value. |
| C12 | malformed call in unreachable Code is rejected during complete EVM predecode/link; no class/result whitelist or lazy skipped failure. |

This list promises neither general linkage nor full verifier behavior. Full
Throwable construction/APIs, exception tables, handler matching/unwind,
initialization, statics, cross-class calls, references/heap, libraries and MC stay
outside this proposal.

## 8. Complete ordered unchanged outcome catalogue

`catalogue.jsonl` contains all 268 cumulative rows and binds each exact row to its
raw-class byte length/SHA-256. The accepted S1 rows 1..82 are unchanged and remain
fully catalogued by S1's accepted root
`f98038bd7cb12d165c0b22dd7feca869803efce86a8194f4a3ddb1973f84764b`;
they are not duplicated below. The tables below exhaustively list every increment
row in manifest order with exact args, all-three outcome, TEST-only dispatch/frame/
call expectations, and current monolith gas. A future catalogue commitment must
extend by ordered leaves; it may not deduplicate repeated roots/arguments or feed
outcomes/counts to the VM.

### M2b rows 83..201 (119)

| # | ID | exact entry and args | JVM8 = JVM21 = monolith | dispatches / frames / calls | monolith gas |
|---:|---|---|---|---:|---:|
| 83 | `m2b-ldc-positive` | `IntegerConstants.positiveLdc()I` `[]` | `123456789` | 2 / 1 / 0 | 455493 |
| 84 | `m2b-ldc-negative` | `IntegerConstants.negativeLdc()I` `[]` | `-123456789` | 2 / 1 / 0 | 455493 |
| 85 | `m2b-ldc-max` | `IntegerConstants.maxLdc()I` `[]` | `2147483647` | 2 / 1 / 0 | 454843 |
| 86 | `m2b-ldc-min` | `IntegerConstants.minLdc()I` `[]` | `-2147483648` | 2 / 1 / 0 | 454843 |
| 87 | `m2b-ldc-high-bit-pattern` | `IntegerConstants.highBitPattern()I` `[]` | `-2147418111` | 2 / 1 / 0 | 456130 |
| 88 | `m2b-ldc-alternating-bits` | `IntegerConstants.alternatingBits()I` `[]` | `1515890085` | 2 / 1 / 0 | 456442 |
| 89 | `m2b-ldc-add` | `IntegerConstants.addLdc(I)I` `[23]` | `1000000023` | 4 / 1 / 0 | 468050 |
| 90 | `m2b-ldc-add-overflow` | `IntegerConstants.addLdc(I)I` `[2147483647]` | `-1147483649` | 4 / 1 / 0 | 468050 |
| 91 | `m2b-ldc-wide-index` | `WideIntegerConstant.loadWide()I` `[]` | `123456789` | 2 / 1 / 0 | 747222 |
| 92 | `m2b-imul-zero-min` | `IntegerArithmetic.multiply(II)I` `[0,-2147483648]` | `0` | 4 / 1 / 0 | 432301 |
| 93 | `m2b-imul-one-max` | `IntegerArithmetic.multiply(II)I` `[1,2147483647]` | `2147483647` | 4 / 1 / 0 | 432301 |
| 94 | `m2b-imul-negone-min-wrap` | `IntegerArithmetic.multiply(II)I` `[-1,-2147483648]` | `-2147483648` | 4 / 1 / 0 | 432301 |
| 95 | `m2b-imul-max-two-wrap` | `IntegerArithmetic.multiply(II)I` `[2147483647,2]` | `-2` | 4 / 1 / 0 | 432301 |
| 96 | `m2b-imul-min-two-wrap` | `IntegerArithmetic.multiply(II)I` `[-2147483648,2]` | `0` | 4 / 1 / 0 | 432301 |
| 97 | `m2b-imul-mixed-sign` | `IntegerArithmetic.multiply(II)I` `[-7,6]` | `-42` | 4 / 1 / 0 | 432301 |
| 98 | `m2b-imul-both-negative` | `IntegerArithmetic.multiply(II)I` `[-7,-6]` | `42` | 4 / 1 / 0 | 432301 |
| 99 | `m2b-imul-square-overflow` | `IntegerArithmetic.multiply(II)I` `[46341,46341]` | `-2147479015` | 4 / 1 / 0 | 432301 |
| 100 | `m2b-imul-power-overflow-zero` | `IntegerArithmetic.multiply(II)I` `[65536,65536]` | `0` | 4 / 1 / 0 | 432301 |
| 101 | `m2b-imul-large-mixed` | `IntegerArithmetic.multiply(II)I` `[123456789,-17]` | `-2098765413` | 4 / 1 / 0 | 432301 |
| 102 | `m2b-idiv-exact` | `IntegerArithmetic.divide(II)I` `[42,6]` | `7` | 4 / 1 / 0 | 433060 |
| 103 | `m2b-idiv-truncate` | `IntegerArithmetic.divide(II)I` `[7,3]` | `2` | 4 / 1 / 0 | 433060 |
| 104 | `m2b-idiv-negative-dividend` | `IntegerArithmetic.divide(II)I` `[-7,3]` | `-2` | 4 / 1 / 0 | 433060 |
| 105 | `m2b-idiv-negative-divisor` | `IntegerArithmetic.divide(II)I` `[7,-3]` | `-2` | 4 / 1 / 0 | 433060 |
| 106 | `m2b-idiv-both-negative` | `IntegerArithmetic.divide(II)I` `[-7,-3]` | `2` | 4 / 1 / 0 | 433060 |
| 107 | `m2b-idiv-min-negone` | `IntegerArithmetic.divide(II)I` `[-2147483648,-1]` | `-2147483648` | 4 / 1 / 0 | 433011 |
| 108 | `m2b-idiv-min-one` | `IntegerArithmetic.divide(II)I` `[-2147483648,1]` | `-2147483648` | 4 / 1 / 0 | 433085 |
| 109 | `m2b-idiv-max-negone` | `IntegerArithmetic.divide(II)I` `[2147483647,-1]` | `-2147483647` | 4 / 1 / 0 | 433060 |
| 110 | `m2b-idiv-smaller-than-divisor` | `IntegerArithmetic.divide(II)I` `[1,-2147483648]` | `0` | 4 / 1 / 0 | 433060 |
| 111 | `m2b-idiv-zero-dividend` | `IntegerArithmetic.divide(II)I` `[0,-7]` | `0` | 4 / 1 / 0 | 433060 |
| 112 | `m2b-idiv-max-two` | `IntegerArithmetic.divide(II)I` `[2147483647,2]` | `1073741823` | 4 / 1 / 0 | 433060 |
| 113 | `m2b-idiv-zero-divisor` | `IntegerArithmetic.divide(II)I` `[7,0]` | `java.lang.ArithmeticException` | 3 / 1 / 0 | 1432951 |
| 114 | `m2b-irem-positive` | `IntegerArithmetic.remainder(II)I` `[43,6]` | `1` | 4 / 1 / 0 | 433400 |
| 115 | `m2b-irem-truncate-pair` | `IntegerArithmetic.remainder(II)I` `[7,3]` | `1` | 4 / 1 / 0 | 433400 |
| 116 | `m2b-irem-negative-dividend` | `IntegerArithmetic.remainder(II)I` `[-7,3]` | `-1` | 4 / 1 / 0 | 433400 |
| 117 | `m2b-irem-negative-divisor` | `IntegerArithmetic.remainder(II)I` `[7,-3]` | `1` | 4 / 1 / 0 | 433400 |
| 118 | `m2b-irem-both-negative` | `IntegerArithmetic.remainder(II)I` `[-7,-3]` | `-1` | 4 / 1 / 0 | 433400 |
| 119 | `m2b-irem-min-negone` | `IntegerArithmetic.remainder(II)I` `[-2147483648,-1]` | `0` | 4 / 1 / 0 | 433386 |
| 120 | `m2b-irem-min-three` | `IntegerArithmetic.remainder(II)I` `[-2147483648,3]` | `-2` | 4 / 1 / 0 | 433425 |
| 121 | `m2b-irem-max-negone` | `IntegerArithmetic.remainder(II)I` `[2147483647,-1]` | `0` | 4 / 1 / 0 | 433400 |
| 122 | `m2b-irem-smaller-than-divisor` | `IntegerArithmetic.remainder(II)I` `[1,-2147483648]` | `1` | 4 / 1 / 0 | 433400 |
| 123 | `m2b-irem-zero-dividend` | `IntegerArithmetic.remainder(II)I` `[0,-7]` | `0` | 4 / 1 / 0 | 433400 |
| 124 | `m2b-irem-max-two` | `IntegerArithmetic.remainder(II)I` `[2147483647,2]` | `1` | 4 / 1 / 0 | 433400 |
| 125 | `m2b-irem-zero-divisor` | `IntegerArithmetic.remainder(II)I` `[7,0]` | `java.lang.ArithmeticException` | 3 / 1 / 0 | 1433315 |
| 126 | `m2b-ineg-zero` | `IntegerArithmetic.negate(I)I` `[0]` | `0` | 3 / 1 / 0 | 424238 |
| 127 | `m2b-ineg-one` | `IntegerArithmetic.negate(I)I` `[1]` | `-1` | 3 / 1 / 0 | 424238 |
| 128 | `m2b-ineg-negone` | `IntegerArithmetic.negate(I)I` `[-1]` | `1` | 3 / 1 / 0 | 424238 |
| 129 | `m2b-ineg-max` | `IntegerArithmetic.negate(I)I` `[2147483647]` | `-2147483647` | 3 / 1 / 0 | 424238 |
| 130 | `m2b-ineg-min-wrap` | `IntegerArithmetic.negate(I)I` `[-2147483648]` | `-2147483648` | 3 / 1 / 0 | 424238 |
| 131 | `m2b-ineg-positive` | `IntegerArithmetic.negate(I)I` `[123456789]` | `-123456789` | 3 / 1 / 0 | 424238 |
| 132 | `m2b-ineg-negative` | `IntegerArithmetic.negate(I)I` `[-123456789]` | `123456789` | 3 / 1 / 0 | 424238 |
| 133 | `m2b-ishl-zero-distance` | `IntegerShifts.shiftLeft(II)I` `[1,0]` | `1` | 4 / 1 / 0 | 422598 |
| 134 | `m2b-ishl-thirty-one` | `IntegerShifts.shiftLeft(II)I` `[1,31]` | `-2147483648` | 4 / 1 / 0 | 422598 |
| 135 | `m2b-ishl-thirty-two` | `IntegerShifts.shiftLeft(II)I` `[1,32]` | `1` | 4 / 1 / 0 | 422598 |
| 136 | `m2b-ishl-thirty-three` | `IntegerShifts.shiftLeft(II)I` `[1,33]` | `2` | 4 / 1 / 0 | 422598 |
| 137 | `m2b-ishl-negative-distance` | `IntegerShifts.shiftLeft(II)I` `[1,-1]` | `-2147483648` | 4 / 1 / 0 | 422598 |
| 138 | `m2b-ishl-negative-value` | `IntegerShifts.shiftLeft(II)I` `[-1,1]` | `-2` | 4 / 1 / 0 | 422598 |
| 139 | `m2b-ishl-max-overflow` | `IntegerShifts.shiftLeft(II)I` `[2147483647,1]` | `-2` | 4 / 1 / 0 | 422598 |
| 140 | `m2b-ishl-min-overflow` | `IntegerShifts.shiftLeft(II)I` `[-2147483648,1]` | `0` | 4 / 1 / 0 | 422598 |
| 141 | `m2b-ishl-pattern-four` | `IntegerShifts.shiftLeft(II)I` `[305419896,4]` | `591751040` | 4 / 1 / 0 | 422598 |
| 142 | `m2b-ishl-large-distance` | `IntegerShifts.shiftLeft(II)I` `[305419896,2147483647]` | `0` | 4 / 1 / 0 | 422598 |
| 143 | `m2b-ishr-min-zero` | `IntegerShifts.shiftRight(II)I` `[-2147483648,0]` | `-2147483648` | 4 / 1 / 0 | 422976 |
| 144 | `m2b-ishr-min-one` | `IntegerShifts.shiftRight(II)I` `[-2147483648,1]` | `-1073741824` | 4 / 1 / 0 | 422976 |
| 145 | `m2b-ishr-min-thirty-one` | `IntegerShifts.shiftRight(II)I` `[-2147483648,31]` | `-1` | 4 / 1 / 0 | 422976 |
| 146 | `m2b-ishr-min-thirty-two` | `IntegerShifts.shiftRight(II)I` `[-2147483648,32]` | `-2147483648` | 4 / 1 / 0 | 422976 |
| 147 | `m2b-ishr-min-thirty-three` | `IntegerShifts.shiftRight(II)I` `[-2147483648,33]` | `-1073741824` | 4 / 1 / 0 | 422976 |
| 148 | `m2b-ishr-min-negative-distance` | `IntegerShifts.shiftRight(II)I` `[-2147483648,-1]` | `-1` | 4 / 1 / 0 | 422976 |
| 149 | `m2b-ishr-max-one` | `IntegerShifts.shiftRight(II)I` `[2147483647,1]` | `1073741823` | 4 / 1 / 0 | 422976 |
| 150 | `m2b-ishr-negone-large-distance` | `IntegerShifts.shiftRight(II)I` `[-1,2147483647]` | `-1` | 4 / 1 / 0 | 422976 |
| 151 | `m2b-ishr-positive-pattern-four` | `IntegerShifts.shiftRight(II)I` `[305419896,4]` | `19088743` | 4 / 1 / 0 | 422976 |
| 152 | `m2b-ishr-negative-pattern-four` | `IntegerShifts.shiftRight(II)I` `[-305419896,4]` | `-19088744` | 4 / 1 / 0 | 422976 |
| 153 | `m2b-iushr-min-zero` | `IntegerShifts.shiftRightUnsigned(II)I` `[-2147483648,0]` | `-2147483648` | 4 / 1 / 0 | 425485 |
| 154 | `m2b-iushr-min-one` | `IntegerShifts.shiftRightUnsigned(II)I` `[-2147483648,1]` | `1073741824` | 4 / 1 / 0 | 425485 |
| 155 | `m2b-iushr-min-thirty-one` | `IntegerShifts.shiftRightUnsigned(II)I` `[-2147483648,31]` | `1` | 4 / 1 / 0 | 425485 |
| 156 | `m2b-iushr-min-thirty-two` | `IntegerShifts.shiftRightUnsigned(II)I` `[-2147483648,32]` | `-2147483648` | 4 / 1 / 0 | 425485 |
| 157 | `m2b-iushr-min-thirty-three` | `IntegerShifts.shiftRightUnsigned(II)I` `[-2147483648,33]` | `1073741824` | 4 / 1 / 0 | 425485 |
| 158 | `m2b-iushr-min-negative-distance` | `IntegerShifts.shiftRightUnsigned(II)I` `[-2147483648,-1]` | `1` | 4 / 1 / 0 | 425485 |
| 159 | `m2b-iushr-negone-one` | `IntegerShifts.shiftRightUnsigned(II)I` `[-1,1]` | `2147483647` | 4 / 1 / 0 | 425485 |
| 160 | `m2b-iushr-negone-thirty-one` | `IntegerShifts.shiftRightUnsigned(II)I` `[-1,31]` | `1` | 4 / 1 / 0 | 425485 |
| 161 | `m2b-iushr-max-one` | `IntegerShifts.shiftRightUnsigned(II)I` `[2147483647,1]` | `1073741823` | 4 / 1 / 0 | 425485 |
| 162 | `m2b-iushr-negative-pattern-four` | `IntegerShifts.shiftRightUnsigned(II)I` `[-305419896,4]` | `249346712` | 4 / 1 / 0 | 425485 |
| 163 | `m2b-iand-zeroes` | `IntegerBitwise.and(II)I` `[0,0]` | `0` | 4 / 1 / 0 | 421269 |
| 164 | `m2b-iand-all-ones-and-zero` | `IntegerBitwise.and(II)I` `[-1,0]` | `0` | 4 / 1 / 0 | 421269 |
| 165 | `m2b-iand-opposite-signs` | `IntegerBitwise.and(II)I` `[-2147483648,2147483647]` | `0` | 4 / 1 / 0 | 421269 |
| 166 | `m2b-iand-alternating` | `IntegerBitwise.and(II)I` `[1431655765,-1431655766]` | `0` | 4 / 1 / 0 | 421269 |
| 167 | `m2b-iand-mixed-patterns` | `IntegerBitwise.and(II)I` `[305419896,-2023406815]` | `35930656` | 4 / 1 / 0 | 421269 |
| 168 | `m2b-ior-zeroes` | `IntegerBitwise.or(II)I` `[0,0]` | `0` | 4 / 1 / 0 | 420721 |
| 169 | `m2b-ior-all-ones-and-zero` | `IntegerBitwise.or(II)I` `[-1,0]` | `-1` | 4 / 1 / 0 | 420721 |
| 170 | `m2b-ior-opposite-signs` | `IntegerBitwise.or(II)I` `[-2147483648,2147483647]` | `-1` | 4 / 1 / 0 | 420721 |
| 171 | `m2b-ior-alternating` | `IntegerBitwise.or(II)I` `[1431655765,-1431655766]` | `-1` | 4 / 1 / 0 | 420721 |
| 172 | `m2b-ior-mixed-patterns` | `IntegerBitwise.or(II)I` `[305419896,-2023406815]` | `-1753917575` | 4 / 1 / 0 | 420721 |
| 173 | `m2b-ixor-zeroes` | `IntegerBitwise.xor(II)I` `[0,0]` | `0` | 4 / 1 / 0 | 421359 |
| 174 | `m2b-ixor-all-ones-and-zero` | `IntegerBitwise.xor(II)I` `[-1,0]` | `-1` | 4 / 1 / 0 | 421359 |
| 175 | `m2b-ixor-opposite-signs` | `IntegerBitwise.xor(II)I` `[-2147483648,2147483647]` | `-1` | 4 / 1 / 0 | 421359 |
| 176 | `m2b-ixor-alternating` | `IntegerBitwise.xor(II)I` `[1431655765,-1431655766]` | `-1` | 4 / 1 / 0 | 421359 |
| 177 | `m2b-ixor-mixed-patterns` | `IntegerBitwise.xor(II)I` `[305419896,-2023406815]` | `-1789848231` | 4 / 1 / 0 | 421359 |
| 178 | `m2b-i2b-0` | `IntegerConversions.toByte(I)I` `[0]` | `0` | 3 / 1 / 0 | 414836 |
| 179 | `m2b-i2b-127` | `IntegerConversions.toByte(I)I` `[127]` | `127` | 3 / 1 / 0 | 414836 |
| 180 | `m2b-i2b-128` | `IntegerConversions.toByte(I)I` `[128]` | `-128` | 3 / 1 / 0 | 414836 |
| 181 | `m2b-i2b-255` | `IntegerConversions.toByte(I)I` `[255]` | `-1` | 3 / 1 / 0 | 414836 |
| 182 | `m2b-i2b-256` | `IntegerConversions.toByte(I)I` `[256]` | `0` | 3 / 1 / 0 | 414836 |
| 183 | `m2b-i2b-neg1` | `IntegerConversions.toByte(I)I` `[-1]` | `-1` | 3 / 1 / 0 | 414836 |
| 184 | `m2b-i2b-min` | `IntegerConversions.toByte(I)I` `[-2147483648]` | `0` | 3 / 1 / 0 | 414836 |
| 185 | `m2b-i2b-max` | `IntegerConversions.toByte(I)I` `[2147483647]` | `-1` | 3 / 1 / 0 | 414836 |
| 186 | `m2b-i2c-0` | `IntegerConversions.toChar(I)I` `[0]` | `0` | 3 / 1 / 0 | 414897 |
| 187 | `m2b-i2c-65535` | `IntegerConversions.toChar(I)I` `[65535]` | `65535` | 3 / 1 / 0 | 414897 |
| 188 | `m2b-i2c-65536` | `IntegerConversions.toChar(I)I` `[65536]` | `0` | 3 / 1 / 0 | 414897 |
| 189 | `m2b-i2c-neg1` | `IntegerConversions.toChar(I)I` `[-1]` | `65535` | 3 / 1 / 0 | 414897 |
| 190 | `m2b-i2c-min` | `IntegerConversions.toChar(I)I` `[-2147483648]` | `0` | 3 / 1 / 0 | 414897 |
| 191 | `m2b-i2c-max` | `IntegerConversions.toChar(I)I` `[2147483647]` | `65535` | 3 / 1 / 0 | 414897 |
| 192 | `m2b-i2c-305419896` | `IntegerConversions.toChar(I)I` `[305419896]` | `22136` | 3 / 1 / 0 | 414897 |
| 193 | `m2b-i2c-neg123456789` | `IntegerConversions.toChar(I)I` `[-123456789]` | `13035` | 3 / 1 / 0 | 414897 |
| 194 | `m2b-i2s-0` | `IntegerConversions.toShort(I)I` `[0]` | `0` | 3 / 1 / 0 | 414025 |
| 195 | `m2b-i2s-32767` | `IntegerConversions.toShort(I)I` `[32767]` | `32767` | 3 / 1 / 0 | 414025 |
| 196 | `m2b-i2s-32768` | `IntegerConversions.toShort(I)I` `[32768]` | `-32768` | 3 / 1 / 0 | 414025 |
| 197 | `m2b-i2s-65535` | `IntegerConversions.toShort(I)I` `[65535]` | `-1` | 3 / 1 / 0 | 414025 |
| 198 | `m2b-i2s-65536` | `IntegerConversions.toShort(I)I` `[65536]` | `0` | 3 / 1 / 0 | 414025 |
| 199 | `m2b-i2s-neg1` | `IntegerConversions.toShort(I)I` `[-1]` | `-1` | 3 / 1 / 0 | 414025 |
| 200 | `m2b-i2s-min` | `IntegerConversions.toShort(I)I` `[-2147483648]` | `0` | 3 / 1 / 0 | 414025 |
| 201 | `m2b-i2s-max` | `IntegerConversions.toShort(I)I` `[2147483647]` | `-1` | 3 / 1 / 0 | 414025 |

### M3a rows 202..268 (67)

| # | ID | exact entry and args | JVM8 = JVM21 = monolith | dispatches / frames / calls | monolith gas |
|---:|---|---|---|---:|---:|
| 202 | `m3a-call-order-basic` | `M3aStaticCalls.multiArgumentOrder(III)I` `[1,2,3]` | `10203` | 15 / 2 / 1 | 870288 |
| 203 | `m3a-call-order-signed` | `M3aStaticCalls.multiArgumentOrder(III)I` `[-7,8,-9]` | `-69209` | 15 / 2 / 1 | 870288 |
| 204 | `m3a-call-order-overflow` | `M3aStaticCalls.multiArgumentOrder(III)I` `[2147483647,-2147483648,99]` | `-9901` | 15 / 2 / 1 | 870288 |
| 205 | `m3a-call-permutation-basic` | `M3aStaticCalls.multiArgumentPermutation(III)I` `[4,5,6]` | `60405` | 15 / 2 / 1 | 871861 |
| 206 | `m3a-call-permutation-signed` | `M3aStaticCalls.multiArgumentPermutation(III)I` `[-10,20,-30]` | `-300980` | 15 / 2 / 1 | 871861 |
| 207 | `m3a-call-zero-arg-prefix` | `M3aStaticCalls.zeroArgumentCall(I)I` `[41]` | `314200` | 6 / 2 / 1 | 807287 |
| 208 | `m3a-call-zero-arg-negative-prefix` | `M3aStaticCalls.zeroArgumentCall(I)I` `[-314160]` | `-1` | 6 / 2 / 1 | 807287 |
| 209 | `m3a-call-zero-arg-root` | `M3aStaticCalls.zeroOnly()I` `[]` | `314159` | 4 / 2 / 1 | 790943 |
| 210 | `m3a-call-private-positive` | `M3aStaticCalls.privateHelperCall(I)I` `[17]` | `149` | 9 / 2 / 1 | 830086 |
| 211 | `m3a-call-private-overflow` | `M3aStaticCalls.privateHelperCall(I)I` `[-2147483648]` | `2147483644` | 9 / 2 / 1 | 830086 |
| 212 | `m3a-call-overload-one` | `M3aStaticCalls.overloadOne(I)I` `[-12]` | `-1` | 7 / 2 / 1 | 823916 |
| 213 | `m3a-call-overload-two` | `M3aStaticCalls.overloadTwo(II)I` `[9,-4]` | `173` | 12 / 2 / 1 | 855532 |
| 214 | `m3a-call-overload-three` | `M3aStaticCalls.overloadThree(III)I` `[7,-8,9]` | `827` | 15 / 2 / 1 | 877141 |
| 215 | `m3a-call-nested-zero` | `M3aStaticCalls.nestedCall(I)I` `[0]` | `0` | 16 / 3 / 2 | 917138 |
| 216 | `m3a-call-nested-negative` | `M3aStaticCalls.nestedCall(I)I` `[-25]` | `-75` | 16 / 3 / 2 | 917138 |
| 217 | `m3a-call-deep-positive` | `M3aStaticCalls.deepNestedCall(I)I` `[13]` | `102` | 23 / 4 / 3 | 1016172 |
| 218 | `m3a-call-deep-negative` | `M3aStaticCalls.deepNestedCall(I)I` `[-101]` | `-582` | 23 / 4 / 3 | 1016172 |
| 219 | `m3a-call-caller-prefix-order` | `M3aStaticCalls.callerPrefix(III)I` `[12,7,-3]` | `12127` | 18 / 2 / 1 | 890354 |
| 220 | `m3a-call-caller-prefix-negative` | `M3aStaticCalls.callerPrefix(III)I` `[-8,-20,30]` | `-8497` | 18 / 2 / 1 | 890354 |
| 221 | `m3a-call-two-prefix-results` | `M3aStaticCalls.twoCallPrefix(II)I` `[4,9]` | `109` | 18 / 2 / 2 | 876955 |
| 222 | `m3a-call-two-prefix-overflow` | `M3aStaticCalls.twoCallPrefix(II)I` `[2147483647,-2147483648]` | `-17` | 18 / 2 / 2 | 876955 |
| 223 | `m3a-call-six-argument-order` | `M3aStaticCalls.sixArguments(IIIIII)I` `[1,2,3,4,5,6]` | `-21` | 30 / 2 / 1 | 962977 |
| 224 | `m3a-call-six-argument-signed` | `M3aStaticCalls.sixArguments(IIIIII)I` `[-1,20,-300,4000,-50000,600000]` | `-3866941` | 30 / 2 / 1 | 962977 |
| 225 | `m3a-call-returned-arithmetic-zero` | `M3aStaticCalls.returnedArithmetic(I)I` `[0]` | `-25` | 13 / 2 / 1 | 849711 |
| 226 | `m3a-call-returned-arithmetic-overflow` | `M3aStaticCalls.returnedArithmetic(I)I` `[2147483647]` | `2147483560` | 13 / 2 / 1 | 849711 |
| 227 | `m3a-call-callee-divide-value` | `M3aStaticCalls.calleeDivide(II)I` `[-2147483648,-1]` | `-2147483648` | 8 / 2 / 1 | 825156 |
| 228 | `m3a-call-callee-divide-zero` | `M3aStaticCalls.calleeDivide(II)I` `[123,0]` | `java.lang.ArithmeticException` | 6 / 2 / 1 | 1852323 |
| 229 | `m3a-call-callee-remainder-value` | `M3aStaticCalls.calleeRemainder(II)I` `[-29,6]` | `-5` | 8 / 2 / 1 | 826446 |
| 230 | `m3a-call-callee-remainder-zero` | `M3aStaticCalls.calleeRemainder(II)I` `[-5,0]` | `java.lang.ArithmeticException` | 6 / 2 / 1 | 1853588 |
| 231 | `m3a-call-nested-divide-zero` | `M3aStaticCalls.callThroughDivide(II)I` `[1,0]` | `java.lang.ArithmeticException` | 9 / 3 / 2 | 1946713 |
| 232 | `m3a-frame-caller-locals-positive` | `M3aFrames.callerLocalIsolation(II)I` `[7,11]` | `71232` | 38 / 2 / 1 | 847637 |
| 233 | `m3a-frame-caller-locals-negative` | `M3aFrames.callerLocalIsolation(II)I` `[-30,9]` | `-299081` | 38 / 2 / 1 | 847637 |
| 234 | `m3a-frame-parameter-positive` | `M3aFrames.parameterIsolation(I)I` `[23]` | `2416` | 17 / 2 / 1 | 740271 |
| 235 | `m3a-frame-parameter-overflow` | `M3aFrames.parameterIsolation(I)I` `[-2147483648]` | `-2147483647` | 17 / 2 / 1 | 740271 |
| 236 | `m3a-void-zero-arg` | `M3aFrames.voidNoArgs(I)I` `[0]` | `1` | 6 / 2 / 1 | 672066 |
| 237 | `m3a-void-zero-arg-max` | `M3aFrames.voidNoArgs(I)I` `[2147483647]` | `-2147483648` | 6 / 2 / 1 | 672066 |
| 238 | `m3a-void-one-arg-negative` | `M3aFrames.voidOne(I)I` `[-44]` | `-45` | 15 / 2 / 1 | 719037 |
| 239 | `m3a-void-one-arg-min` | `M3aFrames.voidOne(I)I` `[-2147483648]` | `2147483647` | 15 / 2 / 1 | 719037 |
| 240 | `m3a-void-nested-positive` | `M3aFrames.nestedVoidCall(I)I` `[19]` | `38` | 20 / 3 / 3 | 858228 |
| 241 | `m3a-void-nested-negative` | `M3aFrames.nestedVoidCall(I)I` `[-19]` | `-38` | 20 / 3 / 3 | 858228 |
| 242 | `m3a-pop-discard-int` | `M3aFrames.discardInt(I)I` `[37]` | `46` | 13 / 2 / 1 | 721037 |
| 243 | `m3a-pop-discard-int-max` | `M3aFrames.discardInt(I)I` `[2147483647]` | `-2147483640` | 13 / 2 / 1 | 721037 |
| 244 | `m3a-pop-discard-nested-zero` | `M3aFrames.discardNested(I)I` `[0]` | `-9` | 18 / 3 / 2 | 813099 |
| 245 | `m3a-pop-discard-nested-negative` | `M3aFrames.discardNested(I)I` `[-999]` | `-1008` | 18 / 3 / 2 | 813099 |
| 246 | `m3a-frame-prefix-call` | `M3aFrames.prefixAndCall(III)I` `[500,7,-9]` | `540` | 14 / 2 / 1 | 730422 |
| 247 | `m3a-frame-prefix-two-calls` | `M3aFrames.prefixAcrossTwoCalls(II)I` `[17,-6]` | `138` | 24 / 2 / 2 | 774228 |
| 248 | `m3a-void-callee-divide-zero` | `M3aFrames.voidDivide(II)I` `[77,0]` | `java.lang.ArithmeticException` | 6 / 2 / 1 | 1729720 |
| 249 | `m3a-recursive-sum-zero` | `M3aRecursion.recursiveSum(I)I` `[0]` | `0` | 7 / 2 / 1 | 659581 |
| 250 | `m3a-recursive-sum-one` | `M3aRecursion.recursiveSum(I)I` `[1]` | `1` | 16 / 3 / 2 | 698364 |
| 251 | `m3a-recursive-sum-ten` | `M3aRecursion.recursiveSum(I)I` `[10]` | `55` | 97 / 12 / 11 | 1047498 |
| 252 | `m3a-recursive-factorial-zero` | `M3aRecursion.recursiveFactorial(I)I` `[0]` | `1` | 8 / 2 / 1 | 670820 |
| 253 | `m3a-recursive-factorial-one` | `M3aRecursion.recursiveFactorial(I)I` `[1]` | `1` | 8 / 2 / 1 | 670820 |
| 254 | `m3a-recursive-factorial-five` | `M3aRecursion.recursiveFactorial(I)I` `[5]` | `120` | 48 / 6 / 5 | 836040 |
| 255 | `m3a-recursive-factorial-ten` | `M3aRecursion.recursiveFactorial(I)I` `[10]` | `3628800` | 98 / 11 / 10 | 1042608 |
| 256 | `m3a-recursive-fibonacci-zero` | `M3aRecursion.recursiveFibonacci(I)I` `[0]` | `0` | 8 / 2 / 1 | 679252 |
| 257 | `m3a-recursive-fibonacci-one` | `M3aRecursion.recursiveFibonacci(I)I` `[1]` | `1` | 8 / 2 / 1 | 679252 |
| 258 | `m3a-recursive-fibonacci-two` | `M3aRecursion.recursiveFibonacci(I)I` `[2]` | `1` | 26 / 3 / 3 | 754598 |
| 259 | `m3a-recursive-fibonacci-seven` | `M3aRecursion.recursiveFibonacci(I)I` `[7]` | `13` | 368 / 8 / 41 | 2187614 |
| 260 | `m3a-recursive-fibonacci-ten` | `M3aRecursion.recursiveFibonacci(I)I` `[10]` | `55` | 1592 / 11 / 177 | 7338674 |
| 261 | `m3a-mutual-recursion-zero` | `M3aRecursion.mutualParity(I)I` `[0]` | `1` | 7 / 2 / 1 | 651696 |
| 262 | `m3a-mutual-recursion-odd` | `M3aRecursion.mutualParity(I)I` `[7]` | `0` | 56 / 9 / 8 | 942355 |
| 263 | `m3a-mutual-recursion-even` | `M3aRecursion.mutualParity(I)I` `[8]` | `1` | 63 / 10 / 9 | 974528 |
| 264 | `m3a-mutual-recursion-deep` | `M3aRecursion.mutualParity(I)I` `[31]` | `0` | 224 / 33 / 32 | 1714971 |
| 265 | `m3a-recursive-gcd-basic` | `M3aRecursion.recursiveGcd(II)I` `[48,18]` | `6` | 32 / 5 / 4 | 782489 |
| 266 | `m3a-recursive-gcd-deeper` | `M3aRecursion.recursiveGcd(II)I` `[1071,462]` | `21` | 32 / 5 / 4 | 782489 |
| 267 | `m3a-recursive-frame-isolation` | `M3aRecursion.recursiveFrameIsolation(II)I` `[5,8]` | `153` | 138 / 10 / 9 | 1167510 |
| 268 | `m3a-recursive-stack-overflow` | `M3aRecursion.unboundedRecursion(I)I` `[0]` | `java.lang.StackOverflowError` | 510 / 128 / 128 | 3872540 |

## 9. Uncertainties requiring parent measurement before freeze

* Whether schema3 should retain the exact S1 metadata byte layout with a new magic
  or add an explicit opcode/effect table; either is acceptable only if EVM-derived,
  immutable, complete, and provenance-bound.
* Exact parser/module/coordinator runtime/initcode sizes and ordinary CREATE,
  registration, resume, cold/warm and dirty-slot gas are unmeasured here. The
  ceilings above are gates, not evidence that a production implementation fits.
* Terminal arithmetic canonicalization (retain pre-fault stack versus clear it)
  must be frozen consistently in state digest and independent tests. It cannot
  affect the reported Java kind or permit resume.
* M3a's storage module boundary, frame-page keying, physical dirty count and
  metadata call-record packing need an architecture prototype. No 64-dirty or
  8KiB-metadata assumption is accepted without measured worst classes/calls.
* TEST trace dispatch counts are deterministic for these bytes and proposed
  frame-cap semantics, but they are not host authority. Production must reach its
  own terminal state within committed caps and merely be compared afterward.

Recommended parent action: freeze only cumulative 201-row integer completion after
an architecture review of persisted Java terminal outcomes; keep the exact 268-row
M3a inventory as the next frame/static-call contract. This document itself makes
no freeze or acceptance claim.
