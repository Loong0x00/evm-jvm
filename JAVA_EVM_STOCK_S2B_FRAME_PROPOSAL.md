# Stock S2b frame preflight: compact persistent integer frames

Status: **proposal and ignored storage prototype only**, measured at base
`3098849993486c7d016da947ebd7836480a3fa90` (`3098849`). This document does not
freeze S2b. Parent final gates for the frozen 201-row S2a slice are still in
progress; this is not S2a acceptance. The only prototype evidence is under the
ignored directory `build/java-diff-stock-s2b-frames/`.

No production runtime, harness, test, plan, fixture, Make target, legacy path,
EVM/core/state/types/consensus/params/gas rule, protocol limit, precompile, global
configuration, or peer worktree was changed. There was no `SetCode`, `SetState`,
genesis executable/storage injection, push, downloaded Java/Minecraft execution,
EULA acceptance, listener, or worker spawning. S0, S1, S2a, and the oversized
monolith remain separate and unchanged. There is no live-upgrade assumption from
an S2a coordinator, parser, class ID, program ID, or checkpoint.

## Recommendation

Use a **new S2b schema and owner-only frame store with reversible compact-int32
physical storage**, and provision a maximum of **four touched frame identities per
resume**. Permit a caller to request a smaller 2-frame slice. Do not retain the old
16-frame/192-dirty-word/800,000-reserve combination: the earlier 16-child lower
bound was about 3.8M gas, and 192 cold zero-to-nonzero `SSTORE`s alone exceed 4.2M.

The measured compact design uses five physical storage words per persistent frame,
versus 19 for the uncompressed control. A conservative four-frame compact commit
therefore reserves at most 20 frame words plus six coordinator words, not 192 cold
frame writes. One `invokestatic` or one return needs at most two persistent frame
identities, so either the 2- or 4-frame slice can stop before an instruction rather
than partially committing it. Four frames substantially reduce transaction count
and aggregate gas in the storage traces while retaining comfortable prototype
headroom under the existing 2M resume and 800k commit-reserve candidates.

This is a recommendation for a production prototype, **not a freeze**. The compact
prototype's densest four-frame transaction used 589,987 signed gas; its measured
store-apply-and-root portion was 401,528. Every compact transaction was actually
submitted with a 2,000,000 gas limit and succeeded. Thus no new project gas budget
is recommended now. A real parser, call resolver, semantic step module, complete
delta validator, provenance checks, and exact event/result ABI must be measured
before the parent decides whether 2M/800k remains sufficient. If that integrated
path fails, first reduce the instruction batch or touched slice; do not alter Osaka,
EIP-170/EIP-3860/EIP-7825, opcode costs, block gas, or consensus rules.

## Exact workload boundary for a future freeze

S2b would retain all 201 unchanged S2a rows and add exactly the 67 unchanged M3a
rows, for 268 cumulative stock rows: 261 integer values, six terminal
`ArithmeticException`s, and one terminal `StackOverflowError`. The additions are
62 values, four propagated arithmetic faults, and one SOE. Existing inventory
measurements remain 4,060 new terminal bytecodes, 512 dynamic calls, 6,702
cumulative bytecodes, and these required stress cases:

- `recursiveFibonacci(10)`: value 55, 1,592 bytecodes, 177 calls, depth 11;
- mutual recursion: successful depth 33;
- unbounded recursion: 510 bytecodes, 128 attempted calls, 128 active frames,
  with the attempted 129th active frame producing kind-2 SOE.

A future freeze must execute all 67 actual unchanged classfile rows in EVM and
retain the 201 S2a gates. The storage traces measured here merely use those known
step/call/depth totals. They do not parse classfiles or execute Java bytecode and
must not be counted as guest outcomes.

S2b metadata must be newly versioned because frozen S2a metadata intentionally has
no call records and only public `(I{0..4})I` roots. The S2b parser/analyzer must
derive in EVM, from unchanged raw class pages:

- exact same-class `CONSTANT_Methodref` owner/name/descriptor resolution;
- stable method IDs (recommended: the bounded declared-method index);
- public integer-return roots with up to six integer arguments;
- internal static public/protected/package/private methods with `(I{0..6})I` or
  `(I{0..6})V`, including overloads and zero-argument/void helpers;
