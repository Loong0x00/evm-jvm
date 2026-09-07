# M4a: integer-array heap and typed category-1 references

Continuous authority: JAVA_EVM_PROGRAM.md. Last-green M3d **1c8d990**,498 fixed
oracle cases. Three Sol/high workers; current installed Fast preference requests
priority without lowering reasoning. Parent integrates then continues toward
ordinary objects/constructors/instance dispatch, not Minecraft.

## Scope / execution boundary
Add **int[] only**, null, typed int/reference slots, local/static storage of int[]
references, helper parameters/returns, aliasing and array access in EVM memory.
All allocation, identity, reads/writes/type/null/bounds checks and Java outcomes
must execute INSIDE EVM. No host heap/reference creation, Java evaluation,
classfile preprocessing or specialized bytecode. Existing raw APIs/CLI unchanged.

New opcodes:
- nop0x00, aconst_null0x01
- aload0x19 / aload_0..3 0x2a..2d; astore0x3a / astore_0..3 0x4b..4e
- newarray0xbc with atype10 ONLY, arraylength0xbe, iaload0x2e, iastore0x4f
- areturn0xb0 (internal int[] return only)
- if_acmpeq/ne0xa5/0xa6; ifnull/non0xc6/0xc7
- category-1 pop2 0x58, dup_x1..dup2_x2 0x5a..0x5e, swap0x5f
  (retain existing pop/dup). Only category-1 forms; category-2 types remain absent.

No object allocation/instance fields/constructors/virtual/interface calls, other
array element types, nested/reference arrays, casts/instanceof, monitors, wide,
switch, other numeric types, handlers or library/native helpers this batch.

## Typed values / method and field contracts
- Distinguish uninitialized local, int, and reference values. A packed word with
  low32 payload and an explicit kind above it is recommended to avoid parallel
  arrays/expensive dispatch; representation is worker-owned. Numeric operations
  must never leak/forge kind bits through overflow/shifts. Ref null is distinct
  from int zero. Every int/array/local/branch/call/return/field operation checks
  its required kind. Preserve old uninitialized/range/underflow error distinctions.
- Nonzero reference values identify allocated int arrays in an invocation-local
  EVM heap. Assignment/calls/returns copy identity, not array contents. Distinct
  allocations including zero-length arrays have distinct identity; aliases share
  writes. Heap survives method returns, resets on new Run/RunClasses.
