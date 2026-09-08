# Stock-EVM S1 architecture proposal: unchanged M1/M2 workloads

Status: **proposal and ignored prototypes only**, based on accepted Stock S0
`a6adae7`. Nothing here freezes S1, changes the accepted S0 ABI, or claims that
the 154,839-byte M5d-a runtime is ordinarily deployable. The only tracked output
of this work is this document. Bounded evidence is ignored under
`build/java-diff-stock-s1-architecture/`.

The next smallest real migration should be the existing, unchanged M1/M2 corpus:
82 manifest cases over five ordinary Java 8 classfiles and 39 distinct selected
methods. This is materially different from another `run()I` toy. It requires
entry names other than `run`, zero through four `int` arguments, six locals,
signed comparisons, conditional branches, `goto`, and real loops including
`sum(100)` and `fibonacci(30)`. The old manifest, source files, JVM outcomes,
monolith outcomes, and old per-invocation gas limits must remain unchanged. New
ordinary-deployment, parse, and resume gas is a separate Stock-S1 measurement.

S1 must remain a narrow single-class integer stage. It does **not** migrate calls,
class initialization, statics, heap objects or arrays, references, category-2
values, floating point, exceptions/handlers, class libraries, I/O, or Minecraft.
S0 and S1 counts must not be added to the accepted 2,231-case M5d-a count.

## Recommendation

Build new, versioned S1 contracts alongside S0 rather than rewriting S0:

1. retain the accepted `ArtifactPage` and exact `STOP || rawClass` format;
2. add a generic EVM parser which creates and attests an immutable parsed-class
   metadata page once per class;
3. select and commit a named method and its arguments in a new S1 coordinator;
4. execute up to 128 complete integer instructions per resume with a separate,
   hash-pinned step module; and
5. retain the 2,000,000 gas resume ceiling and initially retain the 800,000 gas
   commit reserve, subject to adversarial implementation measurements.

The parsed page is reusable by every selected entry and every argument vector for
that class. Parsing is setup work performed in EVM, not repeated in each resume.
The coordinator copies only one selected method's bounded record into immutable
configuration. A resume copies only the selected Code bytes (24 bytes worst in
the measured corpus, 256-byte proposed cap), not the whole class or method table.

The executor prototype makes the per-resume design look feasible: with 128-step
batches, `sum(100)` completed in seven resumes and 3,774,774 gas including three
ordinary deployments; the largest resume was 319,689 gas. `fibonacci(30)` used
three resumes and 2,744,168 aggregate gas; its largest resume was 393,036 gas.
Those are lower-bound architecture measurements, not acceptance: the prototype
uses host-supplied offsets/start bits and omits the production parser, metadata
provenance, digest, event, and full negative validation. A conforming S1 must
produce and validate all metadata in EVM and rerun the gas matrix before freeze.

## Measured unchanged workload

The exact differential command passed all 82 old cases against both the host JVM
and accepted monolith:

```sh
make java-build
PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py \
  --stage m2 --tier full \
  --artifacts build/java-diff-stock-s1-architecture/legacy-run
# selected=82 passed=82 failed=0
```

