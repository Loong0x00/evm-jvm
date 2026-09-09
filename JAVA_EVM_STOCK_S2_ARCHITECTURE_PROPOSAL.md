# Stock S2 architecture proposal: terminal integer faults, then persistent frames

Status: **proposal and ignored prototypes only**, based exactly on accepted Stock
S1 commit `1b5150dd74eb9cb292c81b10fd562cd4bb3b0539`. This document does not freeze an
implementation or change S0, S1, the accepted 2,231-case monolith, any old fixture,
or any old gas budget. Evidence is under the ignored directory
`build/java-diff-stock-s2-architecture/`.

## Recommendation: one schema, two acceptance slices

Do **not** attempt all 186 remaining M2b/M3a rows as one implementation gate. Use
one forward-compatible schema-3 metadata and persistent-frame model, but accept it
in two slices:

1. **S2a, terminal scalar integer completion:** all unchanged M1/M2/M2b rows,
   201 total (119 newly migrated), including `idiv`/`irem` and two genuine uncaught
   `java.lang.ArithmeticException` outcomes. It introduces the schema-3 parser,
   a one-root-frame state store, explicit terminal Java faults, and bounded dirty
   deltas. It does not execute calls.
2. **S2b, same-class calls and persistent frames:** retain all 201 and add all 67
   unchanged M3a rows, 268 total. It enables same-class `invokestatic`, private and
   overloaded internal methods, `I`/`V` returns, `pop`, recursion, a 128-active-frame
   cap, callee arithmetic propagation, and the genuine expected
   `java.lang.StackOverflowError` outcome.

S2a is the next small freeze candidate. S2b should be frozen only after S2a's real
artifact, registration, state-delta, rollback, and gas results are reviewed. The
schema-3 parser must nevertheless encode internal-callable methods and call-site
records from the start, so S2b reuses the identical issued metadata and state
format instead of introducing a second parser or migrating live state. Parser-only
S2a tests may inspect M3a metadata, but that is not a claim that S2a executes M3a.

This split isolates the small arithmetic/fault change from the materially different
call-stack persistence problem. Conversely, making two unrelated schemas would
repeat parsing and strand S2a state, while putting both semantic gates together
would make it difficult to distinguish arithmetic faults, metadata resolution,
frame persistence, and gas defects.

## Invariants and evidence boundary

Unchanged Java 52 classfiles, entry bytes, and `int32` arguments remain the only
guest inputs. The host may compile trusted fixtures, deploy opaque bytes, sign and
submit transactions, and decode exact checkpoint fields. Class/method/descriptor/
constant-pool resolution, call selection, argument transfer, execution, Java-fault
selection, and all resumed state transitions must execute in ordinary EVM bytecode.
No host offsets, descriptors, predecoded instructions, method IDs, expected values,
AOT, Java fallback, or monolith fallback enter production calls.

The accepted S0/S1 contracts, artifacts, ABIs, tests, versions, counts, and budgets
remain immutable. The 154,839-byte M5d-a runtime remains local `runtime.Execute`
evidence and is not assumed deployable or copied into S2. S2 counts remain a
separate stock migration view of existing semantics; they are not added to 2,231.
There is no opcode, gas-rule, precompile, consensus, EIP-170/EIP-3860/Osaka limit,
core/state/types/params, or host `SetCode`/`SetState` change.

No Minecraft artifact was downloaded or run, no EULA was accepted, and no listener,
filesystem/network substitute, Java/server-logic fallback, or startup claim is
part of this work.

## Verified workload and source measurements

A clean cumulative differential run at the base used `javac 21.0.9 --release 8`
with the fixture runner's unchanged default debug attributes:

```sh
make java-build
PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py \
  --stage m3a --tier full \
  --artifacts build/java-diff-stock-s2-architecture/legacy-m3a
# selected=268 passed=268 failed=0
```