- Internal method descriptors accept I and [I parameters, and I/V/[I returns.
  Root entry STILL requires ONLY I parameters and I return. Host int32 arguments
  must not be interpreted as arbitrary reference IDs; reject array-root signatures
  with MethodError11. Do not silently broaden to Object, other arrays or dimensions.
- Static fields permit I and [I; int[] fields prepare to null. Field access,
  inheritance/shared declaring-owner storage, initialization and final-reference
  write restrictions remain. Final array references do not make elements immutable.
  ConstantValue handling stays only supported static I; no native String constants.
- Arrayref arguments/returns and static refs may cross class boundaries with all
  existing name/access/init checks. Caller stack/locals and kind tags survive calls
  and initializer continuations. Root/ref-output ABI remains unchanged.

## Array semantics / resource profile
- New arrays are zero-filled; negative length throws NegativeArraySizeException.
- arraylength/iaload/iastore on null throw NullPointerException. Null check occurs
  before bounds check. Indices are signed int32; negative or >=length throws
  ArrayIndexOutOfBoundsException. Writes and arithmetic preserve int32 wrapping.
- Branches compare reference identity, not length/content; new if*/opcode widths
  must be included in in-EVM instruction-boundary/branch validation.
- Stack permutation forms preserve kinds and value order; mixed refs/ints are
  legal category-1 values. Raw integer-as-reference bytecode is a validation error,
  not a fabricated NullPointerException or access to a forged heap handle.
- Explicit heap limits: at most1024 arrays allocated per invocation, each length
  <=65536, and <=262144 total elements allocated. No GC/reclamation yet; allocations
  count even after references disappear. Exceeding a positive capacity is an
  implementation OutOfMemoryError; negative length takes precedence over caps.
  Report these as resource-profile limits, not OpenJDK heap-size compatibility.
- EVM OOG is separate; caps do not guarantee enough gas for an allowed allocation.
  Check sizes before allocation; keep class64/frame128/CP4096/code65535/local-stack
  1024 caps. Artifact is already overEIP170; local runtime.Execute only.

## Frozen outcomes and validation
Preserve JavaException kinds1 ArithmeticException,2 StackOverflowError,3 EIIE.
Add exact known kinds:
4 java.lang.NegativeArraySizeException
5 java.lang.ArrayIndexOutOfBoundsException
6 java.lang.NullPointerException
7 java.lang.OutOfMemoryError

Known non-Error exceptions1/4/5/6 escaping an active initializer become kind3.
Error kinds2/7 remain unwrapped; OOG/validation/hierarchy faults stay EVM errors.
No catch/unwind/exception objects/retry semantics newly claimed. Go only decodes
exact known payloads; CLI still emits exactly one value or exception key.

- BytecodeError14(pc): value-kind mismatch (int vs ref), preserving existing
  codes3/4/8/9/11 etc. Keep CallError5 for return opcode vs descriptor mismatch.
- ArrayError(uint256 code,uint256 pc), code1: unsupported newarray atype;
  predecode may reject this explicitly (don't silently construct an int array).
- ReferenceError(uint256 code,uint256 pc), code1: impossible/dangling nonnull
  handle or wrong heap kind, defensive EVM validation (not a Java exception).
  Well-typed guest code should not be able to forge this; source review is fine
  if no legitimate input can reach it without bypassing other checks.
- get/put/call kind mismatches at the instruction are BytecodeError14; unsupported
  method/field descriptors retain Method/Call/Field errors. Reference comparisons
  must reject int operands, and numeric operations must reject reference operands.
- Truncated newarray operands/branch targets use existing exact BytecodeErrors.
  Malformed-input precedence is not a full JVM verifier, but isolate each test.

## Oracle/fixture/harness protocol
Add cumulative stage m4a/defaultm4a; schema1 and root int argument/result/known
exception formats stay. No external reference arguments or printed heap IDs.
Preserve prior498 manifest entries/sources/budgets. Append ~80–120 trustedcases:
array zero/length, fill/sum/search/small sort, alias vs distinct identity/null,
post/preincrement and assignment expressions (dup2/dup_x2), local/helper/static
references, returns from helpers, inheritance/static sharing, classinit arrays,
multiple classes/recursive helpers, null/bounds/negative length outcomes and
initializer wrapping. New arrays and loops remain modest for real JVM tests.

Do NOT attempt real host heap exhaustion for oracle OOM tests. Test EVM logical
heap caps via focused Go tests only; those limits differ from reference JVM.
Existing OracleMain catches body Throwable and root EIIE/StackOverflow; no need
to pretend host OOM cases ran. Keep trusted-source-only oracle warning.

## Parallel ownership and naming
Use assigned worktree, scoped local commits. No main/peer files, extra agents,
remote/global/provider config or unrelated full geth tests. Fast is orchestrator
configuration, not a JVM feature to implement. Only one worker edits runtime.

New Go helper symbols MUST be prefixed **runtimeM4a*** or **verifyM4a*** respectively
(file isolation is not package-namespace isolation). Existing helpers may be reused
read-only. Avoid the M3d helper collision; don't duplicate generic function names.

| Worker | Allowed write set | Task |
|---|---|---|
| M4a-runtime | jvmevm/runtime/JVMSubsetInterpreter.sol + runtime.hex; jvmevm/jvmevm.go knownkinddecodeonly; jvmevm/jvmevm_test.go hash + obsolete newarray-negativeonly; jvmevm/integer_test.go known decoder tests only; NEW jvmevm/arrays_test.go | typed slots/heap/opcodes/descriptors/statics/outcomes, inline tests and old regressions |
| M4a-fixtures | jvmevm/testdata/differential/** only | append cases/sources, actual JVM/javap validation, preserve old498 |
| M4a-verifier | tools/java_diff.py, tools/test_java_diff.py, tools/JAVA_DIFF.md; NEW jvmevm/arrays_validation_test.go | stage/known-outcome mock tests and independent exact heap/type/alias/stack/error validation |

Old generic unsupported-newarray test becomes obsolete. Replace only its probe
with truly unsupported category-2 conversion (e.g. long arithmetic from int input
requiring i2l), retaining malformed-class/error purpose. Do not weaken tests to
any outcome or remove unchanged scalar/hierarchy/final checks. Independent tests
are test-first red on M3d; report honestly, don't skip/weaken/wait for peers.

Runtime tests must include each stack permutation's category-1 order/kinds,
negative/null/bounds ordering, exact typed validation, root-ref rejection and
EVM-only capacity limits, final-ref vs mutable-elements distinction, resets,
caller/ancestor/static/initializer interactions and old expected errors. Verifier
may generate/mutate CF only in tests to isolate malformed types/permutation forms;
no unsupported extra bytecodes masking the intended error (lesson from l2i).

## Gates / next continuation
Pinned source/artifact; focused Go/CLI incl independent suite; runner tests with
real legacy smoke; prior498+new oraclecases; AOT/vet. Parent probes identity/type/
alias/init/permutation boundaries and exact errors. Preserve old budgets where
possible; report measured performance blockers, never silently change outcomes
or treat OOG as success. Parent may explicitly version performance allowances.
After last-green commit, continue to ordinary objects/constructors/instance
fields and dispatch with a new bounded contract, no routine confirmation.

## Status
Contract frozen for M4a dispatch on accepted M3d1c8d990; not implemented yet.

## Accepted integration evidence

Runtime8070872→39aa8d0, fixturesbc328dc→32c8afe, verifier35eede3→7675694.
Independent parent review found dup_x2's minimum stack arity incorrectly2 instead
of3; reproduced Solidity Panic0x11, added exact negative regressions for every
category-1 permutation, fixed834f6bc→fd90e56. Assertions were not weakened.

Logical total-cap tests initially genuinely OOGed at100M. Four max arrays cost
138,995,136 gas; exceeding total cap after them costs138,964,154 gas. Only those
new capacity assertions use250M; an explicit100M OOG-not-OOM regression remains.
The old sum(100) demo now costs2,229,893 gas, above its old2M budget; independently
confirmed, preserved result5050/input100, raised demo-only budget to3M. No prior
498 oracle case or gas budget changed. Added a real int-array fillSum demo.

Parent integration reran artifact consistency, focused Go/CLI,29 real/mock Python
runner tests,613/613 JVM/EVM full cases,238 smoke,258 fast, demo, AOT regression
and focused vet. Additional44 independent alias/helper-return/final-reference/
inheritance/init/dup_x2/overflow/null-order probes passed, archive:
`build/java-diff-parent-m4a/probe-qhurqodg/results/`.

Accepted runtime40205 bytes, SHA256
`adb926d70915a716ebbb4f2f091584821fb70af82b743efcba084cb2f203a407`.
Local EVM execution only: artifact still exceeds EIP-170. Known compiler npm
findings remain; no downgrade, deployment or full-JVM claim. Continue directly
to bounded ordinary-object/constructor/field work, then virtual dispatch.