This used `javac 21.0.9 --release 8`, including the same default debug attributes
as `tools/java_diff.py`, and runtime SHA-256
`dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
The oversized monolith used 2,923,901 local-call gas for `sum(100)` and 1,536,536
for `fibonacci(30)`; these figures exclude ordinary deployment and transaction
continuation costs and therefore are not Stock-S1 budgets.

| Class | Raw bytes | `cp_count` | Declared / selected methods | SHA-256 |
|---|---:|---:|---:|---|
| `Comparisons` | 1,115 | 28 | 13 / 12 | `5c4a076b97e146ed73e14a5bea4f3722d3a18be284abd23bf0a56a5848d3cb9e` |
| `Constants` | 824 | 27 | 13 / 12 | `6b3473ae373a53d0c6a8a2a8df4b00b978a9c2db4890bacf14900717d60701a1` |
| `LocalsAndArithmetic` | 845 | 27 | 11 / 10 | `423ca06bab0adebb43e8d98df8438840fe4635bfa73e2e6c28b6397d1b195653` |
| `Loops` | 512 | 19 | 4 / 3 | `c9043994623a900a6c1f4ed096c9d1c23783842d2e5e1406646deea9db20fa38` |
| `M1Baseline` | 308 | 17 | 3 / 2 | `1e71a54ba434b943b44c8633a1fb9e4c52e4f435eaeffb5ebf47e546c49d0813` |

Measured selected-method maxima are Code 24 bytes, `max_stack=2`,
`max_locals=6`, four arguments, and an 18-byte entry name. The 39 descriptors
split as 8/17/10/2/2 methods with 0/1/2/3/4 `int` arguments. There are no
`CONSTANT_Integer` entries in these exact five outputs. Across distinct selected
methods there are 265 Code bytes, 205 static instruction starts, 18 branch
instructions, and two backward edges.

The exact selected opcode union is `iconst_m1..5`, `bipush`, `sipush`, `iload`,
`iload_0..3`, `istore`, `istore_0..3`, `iadd`, `isub`, `iinc`, `ifeq..ifle`,
`if_icmpeq..if_icmple`, `goto`, and `ireturn`. S1 should retain S0's `nop`,
`ldc`/`ldc_w` integer, `imul`, and `ineg` implementations too, rather than fork
the integer semantics merely because these exact outputs do not emit them.

A bounded host-only trace tool counted complete JVM instructions and agreed with
all 82 JVM/legacy values. The corpus executes 2,213 dynamic instructions in total.
The worst cases are:

| Case | Result | Instructions | Resumes at 16 / 64 / 128 |
|---|---:|---:|---:|
| `m2-sum-100` | 5,050 | 806 | 51 / 13 / 7 |
| `m2-fibonacci-30` | 832,040 | 368 | 23 / 6 / 3 |
| `m2-fibonacci-20` | 6,765 | 248 | 16 / 4 / 2 |
| `m2-sum-25` | 325 | 206 | 13 / 4 / 2 |

`sum` has an eight-instruction loop period. With either a 16- or 64-step budget,
many successful resumes end at exactly the same PC at which they began while
locals have advanced: the prototype observed 49 same-PC resumptions at budget 16
and 11 at budget 64 for `sum(100)`. Therefore S0's coordinator check
`after.pc == before.pc && after.done == before.done` is invalid for real loops and
must not appear in S1.

## Proposed execution boundary and profile

Host responsibilities remain opaque packaging only: compile trusted tests, send
unchanged raw class bytes, entry bytes and `int32` arguments, sign transactions,
and decode checkpoints. Parsing, member selection, descriptor checking,
predecode, branch validation, argument initialization, and execution occur in
ordinary deployed EVM code. The old monolith and host JVM are test oracles only;
neither is a fallback.

The proposed S1 profile is intentionally just large enough for all 82 cases while
retaining S0 integer operations:

- Java 8 classfile major 52/minor 0, unchanged payload at most 4,096 bytes,
  `cp_count` 1..512, selected Code 1..256 bytes;
- public ordinary class, direct `java/lang/Object` superclass, no interfaces,
  fields, `<clinit>`, handlers, native/abstract/synchronized selected root, or
  class-library execution;
- exact selected descriptor `(I...)I` with 0..4 arguments, `max_stack<=8`,
  `max_locals<=8`, entry 1..64 valid ordinary ASCII/MUTF-8 profile bytes;
- duplicate declared entry names remain ambiguous before descriptor selection,
  matching the accepted monolith rather than silently selecting an overload;
- the S0 opcodes plus signed integer branches `0x99..0xa4` and `goto 0xa7`;
- Java int cells remain exactly `(1<<64) | uint32(bits)`, with unchecked modulo
  2^32 arithmetic and signed branch comparisons; and
- uninitialized locals are canonical zero and loads/`iinc` require their bit.

Unused methods and nested/class attributes are structurally bounded and skipped.
An unsupported unused method is recorded as ineligible, not executed and not a
reason to fabricate success. Selecting it fails explicitly. No broader classfile
verification claim follows from this profile.

## Parse once: immutable reusable metadata

### Contracts

- **`ArtifactPage`**: reuse the accepted S0 artifact unchanged. The actual raw
  class is still checked byte-for-byte in tests.
- **`S1ClassParser`**: generic append-only parser/factory. `registerClass` reads
  the page with `EXTCODECOPY`, validates exact page and payload hashes, scans the
  constant pool and all members, derives method records, predecodes eligible
  methods, then uses ordinary internal `CREATE` to deploy `STOP || metadata`.
  It records `(classId => metadataPage, metadataHash)` once; no update/delete API.
- **`S1MetadataPage`**: constructor-only generic data page. Its runtime is not a
  class-specific executable and has no callable mutation path.
- **`S1StepModule`**: stateless generic executor. It receives the committed
  selected record and machine, verifies code hashes, copies only selected Code,
  and executes a bounded number of whole instructions.
- **`S1Coordinator`**: persistent schema-2 instance. Its constructor verifies the
  parser-issued metadata record, selects the entry in EVM, validates descriptor
  and argument count, initializes locals, and commits all roots and module hashes.

A parser/module address plus self-reported hash is only a configuration
commitment, not an attestation. Acceptance must compare their deployed bytes to
the pinned compiler artifacts. Every coordinator pins parser, metadata, module,
and raw-page addresses and code hashes and rechecks the relevant hashes.

### Suggested canonical metadata format

Use a versioned binary page, not Solidity's dynamic storage graph. Payload-relative
class offsets are retained; the raw page adds one byte when `EXTCODECOPY` is used.
Schema 2 is six 32-byte header words followed by four 32-byte words per declared
method and then sorted 8-byte integer-literal records:

1. magic/schema, class length, CP count, declared method count, literal count;
2. raw page address and validated class flags;
3. raw page code hash;
4. raw payload hash;
5. declared class-name hash;
6. literal-table root;
7. per method: entry-name hash;
8. descriptor hash;
9. packed declared index/access/eligibility or exact error/code offset/code
   length/max stack/max locals/argument count/literal base and count;
10. 256-bit instruction-start bitmap.

Literal records are `(methodIndex:u16, pc:u16, bits:u32)`, sorted by method and
PC. This preserves S0's accepted CP fix: CP tags/indices/offsets are scanned and
validated once by the parser; execution never rescans a 512-entry CP at `ldc`.
A bounded binary search over the selected literal slice returns already validated
bits. The exact 82-case outputs have no literal records.

With that deliberately uncompressed format, the actual five class metadata
payloads would be 1,856, 1,856, 1,600, 704, and 576 bytes (6,592 total), plus one
STOP byte per page. The largest is only 1,857 runtime bytes. Code-deposit charge
for all five pages is 1,319,400 gas before constructors/transactions; five
append-only two-slot parser records add a nominal 200,000 zero-to-nonzero SSTORE
gas before cold-access and transaction overhead. These are protocol arithmetic,
not a measured parser implementation. The parser transaction must be measured;
if it cannot fit its proposed 8M cap, use explicit parse cursors, not host metadata
or a raised protocol limit.

The parser should retain S0's exact `_page`, CP two-slot handling, outer-length,
Code-boundary and nested-attribute checks. Method loading/descriptor semantics
should be ported from accepted `_loadRoot`, `_descriptor`, and `_isExactIntRoot`.
Instruction widths, start maps, and edge checking should be ported from accepted
`_predecode`, `_instructionWidth`, `_requireDecodedTarget`, and signed target
helpers. This is reuse of reviewed semantics, not a source-level promise that
private monolith memory structs can be split mechanically.

## Stable program and machine commitments

Suggested identifiers are domain-separated and include explicit versions:

```text
classId = keccak256("JVMEVM:S1:CLASS", uint32(2), parserCodeHash,
                    page, pageCodeHash, payloadHash, metadataHash)