It compared the actual host JVM and accepted monolith using runtime SHA-256
`dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
The result is 261 values, six `ArithmeticException`s, and one
`StackOverflowError`. The monolith's aggregate 169,759,879 local-call gas and
7,338,674 maximum (`m3a-recursive-fibonacci-ten`) exclude ordinary deployment and
continuation; they are not S2 budgets.

A bounded trusted-fixture-only classfile interpreter independently reproduced all
268 terminal values/classes and counted complete JVM instructions, including a
faulting `idiv`/`irem` or frame-overflow `invokestatic` as one attempted bytecode.
This analyzer is **host-metadata lower-bound evidence, not conformance**; none of
its metadata may enter an S2 call.

| Cumulative profile | Cases / roots / classes | Outcomes | Total terminal steps | Longest case |
|---|---:|---:|---:|---:|
| through M2b (S2a) | 201 / 60 / 11 | 199 values, 2 arithmetic faults | 2,642 | `sum(100)`, 806 |
| through M3a (S2b) | 268 / 94 / 14 | 261 values, 6 arithmetic faults, 1 SOE | 6,702 | recursive Fibonacci(10), 1,592 |

The 67 M3a rows alone execute 4,060 terminal steps. Fibonacci(10) makes 177 calls,
reaches depth 11, and enters two method identities. The deepest terminating value
case is mutual recursion at depth 33. The SOE row attempts 128 calls, executes 510
steps, and reaches exactly 128 active frames before the attempted 129th frame
becomes kind 2. Across any one actual value row, at most four method identities and
three distinct Methodrefs are entered.

The actual new classfiles are:

| Class | Bytes | CP count | Methods | all Code bytes | call sites / distinct refs | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| `IntegerArithmetic` | 431 | 19 | 5 | 20 | 0 / 0 | `69c6a01e0045efc1caa3e2a9c598a4dd75530fe74f5b4e2c378689feb1c27d43` |
| `IntegerBitwise` | 353 | 17 | 4 | 17 | 0 / 0 | `8cece8e7b75cf657b146eade5cd73d8616826f73ac14427e8e1f0c51fa9dc018` |
| `IntegerConstants` | 633 | 29 | 8 | 28 | 0 / 0 | `189ac9b47a7f09a080a64be3e662aba0045440ca78a6d65674256e0cb0aaf0fd` |
| `IntegerConversions` | 368 | 17 | 4 | 14 | 0 / 0 | `ba383508690bf9aab643b26af435077cc002d8b4ccd61cd6b52b734a82e7fd08` |
| `IntegerShifts` | 380 | 17 | 4 | 17 | 0 / 0 | `1cd887856a8e6922e14c5246c3c563dd5914d499511b0be0fc9b35178d9df2bc` |
| `WideIntegerConstant` | 3,469 | 277 | 3 | 802 | 0 / 0 | `fbf7d7498a50fa0ed8adba88ef74f702cdd4bc82fdab94ba75c8e54a77eb9137` |
| `M3aFrames` | 1,601 | 55 | 20 | 190 | 14 / 9 | `c1807e5289b9981e4804e1bc37575fd44dff1feebb914a235dbd5a32d173d5ad` |
| `M3aRecursion` | 1,390 | 47 | 16 | 163 | 16 / 8 | `3bfec29278c225bb553daf4bd242f61fafe6e7ea1c3a4e31c1fd699c912ac842` |
| `M3aStaticCalls` | 2,169 | 73 | 31 | 239 | 21 / 13 | `316f4878ac2fc59113ee81d20e76304f5eaa32575b3931088b1b1da1adb21156` |

The five accepted S1 classes remain exactly the hashes and sizes in the S1 plan.
The cumulative maxima are raw bytes 3,469, CP count 277, declared methods 31,
entered Code 25 bytes, `max_stack=6`, `max_locals=6`, six integer arguments, and
21 call sites in one class. `WideIntegerConstant.populateIntegerPool` is a real
793-byte unused method containing 261 literal sites; its selected `loadWide` is a
small genuine `ldc_w`. A correct parser must retain the class, mark the oversized
unused method ineligible, discard its partial literal cache, and still execute
`loadWide`. It must not lower the class/CP cap or pretend the wide constant was
host-resolved.

S1's parser already handles CP 277 and raw size 3,469, but its method analyzer does
not accept `idiv`, shifts, conversions, calls, private methods, void descriptors,
or six arguments. Its schema-2 records are public `(I{0..4})I` roots, and its
coordinator persists one fixed `MachineV2`. Therefore a new executor alone is not
enough, and a 128-element monolith `Frame[]` copied through every ABI call is not
acceptable.

## Schema-3 parsed program

Keep accepted `ArtifactPage` and exact `STOP || rawClass` pages. Add a new append-
only `S2ClassParser`, hash-pinned `S2AnalyzeModule`, and constructor-only
`S2MetadataPage`. Registration reads and hashes the raw page, derives every record
in EVM, and creates immutable metadata with ordinary internal `CREATE`. Splitting
the analyzer from the registry is permitted because the accepted S1 parser is
already 15,271 bytes; both deployed components must independently fit EIP-170 and
be pinned in `classId`. It is not permission to supply host metadata.

Candidate schema 3 uses eight 32-byte header words, five words per declared method,
8-byte integer-literal records, and 16-byte call-site records. Freeze exact bit
positions in the implementation plan, but preserve these semantic fields:

- header: schema magic, raw page/address/code/payload identities, parser and
  analyzer identities, class-name hash/access, raw length, CP/method/literal/call
  counts;
- method: declared index, name and descriptor hashes, access, Code offset/length,
  max stack/locals, integer argument count, return kind (`I` or `V`), eligibility
  or exact deferred error, 256-bit instruction starts, literal and call slices;
- literal: `(methodIndex:u16, pc:u16, intBits:u32)`, ordered by method then PC;
- call: `(callerMethod:u16, pc:u16, cpIndex:u16, targetMethod:u16, argc:u8,
  returnKind:u8, flags:u16, reserved:u32)`, ordered by caller then PC.

Caps should remain raw bytes 4,096, CP count 512, declared methods 32, selected or
internal-entered Code 256, stack/locals 8, total eligible literal records 256, and
total eligible call records 32. The maximum payload is exactly
`8*32 + 32*5*32 + 256*8 + 32*16 = 7,936` bytes (7,937 with STOP), retaining S1's
8 KiB metadata-runtime ceiling. The measured largest call class would be 5,560
payload bytes; `M3aFrames` 3,680; `M3aRecursion` 3,072; and the wide-constant class
744 after correctly discarding the oversized method's literals.

Registration must proceed in two internal analyses: first establish bounded method
names/descriptors/access/Code envelopes, then predecode eligible methods and resolve
calls. Internal callable methods may be private, package, protected, or public but
must be static, nonsynchronized, nonnative, nonabstract, have exactly one bounded
Code with no handlers, and descriptor `(I{0..6})I` or `(I{0..6})V`. Constructors,
`<clinit>`, fields, interfaces, and external owners remain ineligible/unsupported.
Root selection remains one unambiguous declared public static name and an `I`
return; unrelated internal overloads do not affect exact call resolution.

For each `invokestatic`, resolve `CONSTANT_Methodref` (tag 10) through Class and
NameAndType/Utf8 chains in EVM, require the owner name to equal the declared class
name, and find one exact target by **name plus descriptor**. Cache the resolved
method and descriptor effect in the immutable call record. At execution, verify
that the raw opcode's CP operand equals the cached `cpIndex` at that caller/PC;
metadata code hash and class/program roots bind the target. Never rescan the whole
CP per recursion and never accept a host target index. InterfaceMethodref, external
owner, non-int/reference/category-2 descriptors, and malformed chains are explicit
call errors.

Flow analysis must include `idiv`, `irem`, shifts, bitwise/conversions, `pop`,
`invokestatic` descriptor stack effects, `ireturn`, and void `return`. It validates
all decoded widths and branch targets before dataflow, preserves definite-local and
equal-stack-height checks, and allows recursive call graphs without recursively
parsing them.

Suggested domain-separated identities include schema, every component code hash,
and immutable metadata:

```text
classId   = H(DS2CLASS, 3, parserHash, analyzerHash, rawPage,
              rawPageHash, payloadHash, metadataHash)