- call records binding caller method, invoke PC, CP index, target method, argument
  count, and `I`/`V` return kind; and
- flow effects for `invokestatic`, `ireturn`, `return`, and `pop`, in addition to
  the complete S2a integer set.

External owners, interface calls, references, category-2 values, handlers,
constructors, fields, `<clinit>`, synchronized/native/abstract targets, or malformed
and ambiguous exact targets remain explicit unsupported/validation errors, never
Java faults. Private helpers, void returns, discarded integer results, six-argument
order, expression prefixes, caller-local isolation, overloads, direct/mutual
recursion, and callee arithmetic faults are mandatory acceptance cases.

## Recommended persistent representation

### Canonical semantic frame

The module/delta boundary should use a canonical integer-only frame:

```text
frameId:u64, parentFrameId:u64, methodId:u16,
invokePC:u32, pc:u32, sp:u8, initialized:u8,
parentRoot:bytes32, frameRoot:bytes32,
stack[8]:tagged-int-or-zero, locals[8]:tagged-int-or-zero
```

`invokePC` is the caller's actual call-opcode PC. The root frame has ID 1,
`parentFrameId=0`, zero `parentRoot`, and no fabricated invoke PC. `nextFrameId`
starts at 2, advances monotonically, never wraps, and IDs are never reused after a
return/clear. `maxTotalSteps<=4096` bounds allocations; active depth is separately
bounded at 128 including the root.

Every active stack cell and initialized local must be exactly
`(1<<64) | uint32(intBits)`. Every inactive stack cell and uninitialized local is
zero. **Before compact storage**, the module reply decoder, coordinator delta
validator, and store writer must all reject a missing tag, extra high bits,
nonzero inactive cell, out-of-range `sp`, or initialized bit outside the method's
`maxLocals`. The prototype validates the global stack8/locals8 envelope; production
must additionally validate each method's metadata bounds.

### Reversible compact-int32 storage

For this integer-only stage, store each persistent frame in exactly five physical
mapping words:

1. packed ID, parent ID, method ID, invoke PC, PC, SP, and initialized mask;
2. `parentRoot`;
3. `frameRoot`;
4. eight 32-bit stack payloads;
5. eight 32-bit local payloads.

The SP and initialized mask preserve occupancy, so reads reconstruct each active or
initialized cell with the canonical int tag and each other cell as zero. The
prototype checked byte-for-byte that both compact and uncompressed getters return
the same canonical tagged ABI frame. Compaction is reversible only because S2b's
entire supported value domain is int32. Long, float, double, reference, return
address, uninitialized-object, category-2, or any future tag is **not supported by
this layout**; adding one requires a separately versioned storage schema and new
measurements, not truncation into 32 bits.

The uncompressed control uses one packed metadata word, two roots, and 16 full cell
words: 19 physical words. It fits 2M for the measured four-frame prototype, but its
dense four-frame store operation alone used 1,214,657 gas, already exceeding the
800k reserve. It is therefore not the safe default.

## Hash-linked active stack and state commitments

Recommended frame hash:

```text
frameRoot = keccak256(abi.encode(
  frameDomain, frameId, parentFrameId, methodId, invokePC, pc, sp,
  initialized, parentRoot, canonicalStack8, canonicalLocals8
))
```

A child stores the caller's post-invoke `frameRoot` as `parentRoot`. The current
frame's root is the coordinator's `activeRoot`. Calls update/freeze the caller
before linking the child; returns verify the link, clear the child, update the
parent, and make the parent's new root active. No resume ABI includes 128 frames,
a whole heap, class CP, static table, or monolith arena.

These hashes commit a hash-linked **active Java stack**, not all Ethereum storage.
The coordinator `stateDigest` should commit the prior digest, input/program and
component identities, epoch/step/header transition, active root, and canonical
delta hash. It is a transition-history commitment, not an independently proven
sparse-Merkle state root. The authoritative global state is the Ethereum state
trie root produced from all touched accounts/storage; it also includes unrelated
EOA nonce/balance/gas effects. Accordingly, the rollback probe precisely compares
the coordinator checkpoint and frame getter and requires no logs; it does not
claim the global trie root is unchanged after a failed signed transaction.

## Bounded deltas and atomic instructions

A production reply should contain a fixed header transition plus a sorted, unique
array of at most four frame identities. Each persistent delta carries operation,
frame ID, exact expected old root, and a canonical final frame for create/update.
The operations are:

- `UPDATE`: existing ID and exact old root to canonical new frame;
- `CREATE`: exactly the next unconsumed ID, absent old root, canonical new frame;
- `DELETE`: existing ID and exact old root to all-zero storage;
- `EPHEMERAL`: exactly the next unconsumed ID for a frame both created and returned
  within this batch, absent before and after.

An ephemeral frame consumes its ID but leaves no mapping entry. Production should
include a bounded creation/terminal summary hash (ID, parent/method/invoke identity,
creation root and terminal root) in the delta-history commitment so omission from
persistent storage does not erase transition provenance. Nested ephemeral records
must be ordered and link consistently. The ignored prototype measures only the ID
record for this case, so its ephemeral gas is intentionally a lower bound.

Before any write, the coordinator must validate ABI length/canonical narrow words,
component/store owner and code hashes, stale epoch, sorted uniqueness, old roots,
operation legality, sequential new/ephemeral IDs, frame/count/physical-word caps,
new links, no references to deleted IDs, final current/depth/next/root, executed
count, lifecycle/fault shape, and step cap. The store is deployed by ordinary
internal CREATE with the coordinator as immutable sole writer; direct EOA commit
failed in the measured probe.

The module must stop at the last safepoint before an instruction whose complete
result would exceed the frame/delta/word cap. `invokestatic`, `ireturn`, and
`return` are each one indivisible JVM instruction and increment the bytecode count
exactly once. A call validates the Methodref, target, argument tags, depth, and all
caps before popping anything; it preserves the caller expression prefix, advances
the caller PC, copies arguments in declaration order to independent child locals,
starts an empty child stack, sets `invokePC`, and changes current frame. A return
validates shape and link before clearing the child and pushing one int or no value
onto the untouched parent prefix. There is no partial call, partial return, reused
ID, or dangling parent link.

A four-frame maximum conservatively means 20 compact physical frame words plus six
coordinator words. Keep separate counters for touched frame identities, physical
store words, and semantic fields; do not call 26 physical words “26 logical Java
words.” A single call/return is guaranteed to fit a 2-frame slice. Same-PC loops
remain valid progress because `executed>=1` and total steps/epoch advance.

## Terminal fault and cap rules

Retain S2a lifecycle values: 0 RUNNABLE, 1 RETURNED, 2 STEP_LIMIT, 3 JAVA_FAULT.
Fault fields are exactly kind, throwing frame ID, method ID, and opcode PC.

- Kind 1 ArithmeticException validates operands and tags, counts the faulting
  `idiv`/`irem` once, and preserves the throwing frame at the pre-instruction PC
  with operands, locals, prefix, and active call chain intact. A callee fault is
  terminal in S2b; no fake unwind or handler search occurs.
- Kind 2 StackOverflowError occurs when an `invokestatic` attempts to exceed 128
  active frames. Count that call opcode once, retain the caller at its pre-invoke
  PC and state, do not pop arguments, do not allocate/consume a frame ID, and do
  not create a child or dangling link.

Earlier complete instructions in the same resume may commit. The exact faulting or
return instruction wins if it lands exactly on `maxTotalSteps`; otherwise a still
runnable state reaching the cap becomes STEP_LIMIT. If the cap is exhausted before
a future divide/call is attempted, the outcome is STEP_LIMIT, not predicted
ArithmeticException/SOE. Dirty-slice exhaustion is a runnable checkpoint, not a
Java outcome. Terminal resume rejects. EVM OOG/revert/malformed response remains an
EVM failure and must never decode as kind 1 or 2.

## Measured prototype

The Solidity prototype is storage-only. Its echo module round-trips a realistic
full canonical-frame delta ABI through bounded `STATICCALL`; the coordinator
checks counts, sorted IDs, old roots, links, lifecycle, hashes, and caps, then calls
an owner-only store and commits header/digest/event atomically. It does not parse,
resolve, or execute Java. The trusted Go driver generates storage transitions and
known workload totals only; those inputs are TEST lower bounds, not production
inputs or conformance evidence.