programId = keccak256("JVMEVM:S1:PROGRAM", uint32(2), classId,
                      methodIndex, entryHash, descriptorHash, moduleCodeHash)
argsHash = keccak256(abi.encode(int32[] args))
inputRoot = keccak256("JVMEVM:S1:INPUT", programId, argsHash, maxTotalSteps)
stateDigest = keccak256(abi.encode(uint32(2), inputRoot, parserCodeHash,
                                  moduleCodeHash, machine, epoch, totalSteps))
```

The exact constructor-supplied entry bytes are hashed; the EVM compares them to
all declared names, rejects ambiguity, and verifies the selected record. Arguments
are ABI-canonical `int32`, hash-committed, copied into locals 0..N-1 as tagged
cells, and those initialized bits persist through every resume. Neither entry nor
arguments can change after construction.

Suggested schema-2 machine:

```solidity
struct MachineV2 {
    uint32 pc;          // selected Code-relative instruction start
    uint8 sp;
    uint8 initialized; // low maxLocals bits
    uint8 lifecycle;   // 0 RUNNABLE, 1 RETURNED, 2 STEP_LIMIT
    uint256[8] stack;
    uint256[8] locals;
    int32 result;       // zero unless RETURNED
}
```

All inactive stack cells and uninitialized/out-of-range locals are zero. Active
cells are exactly tagged ints. A returned machine has `sp==0`. `STEP_LIMIT` is an
explicit harness/protocol outcome, never a Java exception, OOG, or value.

## API proposed for a parent freeze

```solidity
S1ClassParser.registerClass(
    address page, bytes32 expectedPageHash, bytes32 expectedPayloadHash
) external returns (
    bytes32 classId, address metadataPage, bytes32 metadataHash,
    uint16 declaredMethods
);