programId = H(DS2PROGRAM, 3, classId, rootMethod, rootNameHash,
              rootDescriptorHash, activeStepModuleHash, storeTemplateHash)
inputRoot = H(DS2INPUT, programId, frameStore, argsHash, maxTotalSteps,
              frameCap, dirtyFrameCap, dirtyWordCap)
```

A supplied address/hash is only a configuration commitment. S2a and S2b have
separate program IDs because they pin different active modules, while sharing the
class metadata format. Acceptance compares actual code byte-for-byte with pinned
reproducible artifacts and checks immutable references.

## Versioned persistent state, not a copied memory graph

Create one `S2FrameStore` per coordinator through ordinary internal CREATE. It has
an immutable coordinator owner, no public mutation path, and a mapping from stable,
monotonically allocated `uint64 frameId` to bounded frame records. A frame contains:

```text
frameId, parentFrameId, methodId, invokePC, pc, sp, initialized,
parentRoot, frameRoot, stack[8], locals[8]
```

Only initialized/active cells are nonzero and all cells retain the exact tagged-int
encoding. The root is frame 1. IDs are never reused during an invocation; popped
frame storage is cleared. `maxTotalSteps<=4096` bounds allocations without inventing
a separate Java OOM. `depth` and `currentFrameId` are header state, and depth is
capped at 128 active Java frames including the root.

Use a hash-linked active stack rather than recomputing or ABI-copying all active
frames. `frameRoot = H(schema, frame identity/content, parentRoot)`. A call first
forms the caller's post-call frame root, then gives that root to the child as
`parentRoot`. A return checks the stored parent frame hash against the child's
link before changing the parent. The checkpoint commits `activeRoot`, current ID,
depth, next ID, lifecycle/fault, counters, input root, component hashes, epoch,
and the prior digest/delta hash. The EVM account storage remains authoritative;
`stateDigest` is a transition-history commitment and must not be described as an
independently proven sparse-Merkle root.

The step module receives only fixed context/header, the store address, and bounds.
It loads the current frame and only subsequently touched parent/child frames into a
bounded cache. It returns sorted, unique final records for at most 16 touched frame
identities plus exact old/new frame hashes and a compact header transition. It does
**not** receive or return 128 frames, all metadata, the class CP, static/heap tables,
or the monolith memory arena. A delta may contain at most 192 changed logical frame
words. Execution stops at the last complete instruction before either delta cap;
a single call/return instruction is indivisible and must fit by construction.

The coordinator checks component/store provenance, epoch and old roots, exact ABI
length/canonicality, unique sorted frame IDs, new/delete legality, frame links,
depth/current/next-ID transitions, actual changed-frame/word counts, steps, and
terminal state before asking the owner-only store to apply. It then updates the
header/digest and emits one checkpoint. A store write, coordinator write, or log
is in the same EVM transaction: any later revert/OOG rolls all of them back. The
step module remains a bounded `STATICCALL`; it cannot mutate the store directly.
This is preferred over `DELEGATECALL`, which would expose all coordinator storage
to the executor and make dirty-write validation less meaningful.

### Atomic call and return transitions

`invokestatic` is one complete JVM step:

1. verify the cached Methodref and target metadata before changing state;
2. verify caller operand count/types and frame capacity;
3. preserve any caller expression prefix, pop arguments in descriptor order, and
   set caller PC to the instruction after the call;
4. allocate a child with independent stack/locals, stable ID, parent ID, the
   caller's opcode PC as `invokePC`, and arguments in locals 0..N-1; and
5. make the child current.

`ireturn`/`return` is one complete step: validate return kind/shape, verify the
parent link, clear the child, restore the parent, and push one int or nothing.
Caller locals and expression-prefix operands are untouched. S2b must reproduce
private helpers, exact overloads, void calls, discarded int results, direct/mutual
recursion, and recursive frame isolation from the actual sources.

## Lifecycle, Java faults, safepoints, and step counts

Candidate lifecycle values are `0 RUNNABLE`, `1 RETURNED`, `2 STEP_LIMIT`, and
`3 JAVA_FAULT`. `JAVA_FAULT` contains exactly:

```text
kind:u8, throwFrameId:u64, throwMethodId:u16, faultPC:u32
```

Kind 1 is `java.lang.ArithmeticException`; kind 2 is
`java.lang.StackOverflowError`. This is a successful terminal checkpoint, not a
Solidity custom-error revert. The host may decode only exact lifecycle-3 known
kinds to the existing outcome class. Validation/call/control errors, unknown fault
kinds, malformed module output, module/store revert, OOG, and transaction failure
remain EVM/harness failures. `STEP_LIMIT` is also distinct and is never a Java
value or exception.

On zero divisor or an attempted 129th active frame, count the faulting bytecode once,
retain the canonical pre-instruction frame at its opcode PC, and commit fault
identity. S2 has no exception object, handler search, or unwind. A callee arithmetic
fault is therefore terminal with its throwing frame identity; the EVM has still
resolved and executed the actual call chain. Later handler work can consume this
pending-fault shape without reconstructing lost frames, but S2 must not claim that
later semantics now.

Safepoints are only between complete instructions, at return, Java fault, requested
step exhaustion, dirty-cap exhaustion, or committed aggregate step exhaustion.
Dirty-cap exhaustion while runnable is an ordinary resumable checkpoint, not
`STEP_LIMIT`. Require `executed>=1`; same-PC/same-cell progress remains valid.
`RETURNED` or `JAVA_FAULT` wins on the exact aggregate cap; otherwise cap exhaustion
sets `STEP_LIMIT`. Terminal resume rejects.

The trusted trace model scheduled at most 128 bytecodes and 16 touched frame IDs per
resume. It predicts seven resumes for `sum(100)`, 14 for Fibonacci(10), five for
the depth-33 mutual recursion row, and nine for the 128-frame SOE row. Fibonacci's
largest modeled batch has 126 steps/16 frame identities. These are scheduling lower
bounds only: the model did not count production logical-word deltas, provenance, or
gas and cannot be an acceptance oracle.

## Candidate APIs for a later freeze

Names and exact tuple layout should be frozen by the parent only after a prototype
review. The minimal surface should resemble:

```solidity
S2ClassParser.registerClass(
    address rawPage, bytes32 expectedPageHash, bytes32 expectedPayloadHash
) returns (bytes32 classId, address metadataPage, bytes32 metadataHash,
           uint16 methods, uint16 literals, uint16 calls);