Build settings were pinned solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer
200, via IR, Cancun, metadata disabled. All deployment and calls used signed legacy
transactions, recovered sender, `TransactionToMessage`, and `core.ApplyMessage`
with nonce and transaction checks enabled, chain ID 1337, Osaka-active
`AllDevChainProtocolChanges`, a 30M block limit, ordinary external/internal CREATE,
and genesis TEST EOA funding only.

| Component | Init / runtime bytes | Init SHA-256 | Runtime SHA-256 | Runtime keccak256 |
|---|---:|---|---|---|
| `DeltaEchoPrototype` | 1,455 / 1,429 | `ca62d43fc1cea25d3afdfa19b7f5b12ec112775ce66e181d286b0087c40106e7` | `ec6e5db4ffc49451c505f7c43f5ae0d706f025a15f8aa0952fc4c2d0496ab5c1` | `e4181713c8bcbfccdecde9779ca08895a91d744bfda6db54bfb4d02053f9c7bc` |
| `FrameStorePrototype` | 4,645 / 4,422 | `743f51385fe516f662954347174037d6d5f25ed1d1cb90f82c0815731c26b75a` | `fb5cb4e8def1867f0b70197e66b67c51df4b4422ab8a815a7a061a58d052af6c` | `e98848ebf600d0801f23aa1e2f2394bf35363dc0d2dfe5039eaf2fb79cdd83cf` |
| `FrameCoordinatorPrototype` | 14,423 / 8,996 | `d2c26ccd7c201453092ed6adeee0cafd71c970683f456f22afb36c56e1c19dd4` | `e792c31699e7fe4bf4a07b20836b43157eb16107515ccb7d8a9bda85967362a1` | `9d519936570abfbd0196f19dc7984c1d85f2a95d2e56d292dfa9181185efe8a8` |

Echo CREATE used 362,335 gas. Coordinator CREATE, including ordinary internal
store CREATE, used 3,044,234 compact / 3,044,222 uncompressed. All sizes are below
unchanged EIP-170/EIP-3860 and the prior 12/24 KiB project component targets.

### Cold writes, clearing, compact comparison, and rollback

`store gas` below is instrumented from immediately before owner-store commit to
after final active-root read. Signed gas includes transaction calldata/intrinsic,
echo `STATICCALL` ABI encode/decode, validation, storage/header/digest, and event.
The dense four-frame push uses six active stack cells and six initialized locals in
each frame, matching the measured M3a maxima rather than a sparse toy frame.

| Operation | Compact signed / store gas | Uncompressed signed / store gas |
|---|---:|---:|
| root, six locals, cold zero→nonzero | 233,167 / 82,737 | 363,564 / 213,096 |
| mutate current | 146,027 / 48,665 | 176,783 / 79,370 |
| two-frame call (caller + new child) | 255,954 / 128,329 | 318,428 / 190,714 |
| two-frame return/clear | 154,920 / 54,805 | 233,937 / 134,116 |
| dense four-frame push | **589,987 / 401,528** | **1,403,281 / 1,214,657** |
| four-frame return/clear | 228,256 / 109,081 | 407,305 / 332,766 |
| parent update + three ephemeral IDs | 192,135 / 37,392 | 222,969 / 68,136 |

No operation first failed at the actual 2M transaction limit. The 800k reserve is
larger than the entire densest compact prototype transaction, but smaller than the
uncompressed store operation alone. The compact result supports retaining 800k as
a candidate; it does not prove the integrated semantic validator fits it.

A forced revert after owner-store application consumed 145,984 compact / 176,740
uncompressed gas, emitted zero logs, and left the sampled checkpoint and current
frame ABI exactly unchanged. Separate probes rejected an EOA calling store commit,
rejected a live cell lacking `INT_TAG`, emitted no logs, and left the checkpoint
unchanged. Compact readback exactly reconstructed the canonical tagged frame.

### Bounded 2- versus 4-frame storage traces

Transaction counts include root initialization and terminal header commit. Every
transaction below was submitted with a 2M limit; none needed the 8M retry path.
“Store max” excludes parser/resolver/Java semantics as described above.