S1ClassParser.classRecord(bytes32 classId)
    external view returns (address metadataPage, bytes32 metadataHash);

S1StepModule.step(
    ProgramContext calldata program, MachineV2 calldata beforeState,
    uint16 budget
) external view returns (MachineV2 memory afterState, uint16 executed);

S1Coordinator.resume(
    uint64 expectedEpoch, uint16 maxJvmSteps, uint8 maxDirtyWords
) external returns (
    uint64 newEpoch, uint8 lifecycle, int32 result,
    uint16 executed, uint8 dirtyWords
);

S1Coordinator.checkpoint() external view returns (
    uint32 schema, bytes32 classId, bytes32 programId, bytes32 inputRoot,
    uint64 epoch, uint64 totalSteps, bytes32 stateDigest, MachineV2 memory machine
);
```

`ProgramContext` is fixed-width: raw page/address hashes, payload-relative code
offset/length, max stack/locals, instruction-start bitmap, selected literal
base/count, method index, and program ID. The coordinator supplies it from pinned
immutables; callers never supply PC, metadata, state, entry, arguments, or module
to `resume`.

Use one exact `CheckpointV2` event with indexed epoch and program ID plus total
steps, PC, SP, lifecycle, result, executed, dirty words and state digest. No event
or state change survives a failed transaction.

Suggested errors, to be frozen with exact mutation tests rather than opaque
panics:

- `S1ClassError(code,offset)`: 1 truncation/boundary, 2 magic/version, 3 CP/tag/
  index/two-slot, 4 class profile/name/super/field/interface/clinit, 5 method or
  attribute count/cap, 6 metadata creation/duplicate;
- `S1MethodError(code,index)`: 1 missing, 2 ambiguous, 3 access, 4 descriptor,
  5 Code count/caps/handlers, 6 unsupported selected method, 7 argument mismatch;
- `S1BytecodeError(code,pc)`: retain S0 meanings for truncation, underflow,
  return shape, unsupported, fallthrough, local range, stack capacity,
  uninitialized local, non-start PC, and malformed tagged state; add 15 invalid
  branch target and 16 missing/mismatched cached literal;
- `S1ControlError(code)`: terminal, component/hash/provenance, stale epoch,
  budget range, reserve, dirty cap, invalid module result, aggregate step limit.

## Continuation, loops, and safepoints

A successful resume commits only after one or more complete JVM instructions.
For this S1 opcode set there are no partial Java-visible operations, so the only
normal safepoints are terminal return, exhaustion of the caller's bounded step
budget, or the committed aggregate step limit. A branch itself is not a pause.
Future calls, parsing cursors, allocation, and exception search require explicit
phase/cursor states; they must not reuse this claim automatically.

Predecode validates every selected instruction, including unreachable bytes:
width, local and CP operands, and a bitmap of starts. A second pass checks every
conditional and `goto` signed-16 target is within Code and points to a start. The
step module requires the incoming PC and every resulting PC to be starts and
rechecks branch targets defensively.

Progress is `executed in 1..budget`, an incremented `totalSteps`, epoch, and digest.
It is **not** a changed PC or changed Java cells. A valid `goto 0` or periodic loop
may return the identical machine after a batch. Such execution remains finite
because the coordinator commits `maxTotalSteps` (proposed 1..4,096; use 1,024 for
the 82-case gate), reduces a batch to the remaining allowance, and transitions
to `STEP_LIMIT` if no `ireturn` occurs. This permits `sum(100)`'s 806 steps but
terminates a genuine infinite loop deterministically.

Keep atomicity and gas behavior from S0: reserve gas before the module call,
recheck at the actual call boundary before stipend subtraction, bubble module
reverts/OOG without relabelling them Java outcomes, validate/canonicalize output,
check dirty count before any committed write, then write machine/header/digest
and emit once. This specifically retains fixes `861c8c2` (post-encoding reserve
recheck) and `c62cec4` (reuse validated CP data), plus Java int32 behavior from S0.

The conservative dirty count remains within 32: three committed header words,
PC/SP/initialized/lifecycle/result logical words, and sixteen stack/local cells
is at most 24. Actual changed storage slots must not exceed the reported count.
Do not assume packing; verify compiler storage layout and an all-dirty adversarial
transition.

## Gas and size evidence

The ignored cached-executor prototype was compiled with pinned solc 0.8.30,
optimizer 200, via IR, Cancun target, and metadata disabled:

| Prototype artifact | Init bytes | Runtime bytes | Runtime SHA-256 |
|---|---:|---:|---|
| dynamic `PPage` constructor/template | 288 | 3 template; 513 actual `Loops` page | `0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438` (template) |
| `PCachedStep` | 3,920 | 3,894 | `29bc03182b4eefb56769418b3ac2e4b364a26c451021ffa2984d301dc5d8585b` |
| `PCoordinator` | 4,138 | 3,276 | `eb156cf68cc41574f266e84a5a1cd1c037df221a22ef72edddbe12648397ef32` |

It used signed legacy transactions, sender recovery, `TransactionToMessage`, and
`core.ApplyMessage` with nonce/transaction checks enabled under chain ID 1337
all-dev rules including Osaka. Only a test EOA balance was initialized. All code
used ordinary CREATE; no `SetCode`, `SetState`, listener, EULA change, downloaded
Java, core limit, opcode, gas, consensus, precompile, or global change was used.

| Workload / step budget | Resumes | Resume gas range | Same-PC nonterminal resumes | Positive gas including page/module/coordinator CREATE |
|---|---:|---:|---:|---:|
| `sum(100)` / 16 | 51 | 115,519..154,349 | 49 | 7,818,240 |
| `sum(100)` / 64 | 13 | 168,520..225,209 | 11 | 4,326,168 |
| `sum(100)` / 128 | 7 | 168,520..319,689 | 5 | 3,774,774 |
| `fibonacci(30)` / 64 | 6 | 145,580..261,975 | 0 | 2,991,117 |
| `fibonacci(30)` / 128 | 3 | 232,776..393,036 | 0 | 2,744,168 |

The prototype's module ABI copies 932 bytes in and 704 bytes out per static call;
the external resume calldata is 100 bytes. Its machine expands S0 from four to
eight persistent locals. Only selected Code is copied from the page per resume,
24 bytes worst for this corpus and at most 256 by profile. Those copying costs are
included in the measured resume gas.

These measurements leave substantial room below 2M even while reserving 800k,
and a 128-step budget reduces the worst workload to seven resumes. Thus both S0
ceilings are plausible for S1; they are **not yet proven** for the real parser,
provenance checks, digest/event, exact module-result decoder, or adversarial dirty
state. Do not increase either limit during implementation. A failure to fit is a
freeze blocker requiring a measured design change.

Provisional separate S1 ceilings:

- parser/module/coordinator CREATE and `registerClass`: each <=8,000,000 gas;
- resume <=2,000,000 gas with 800,000 gas commit reserve;
- `maxJvmSteps` 1..128, `maxDirtyWords` 1..32, committed total steps <=4,096;
- each executable runtime <=12 KiB except parser <=16 KiB, each initcode <=24 KiB;
- metadata runtime <=8 KiB, raw page unchanged <=4,097 bytes including STOP;
- canonical 82-case runs use `maxTotalSteps=1,024`; at budget 128, at most seven
  resumes, and <=19 successful transactions including isolated deployments and
  class registration;
- each isolated case <=30M successful aggregate gas, reported separately from
  failures and from legacy manifest `gas_limit`.

All remain below EIP-170/EIP-3860 and Osaka's 16,777,216 max transaction gas; the
test header remains 30M block gas. Internal metadata CREATE does not evade any
limit and its gas belongs to `registerClass`.

## Acceptance tests and gates to freeze later

A parent freeze should require all of the following without changing old inputs:

1. **82 real cases**: compile the existing five source files with the existing
   command, require the hashes above for the pinned environment, and pass every
   existing ID/result through JVM, legacy monolith, and actual Stock S1. Report
   old monolith gas and Stock deploy/register/resume/aggregate gas separately.
2. **Reuse**: deploy each raw page and parsed metadata page once, then use that
   metadata for every selected method and argument vector in the class. Verify
   39 program IDs, argument commitments, and that changing entry/args changes the
   expected roots without changing class metadata.
3. **Batch equivalence**: all 82 cases complete at budgets 64 and 128; every
   non-loop case also completes at 1, 7, and 16. Complete the long loop cases at
   64/128 and compare bounded budget-1/7/16 prefixes instruction-for-instruction,
   without pretending 806 one-step transactions meet the <=19-transaction case
   ceiling. Values and canonical terminal cells match Java (epoch/digest differ
   by batching). Compare independent traces at every checkpoint for trusted inputs.
4. **Real loop progress**: require successful same-PC checkpoints for `sum(100)`
   in a bounded budget-16 prefix and its complete budget-64 run; separately run a
   valid self-loop until exact `STEP_LIMIT`.
   Reject non-start, out-of-range, middle-of-immediate, forward and backward bad
   targets, including unreachable branches.
5. **Entry/args**: missing/duplicate names, unsupported and malformed methods,
   visibility/static/descriptor errors, 0..4 argument edges, wrong count,
   int32 min/max, six-local initialization persistence, and uninitialized reads.
6. **Parser/cache**: malformed CP including last-slot long/double, attribute and
   Code boundaries, stale/wrong parser record, forged metadata page, page/hash
   mismatch, literal CP kind/index/value, and a retained CP512/Code256 boundary.
   The accepted S0 CP512 final-resume regression remains green unchanged.
7. **Atomicity/gas**: stale epoch, terminal, dirty cap before/after progress,
   exact reserve thresholds, actual module OOG, aggregate limit, all-dirty storage,
   no logs/state on failure, normal EOA nonce/gas effects, and retry from the same
   checkpoint. No Solidity panic may replace a specified error.
8. **Two transaction paths**: signed in-process simulated-chain receipts and
   direct signed-transaction ApplyMessage replay, replayed twice with explicit
   deterministic contexts and matching checkpoints, gas, addresses/code hashes,
   and state roots where contexts are actually identical. No listeners.
9. **Stock limits/artifacts**: reproducible pinned artifacts and source hashes,
   deployed byte equality/codehash/immutable references, plus ordinary EIP-170,
   EIP-3860 and Osaka EIP-7825 negatives. Audit no changes under `core/vm`,
   `core/state`, `core/types`, `consensus`, or `params` from the accepted base.
10. **Regression separation**: existing `java-stock-check/test/demo`, all legacy
    2,231 cases and existing Go/CLI/Python/artifact/bootstrap/demo/AOT/vet gates
    remain unchanged and green. S1 gets new, separately named targets and counts.

## Suggested implementation write set

This is a proposal for a future parent freeze, not authorization from this worker:

- one Solidity owner only:
  `jvmevm/stock/s1/runtime/{S1Types.sol,S1MetadataPage.sol,S1ClassParser.sol,S1StepModule.sol,S1Coordinator.sol,build.js,package.json,package-lock.json,artifacts/*.json,README.md}`;
- harness owner only:
  `jvmevm/stock/s1/{s1.go,s1_test.go}`; read existing
  `jvmevm/testdata/differential/{cases.json,M1Baseline.java,Constants.java,LocalsAndArithmetic.java,Comparisons.java,Loops.java,OracleMain.java}` without editing them;
- independent verifier only: `jvmevm/stock/s1/validation_test.go` with helper
  prefixes such as `stockS1Harness*` and `stockS1Verify*`;
- parent only: Makefile gates, frozen S1 plan and status docs.

No S1 worker should edit S0 Solidity/Go/tests/fixtures, the monolith, historical
fixtures, CLI, differential tooling, consensus/core/params, or old plans.

## Path after S1

S1 deliberately establishes a reusable class-metadata commitment and a finite
continuation rule, not a template that can be copied blindly for M5d-a. The next
migration must be selected by actual workload and dependency measurements:

- static calls require persistent frame records, method/class identities,
  argument/return transfer, recursion ceilings, and initialization ordering;
- statics and `<clinit>` require persistent initialized/in-progress/failed class
  cells and cached failure identity;
- objects/arrays require paged heap chunks, monotonically committed handles,
  quotas, reference typing, and bounded dirty-page commits;
- exceptions require a pending fault plus resumable ordered handler search and
  unwind phases, without converting EVM OOG into Java OOM;
- long/FP require category rules and the accepted software IEEE helpers in
  independently deployable modules; and
- libraries/Minecraft require explicit bootstrap classes, VFS/resources,
  deterministic time/scheduling and an external I/O boundary. No host Java or
  server logic may fill those gaps.

Those stages may introduce schema 3+ coordinators or versioned state-page roots.
They must consume schema-2 metadata through explicit adapters or rebuild it in EVM;
they must not mutate S0/S1 history or assume private monolith memory graphs can be
ABI-copied across contracts.

## Evidence and caveats

Key ignored evidence hashes:

- `m1m2-measurements.json` SHA-256
  `34902afc198dfe76e564f6df88906c018a897f4f400f183e402daf0dc1803b63`;
- `analyze_m1m2.py` SHA-256
  `002d168b3a5cb0cba8cc082737a50cae769216abde29bbe0015a4ca3adc7dcc0`;
- `m1m2.javap.txt` SHA-256
  `9923601dc27409f2622be871b9c160a9407f902f0462b61c1bc401baa6c276cb`;
- legacy 82-case `report.json` SHA-256
  `83c9255562b2d45ddeacff270ae7b074ee26c3437fa285b5e7567de9828bae18`;
- `S1CachedPrototype.sol` SHA-256
  `48b763ed33e0402b82e7a4e94e8d764f61d4415d7e2b89e0e6cda96c690c7a4c`;
- `prototype.go` SHA-256
  `bdb2952058d81372920880793fcb491e1ce2a28a6c2f87295cb4505025be6e08`;
- `prototype.log` SHA-256
  `ca7f511c468bb3bcc23948f5169a98160623c0ad613b2742cca33d5b0e1e49ee`;
- `compile.log` SHA-256
  `f80c844034a08a5240a68e9c8e2db6037e569b4bcc10ac8e94245a78165b5eaf`.

The host analyzer and host-supplied prototype metadata are test/proposal tools
only. They are not permissible production parsing or execution. The prototype
runs only two real methods, not all 82 on Stock S1, and contains no production
parser. Its evidence supports the selected-Code/cached-state performance shape
and exposes the same-PC issue; it does not prove parser correctness, metadata
provenance, adversarial rollback, full ABI, final artifact sizes, or independent
client behavior. Consequently this document recommends the architecture and a
freeze matrix, but does **not** recommend accepting S1 yet.