S2ClassParser.classRecord(bytes32 classId)
    view returns (address metadataPage, bytes32 metadataHash);

S2StepModule.step(
    ProgramContextV3 calldata program, address frameStore,
    HeaderV3 calldata beforeHeader, uint16 maxJvmSteps,
    uint8 maxDirtyFrames, uint16 maxDirtyWords
) view returns (HeaderV3 afterHeader, FrameDeltaV3[] deltas,
                uint16 executed, uint8 dirtyFrames, uint16 dirtyWords);

S2FrameStore.frame(uint64 frameId) view returns (FrameV3);
S2FrameStore.apply(
    uint64 expectedEpoch, FrameDeltaV3[] calldata deltas,
    HeaderCommitV3 calldata commit
); // coordinator only

S2Coordinator.resume(
    uint64 expectedEpoch, uint16 maxJvmSteps,
    uint8 maxDirtyFrames, uint16 maxDirtyWords
) returns (uint64 newEpoch, uint8 lifecycle, uint8 javaFaultKind,
           int32 result, uint16 executed, uint8 dirtyFrames,
           uint16 dirtyWords);

S2Coordinator.checkpoint() view returns (
    uint32 schema, bytes32 classId, bytes32 programId, bytes32 inputRoot,
    address frameStore, uint64 epoch, uint64 totalSteps,
    HeaderV3 header, JavaFaultV3 fault, bytes32 stateDigest
);
```

Callers never supply PC, frame IDs, state, method metadata, branch choices, fault,
or result. Configuration is immutable after construction. `resume` keeps S1's
stale-epoch guard, reentrancy lock, pre/post-encoding gas checks, bounded stipend,
800,000 commit reserve, exact response decoder, and failure bubbling.

## Candidate exact error domains

Do not use Solidity panics or a generic revert where one of these applies. Numeric
assignments are a proposal for the future freeze:

- `S2ClassError(code,offset)`: 1 outer boundary/trailing, 2 magic/version, 3 CP
  tag/index/two-slot/name chain, 4 class profile, 5 metadata counts/capacity,
  6 analyzer/metadata CREATE/registry consistency;
- `S2MethodError(code,index)`: 1 root missing, 2 root name ambiguous, 3 root access,
  4 root descriptor, 5 Code/caps/handlers, 6 reserved/unsupported, 7 argument count,
  8 invalid entry bytes;
- `S2BytecodeError(code,method,pc)`: retain S1 meanings 2 truncation, 3 underflow,
  5 stack/return shape, 6 unsupported opcode/literal kind, 7 fallthrough, 8 local
  range, 9 stack capacity, 11 uninitialized, 12 non-start/range, 14 malformed cell
  or frame, 15 branch target, 16 literal cache; add 17 dataflow join;
- `S2CallError(code,method,pc)`: 1 malformed Methodref chain/cache, 2 owner not the
  same class, 3 no unique exact name+descriptor target, 4 target flags/descriptor/
  Code unusable, 5 return opcode inconsistent with descriptor;
- `S2ControlError(code)`: 1 terminal, 2 component/provenance, 3 stale epoch,
  4 budget/cap range, 5 gas reserve, 6 dirty frame/word cap, 7 malformed module
  response/counters, 8 frame-store/link/delta transition.

Class/method/bytecode/call validation errors are never Java faults. The exact known
fault lifecycle is never one of these reverts.

## Measured storage prototype and provisional ceilings

An ignored Solidity prototype stored stable IDs, parent/invoke PC, six locals,
frame roots, active root, counters, and rollback state. It deliberately did not
parse or execute Java. It was compiled with solc 0.8.30, optimizer 200, via IR,
Cancun, metadata off: init 3,678 bytes; runtime 3,622 bytes, runtime SHA-256
`5baac0b0489e550e0d30569685d3f51af883753221daed9a70a9a62ba3306f0a`.

A Go driver used a funded test EOA only, signed legacy transactions under chain
1337 AllDev/Osaka rules, recovered the sender, used `TransactionToMessage` and
`core.ApplyMessage` with nonce/transaction checks enabled, and ordinary CREATE.
No code/storage injection or listener was used.

| Prototype operation | Signed gas |
|---|---:|
| ordinary CREATE | 858,572 |
| initialize root with six locals | 275,522 |
| mutate one current frame for a modeled 128-step scalar batch | 114,715 |
| create one child / eight children / sixteen children | 321,156 / 1,942,723 / 3,796,575 |
| clear/return sixteen children after that push | 917,871 |
| later sixteen-child depth batches | 3,776,675 each |
| final fifteen-child batch reaching depth 128 | 3,544,907 |
| write sixteen provisional frames then intentional revert | 774,488 failed gas |

The failed transaction left all sampled combined coordinator/store slots unchanged.
These figures include direct storage hashing and writes but omit Java parsing,
metadata provenance, module/store ABI transfer, semantic execution, full delta
validation, events, and reserve. They are **architecture lower bounds, not
conformance or gas acceptance**. In particular, the 3.80M write result rules out
retaining S1's 2M resume ceiling for a 16-frame dirty batch without measurement-
driven compression; it does not justify changing any protocol limit.

For comparison, accepted S1's complete valid 32-method/256-literal boundary
registers in 6,923,070 parent-sequence gas after the reviewed MCOPY fix; its parser,
step, and coordinator templates are 15,271, 8,408, and 6,328 bytes. S1's actual
`sum(100)` at 128 steps takes seven resumes and 10,324,488 isolated gas. These are
real deployed baselines, not estimates that a larger schema/frame executor will
inherit automatically.

Candidate S2a ceilings, to be success-required rather than silently raised:

- `maxJvmSteps=128`, `maxTotalSteps=4,096`, active frames exactly 1;
- `maxDirtyFrames=1`, `maxDirtyWords<=32` including fault/header words;
- every executable CREATE and actual-class registration transaction <=8,000,000;
- resume <=2,000,000 with an 800,000 commit reserve;
- project runtime <=16 KiB for each parser/analyzer/executor/store/coordinator and
  initcode <=24 KiB, both below the unchanged EIP-170/EIP-3860 protocol ceilings;
  report/refactor a larger component rather than raising the project target;
- metadata runtime <=8,192, raw page <=4,097 including STOP;
- isolated case <=13 successful external transactions (analyzer, parser, scalar
  module, raw page, registration, coordinator/store, then at most seven resumes)
  and <=30M aggregate positive gas; shared setup is reported separately;
- all 201 cases run at step budgets 64 and 128; short cases also 1/7/16, while
  long loops use complete 64/128 runs and bounded small-budget prefixes.

Candidate S2b ceilings, separately frozen only after a real S2a implementation:

- `maxJvmSteps=128`, `maxTotalSteps=4,096`, active-frame cap 128;
- `maxDirtyFrames<=16`, `maxDirtyWords<=192`; reaching a dirty cap pauses before
  the next complete instruction and is not a Java outcome;
- resume <=8,000,000 with the same 800,000 reserve; other CREATE/registration
  transactions remain <=8,000,000;
- isolated case <=20 successful transactions (six setup plus the measured-model
  maximum 14 resumes) and <=100M aggregate positive gas;
- all 268 cases complete at 64/128 requested steps subject to dirty caps; require
  the exact value/fault, total instruction count, active-depth/frame-ID invariants,
  and batch-independent terminal state, not an exact epoch count;
- the 8M/16-frame choice is provisional. A complete module exceeding it blocks
  S2b and requires compression or a smaller dirty slice, not an Osaka/gas/precompile
  change and not relabeling OOG as SOE.

Old manifest `gas_limit` values remain untouched and are reported separately from
all stock deployment/registration/resume costs.

## Acceptance gates to freeze later

### S2a

1. Compile the exact 11 source classes used through M2b with the existing command;
   check hashes, all 201 IDs/order/arguments/outcomes, JVM 8 and 21 where available,
   accepted monolith, and signed Stock S2a. No deduplication of argument vectors.
2. Require every M2b opcode and corner: `ldc/ldc_w`, multiply/divide/remainder,
   negate, masked signed/unsigned shifts, bitwise, `i2b/i2c/i2s`, INT_MIN/-1, both
   zero divisors, malformed/truncated/noninteger constants, and CP277 wide lookup.
3. Commit exact lifecycle-3 Arithmetic fault checkpoints and prove unknown kinds,
   arbitrary reverts, OOG, validation errors, and `STEP_LIMIT` cannot decode as it.
4. Prove schema-3 registration derives metadata in EVM, records the 793-byte unused
   method ineligible, discards its 261 literals, and retains genuine `ldc_w`.
5. Exercise one-frame delta caps before/after progress, stale epoch, reserve/OOG,
   malformed module responses, store owner/provenance, retries, terminal rejection,
   and full transaction rollback/no logs.
6. Parser-only schema tests cover the three M3a classes' internal descriptors,
   Methodref records, private overloads, and void methods. They confer no S2b
   execution acceptance.

### S2b

1. Add all 67 exact M3a rows: 62 values, four callee arithmetic faults, and one
   SOE; retain all 201 S2a rows. Compare genuine JVM/monolith outcomes and independent
   trusted checkpoint traces without passing trace data to EVM.
2. Require exact CP Methodref owner/name/descriptor resolution and immutable cache
   checks; malformed tag/chains, external owner, missing/duplicate exact target,
   bad target flags/Code, and wrong I/V return each produce exact `S2CallError`.
3. Check six-argument declaration order, zero/private helpers, overloads, caller
   expression prefixes/locals, void/no-value transfer, `pop`, nested returns, direct
   and mutual recursion, and frame IDs/parent/invokePC/root links across resumes.
4. At 128 active frames, the attempted next call commits exact kind-2 SOE. A low-
   gas version remains OOG. Arithmetic in a callee commits kind 1 at that callee's
   frame/method/PC without host unwinding or fabricated handler support.
5. Cross dirty/step boundaries immediately before/after call and return; exercise
   1 and 16 dirty-frame limits, exact 192-word bound, delete/refund paths, stale or
   reordered deltas, forged old hashes, frame alias/reuse, and rollback after store
   apply but before coordinator commit/event.
6. Run signed simulated-chain and direct signed ApplyMessage replay with identical
   explicit contexts. Verify deployed bytes/code hashes/immutables, receipts, gas,
   roots, epochs, logs, and EIP-170/EIP-3860/EIP-7825 failure layers.

Both slices retain all S0 and S1 gates, all 2,231 legacy cases, CLI/Python/artifact/
bootstrap/demo/AOT/vet gates, and an audit that no original-EVM/core/params/consensus
surface changed.

## Suggested future write sets

This is not authorization to implement. A parent freeze should keep one Solidity
owner and use only new versioned paths:

- runtime owner: `jvmevm/stock/s2/runtime/**`, expected components
  `S2Types.sol`, `S2MetadataPage.sol`, `S2ClassParser.sol`, `S2AnalyzeModule.sol`,
  `S2FrameStore.sol`, `S2ScalarStepModule.sol`, later `S2FrameStepModule.sol`,
  `S2Coordinator.sol`, build files and pinned artifacts;
- harness owner: `jvmevm/stock/s2/{s2.go,s2_test.go}` and only new
  `jvmevm/testdata/stock/s2/**`; read unchanged differential sources/cases;
- independent verifier: only new `jvmevm/stock/s2/validation_test.go` and README,
  with uniquely prefixed `stockS2Harness*`/`stockS2Verify*` helpers;
- parent only: Make targets, frozen plans, guides, integration, review fixes.

No worker edits S0/S1, the monolith, old cases/sources/budgets, core/vm/state/types,
consensus, params, precompiles, CLI, or differential tooling merely to implement
this proposal.

## Deferred semantics and limitations

S2 remains one ordinary class with scalar int values. It has no multi-class link,
statics or `<clinit>`, heap/object/array/reference, long/FP, handler search/unwind,
Throwable object/APIs, class libraries, String/main/JAR, monitors/threads, VFS,
clock/scheduler, network boundary, Minecraft startup, or connectivity. Its pending
fault record is a deliberate bridge to later unwind, not handler support. The
frame store is a path toward persistent execution state, not a reason to serialize
future heap/static/class graphs through the step ABI; those require separately
versioned paged arenas and dirty deltas.

## Evidence hashes and reproducibility

All prototype files below are ignored and may be regenerated; only this proposal
is tracked.

- cumulative differential `report.json` SHA-256
  `01a26970990d53a7a47e677d7c821b87fee42ff9e775ca37c44b719d256904f2`;
- `analyze_s2.py` SHA-256
  `e8a47f495350f76420c063affde785f52863c7f4e1e8976bb730f33fe189bb2d`;
- `s2-measurements.json` SHA-256
  `579b7569b9fdb5f18f0e04f08aee45a09ede5edde14aacd06dff685e5e77d9b3`;
- relevant `javap -verbose` output SHA-256
  `65c7f88ec9ba637e71f17e98dd5589e1007a5170683753d32b9b2cb19b876422`;
- `FrameStorePrototype.sol` SHA-256
  `45be33134e3a081f0e6125d63d27602f94a2bcefbc98f33a0936b439ed6a2357`;
- prototype artifact JSON SHA-256
  `6923ac7529007e348d77c26c80bbef7d3d0b31c0ab6fed9b11ddc69440c18c2d`;
- signed prototype driver `prototype.go` SHA-256
  `d29c1f03891d0aa325a4a6d0ffd5c49701edc054417153df5eff8b7aa652dfde`;
- prototype results JSON SHA-256
  `3ec2608ba6eb45706647c7b51ace331b59ea61e5837485bd746b30020376993b`.

Relevant reviewed source SHA-256 values at the base are S1 parser
`ade5d2b0bb4590c3c4772cfea53d2793f8c61d3cc44a2fc303a4042202afb4d5`,
S1 step module `3dca6a04810453aed95432c8e81cea3cecffaf079a6ab81f3da78938baed2224`,
S1 coordinator `fa5085399214518f5c1a0061c1f6cd1686e7b8ec5b781c049ff65a296144020f`,
S1 codec `2c9f4aadb08ee8852b254d8b82a915c279a49e19c0be32aaa5bcc6753919fbbc`,
and accepted monolith source
`ac7f1d1a6b4dd9899e2ca4288414d0498377df40d44f7289315723968670cbb8`.