| Layout / slice | TEST storage trace | tx | aggregate gas | max signed | max store |
|---|---|---:|---:|---:|---:|
| compact / 2 | Fibonacci(10) totals | 267 | 52,375,043 | 278,342 | 147,053 |
| compact / 4 | Fibonacci(10) totals | 91 | 28,637,595 | 575,510 | 386,509 |
| uncompressed / 2 | Fibonacci(10) totals | 267 | 66,264,435 | 341,659 | 210,268 |
| uncompressed / 4 | Fibonacci(10) totals | 91 | 36,914,201 | 701,971 | 512,792 |
| compact / 2 | depth-128/SOE totals | 129 | 29,862,824 | 234,074 | 107,025 |
| compact / 4 | depth-128/SOE totals | 45 | 19,434,501 | 450,311 | 266,432 |
| uncompressed / 2 | depth-128/SOE totals | 129 | 40,514,758 | 317,432 | 190,294 |
| uncompressed / 4 | depth-128/SOE totals | 45 | 27,419,855 | 636,921 | 452,877 |

The Fibonacci traces finish at depth 1, `nextFrameId=179`, totalSteps 1,592,
lifecycle RETURNED, and one persistent root. The SOE traces finish at depth 128,
`nextFrameId=129`, totalSteps 510, lifecycle JAVA_FAULT/kind 2, and 128 persistent
active frames. This checks bounded persistence, ID consumption, clear/refund paths,
and terminal header shape only. Epoch counts and gas are not predictions of actual
Java execution because the TEST scheduler coalesces storage transitions without
executing intervening bytecodes.

## Prototype limitations and required parent freeze

The prototype deliberately omits classfile parsing, Methodref resolution, metadata
registration, bytecode execution, argument/return semantic checks, method-specific
stack/local limits, exact production errors, code provenance beyond the echo hash,
full unchanged-chain topology proof, production ephemeral summary records, and all
268 signed guest comparisons. Its full-frame echo ABI is useful conservative ABI
evidence, but not necessarily the final encoding. CREATE measurements exclude the
future parser/analyzer and metadata registration. Consequently it is neither S2b
execution nor an acceptance result.

Before implementation, the parent must freeze exact schema/domain IDs, metadata
bits and call records, component split and code hashes, constructor/resume/
checkpoint/store ABI, compact packing, frame/delta/fault tuples, sorted-delta and
ephemeral-summary rules, error numbers and precedence, max frames/steps/delta bytes,
physical versus semantic dirty counters, reserve checks, gas thresholds, and the
268-row oracle/resource gates. That freeze is outside this task.

Recommended future write set is exclusively new `jvmevm/stock/s2b/**` runtime,
harness, verifier, artifacts, and new stock/s2b testdata/catalogue paths, with
unique `stockS2b*` helper names. Parent alone owns the frozen S2b plan, Make/guide
integration, and cross-stage final gates. Do not edit or migrate S0/S1/S2a,
monolith, old fixtures/cases/gas budgets, tools/CLI, or EVM/core/consensus/params.

S2b remains a single ordinary-class scalar-int call profile. It adds no heap,
objects, arrays, references, long/FP, statics/`<clinit>`, exception object,
handler search/unwind, Throwable API, libraries, String/main/JAR, monitors/threads,
VFS, clock/scheduler, network boundary, Minecraft startup, or connectivity claim.

## Reproduction and evidence hashes

```sh
cd build/java-diff-stock-s2b-frames
npm ci --ignore-scripts --no-audit --no-fund
node build.js
cd ../..
go run ./build/java-diff-stock-s2b-frames
```

The directory is ignored and may be regenerated. Only this proposal is tracked.

| Evidence | SHA-256 |
|---|---|
| `FrameDeltaPrototype.sol` | `2c4c2d328fe724dbb1919b1a034cb136bc6b96c8cad0020f2a81237fbf90b864` |
| `build.js` | `ca7cc7e001a97149c96f54f6609968b0ec0a9f61cb0f3872bb747340a23a381d` |
| `prototype.go` | `938f5a4e505e36f48609f83cc661551554585e596ebba32f85138afb55bec607` |
| `artifacts.json` | `82cbc5be75d187c16fa18c06077cb2ad87dbd24450410bde50ca25a9bb1516db` |
| `results.json` | `6344f5abb47b68243b73cd0a0dd16d82d8a34f72db98dca9b5828e13bc2fb792` |
| `package.json` | `22dcf44f9cafaafb149268dc009cccaf89f0d2de8fb96e453ba85ad17915cff6` |
| `package-lock.json` | `d6f3e6a5132369648213e85fcf5919cb590b2d092c3708d1e302f17bba579547` |
