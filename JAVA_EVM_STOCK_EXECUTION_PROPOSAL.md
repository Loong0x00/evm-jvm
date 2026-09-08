# Stock-EVM modular execution and continuation preflight

Status: **proposal and ignored prototype only**, based on
`fc9061c28fb7065097fff722915c3a5dd79b7b5d`. This is not a frozen stage,
production implementation, M5d-a acceptance, full-interpreter deployment proof,
or Minecraft execution claim. Parent-reported M5d-a candidate gates were still
running: 154,839 runtime bytes and 2,231 cases, with latest fixes `4ceb539` and
`fc9061c`. The measured candidate artifact is SHA-256
`dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.

No Minecraft/server JAR was executed or downloaded for this work. No listener was
opened and no EULA decision was made. The endpoint remains the genuine, guest-
produced 1.12.2 startup-complete marker proposed in
`JAVA_EVM_MC_STARTUP_PROPOSAL.md`; connectivity is optional. All work products
except this document are ignored under
`build/java-diff-stock-evm-preflight/`.

## Conclusion

A generic modular interpreter with persistent continuation is technically
feasible using ordinary stock EVM contracts. A bounded probe demonstrates all of
these narrower facts in unchanged geth:

* three small contracts were deployed through transaction-style `CREATE`, not
  `SetCode`;
* one contract's deployed code is exactly a trusted, unchanged 183-byte Java 8
  classfile and is read as an immutable code page;
* a generic 4,605-byte classfile parser/integer step module executes the raw
  `run()I` Code bytes;
* a generic 2,020-byte controller commits PC, stack, locals and completion state;
* four separate resume transactions produce the JVM-oracle value 12; and
* an intentionally underfunded resume reverts, after which the first successful
  checkpoint still has sequence 1.

This establishes an execution mechanism, **not** a way to mechanically split the
current 154,839-byte Solidity monolith. The monolith's state is almost entirely
Solidity memory and its helper functions are private. EVM calls do not share
linear memory. Preserving the current Java semantics therefore requires a real
conversion to a canonical persistent VM state and bounded state-machine steps,
followed by differential replay of the complete accepted profile. Copying source
functions into contracts and ABI-encoding the current memory graph between them
would be both semantically fragile and prohibitively expensive.

The architecture is feasible; its Minecraft-scale gas, state growth, class-
library coverage and total execution count remain unproven. In particular, the
30,222,121-byte pinned 1.12.2 server JAR needs at least 1,230 maximum-size code
pages and 6,044,424,200 gas in code-deposit charge alone, before initcode,
transaction, manifest, class parsing, libraries, VFS, or world generation.

## What the current runner actually proves

`jvmevm.Run`/`RunClasses` ABI-pack raw classfiles and call
`core/vm/runtime.Execute` (`jvmevm/jvmevm.go:132-160`). The pinned upstream helper
creates a temporary account and directly invokes
`State.SetCode(address, code)` before `EVM.Call`
(`core/vm/runtime/runtime.go:137-170`). Its reported gas is only the call gas given
to that helper. It excludes transaction intrinsic/floor gas, contract-creation
execution, 200 gas per deployed code byte, and persistent checkpoint storage.

The helper's default chain rules activate through Cancun at block/time zero but
not Prague or Osaka, and a caller-supplied `GasLimit` is passed directly to the
call. Existing focused tests commonly use 50--250 million gas. Those remain
valuable semantic tests but are not evidence that the call fits a current stock
transaction or block.

`runtime.Create` is closer, but it still calls `EVM.Create` directly and does not
charge top-level transaction intrinsic/floor gas. The probe instead uses
`core.ApplyMessage`, `To == nil`, nonce checks and transaction checks enabled.
That path deducts intrinsic gas, checks EIP-3860, then invokes ordinary
`EVM.Create`. It does not use `StateDB.SetCode`. It is not a signed transaction,
block import, receipt, public-network, or multi-client proof; a frozen
implementation slice should add a signed simulated-backend replay.

## Pinned geth / stock-limit audit

The diff from pinned upstream geth v1.16.9
`95665d5703e1023995a0ff93e4ce9eb77e8a59bd` through `fc9061c` changes no path
under `core/vm`, `core/state`, `core/types`, `consensus`, or `params`.
`core/vm/runtime/runtime.go` has the same SHA-256 on both revisions:
`822478c26ca1eb4313ab83da97576cbc4d93397f8f1cfddebbffcb6afd7d9c26`.
This source audit does not replace bytecode execution on another conforming
client.

| Limit/cost | Pinned geth behavior | Consequence |
|---|---|---|
| EIP-170 deployed code | `params.MaxCodeSize = 24,576`; post-EIP-158 creation rejects a larger return | 154,839 bytes cannot be one ordinarily deployed contract; at least 7 perfectly packed code modules, and probably more after routing/state code, are required |
| EIP-3860 initcode | Shanghai creation transaction and CREATE/CREATE2 limit is 49,152 bytes; 2 gas per 32-byte word | Factories do not evade the limit; each module/page needs bounded initcode |
| Code deposit | 200 gas per deployed byte before Verkle rules | A full 24,576-byte module costs 4,915,200 gas solely to store code |
| Transaction intrinsic | creation base 53,000; call base 21,000; calldata is 4 gas/zero byte and 16 gas/nonzero byte after Istanbul | Deployment and resume accounting must include these, unlike `runtime.Execute` |
| Prague calldata floor | `21,000 + 10 * (zeroBytes + 4*nonzeroBytes)` | Large transaction inputs may be floor-priced even when ordinary intrinsic gas is lower |
| EIP-7825 | when Osaka is active, `params.MaxTxGas = 2^24 = 16,777,216`; `core.ApplyMessage` rejects more | Every deployment and resume must fit independently below this cap; pre-Osaka chains instead remain bounded by block gas/configuration |
| Block gas | supplied by the block header/chain; not a universal EVM constant | A 16.77m-valid transaction still needs a block that admits it; proposals must pin chain/fork/block gas |
| Call/create depth | `params.CallCreateDepth = 1,024`, with EIP-150 forwarding at most 63/64 of available gas | Never represent Java frames by recursive EVM calls. Keep module routing sequential and target EVM nesting <= 4 |
| Operand stack | EVM stack limit is 1,024 words per EVM frame | JVM operand/local/frame vectors belong in persistent state or bounded memory, not on a long-lived EVM stack |
| Memory | expansion is `3*w + floor(w*w/512)` gas for `w` 32-byte words; geth also rejects sizes above `0x1FFFFFFFE0` bytes | At 16,777,216 gas, memory expansion alone reaches only about 91,917 words / 2,941,344 bytes, before any useful execution. Whole-JAR or whole-heap materialization per resume is impossible |
| Storage | cold access 2,100, warm read 100, and a clean zero-to-nonzero SSTORE normally 20,000 gas under the audited schedule; refunds are capped | Dirty VM state per slice, not just opcode count, controls continuation throughput and total state cost |

The executable negative probes under all-dev rules (Osaka active) measured exact
rejection of 49,153-byte initcode and a 16,777,217-gas transaction. Initcode that
returns 24,577 bytes failed with `max code size exceeded`, consumed its full
8,000,000 transaction gas, and left no deployed code. These are expected stock
rules, not project-added guards.

### Artifact paging

Use immutable code-as-data page contracts, not storage slots, for pinned JAR,
class and resource bytes. A production page should deploy `STOP || payload`, so
an arbitrary payload beginning with forbidden EIP-3541 byte `0xef` cannot become
the runtime's first byte. This leaves at most 24,575 payload bytes per page.
A manifest contract commits:

```
artifactId = keccak256(version || totalLength || pageCount || pageHash[])
pageHash[i] = keccak256(exact payload bytes)
```

Readers use `EXTCODEHASH` plus bounded `EXTCODECOPY`, remove the one-byte prefix,
and reject length/hash mismatches. Reconstructing the exact ordered bytes is an
EVM operation. The host may submit opaque pages and inspect receipts; it may not
parse JARs/classes or choose execution results on the production path. CREATE2
can make addresses deterministic, but neither CREATE2 nor a factory waives
EIP-170, EIP-3860, gas, or transaction checks. Blob data is not permanent state
and therefore needs an explicit availability/commitment protocol before it could
replace code pages.

The probe used a direct raw classfile page because its first byte is `0xca`; the
safer prefix convention is a required change for any production slice.

## Existing monolith dependency inventory

The current source is one 6,090-line contract. Its two public pure front ends
build one invocation-local memory graph and call `_execute`:

* `interpret` / `interpretClasses` (lines 213--436): ABI input, class selection,
  bootstrap append, per-class cache allocation;
* parsing and method loading (437--697), plus member/class readers
  (4,308--4,795 and 5,846--5,972);
* `_execute` (698--2,330): the monolithic opcode loop. It directly mutates frames,
  statics, initialization state, array/object heaps and the exception arena;
* initialization, hierarchy, dispatch and member resolution (2,331--4,307);
* IEEE software kernel (4,797--5,230);
* primitive/value/stack/local/heap/exception helpers (5,231--5,845); and
* 24 embedded bootstrap classfile producers (5,973--end).

The important dependency cycles are semantic, not merely source-level:

1. parsing/predecode feeds descriptors, handlers and all resolution caches;
2. resolution may trigger class/default-interface initialization and new frames;
3. an opcode may resolve a member, initialize a class, allocate, or raise a Java
   fault before it performs its visible write;
4. unwind traverses frames and lazily resolves applicable catch classes;
5. heap assignability depends on hierarchy metadata; and
6. FP, array and field operations all use the same tagged 64-bit value cells.

`ClassInfo`, `Selected`, `Frame`, `PendingException`, `HeapRegistry` and
`ExceptionArena` contain dynamic memory arrays. An external CALL or DELEGATECALL
starts with separate EVM memory. DELEGATECALL shares storage/address/caller, not
memory. Consequently, module boundaries should be placed around operations on a
versioned storage schema, not around today's private helper signatures.

## Concrete modular architecture

### Contracts and trust boundary

1. **ArtifactManifest + DataPages**: immutable exact-byte source, page hashes,
   total length and root.
2. **VMCoordinator** (small): instance ownership, immutable module-registry hash,
   artifact/config roots, lifecycle, sequence/epoch checks, reentrancy lock,
   per-call gas/step/write ceilings, checkpoint event and final output.
3. **ModuleRegistry** (immutable for an instance): schema version, role IDs,
   module addresses and `EXTCODEHASH` commitments. No class-specific module or
   runtime generation is permitted.
4. **Parser/Linker module**: bounded page reads, class/JAR structures, descriptors,
   predecode and cache records.
5. **Dispatch modules**: grouped opcode families operating on the same canonical
   frames/value-cell format. Java invokes push persistent Java frames; they do not
   recurse through EVM calls.
6. **Resolver/Init, Heap/Type, Exception/Unwind and IEEE modules**: preserve the
   existing ordering rules and tagged cells. Later library/platform modules use
   the same explicit guest boundary.
7. **State pages** only where coordinator storage becomes too large: keyed chunks
   with owner/instance/schema checks. They are ordinary contracts and must not
   permit arbitrary callers to alter a live VM.

The coordinator performs a sequence of sibling DELEGATECALLs, normally at EVM
nesting depth 2. A module returns the next role/opcode and a bounded accounting
summary; it must not delegate recursively. Module code is generic and frozen by
code hash. DELEGATECALL is chosen so modules share the coordinator's persistent
schema, not to evade any deployment limit.

A minimal stable control ABI is:

```
resume(expectedEpoch, maxJvmSteps, maxDirtyWords)
  -> (newEpoch, status, steps, dirtyWords, guestOutputDigest)
status() -> (schema, artifactRoot, configRoot, epoch, lifecycle,
             currentFiber, virtualTime, outputLength)
```

`resume` rejects stale epochs, wrong module hashes, unsupported state/schema,
reentrancy and excessive budgets. Public callers may pay gas, but cannot choose a
module, PC, exception result or state delta. A later inbox ABI accepts only opaque,
commitment-bound virtual I/O bytes; Java/library code consumes them.

### Canonical persistent VM state

The initial schema should retain the current representations rather than invent
new semantics:

* VM header: schema, lifecycle (`LOADING/RUNNABLE/THREW/RETURNED/WAITING`), epoch,
  artifact/config/module roots, deterministic step count and active fiber;
* class table: raw byte range, parsed CP/member metadata, hierarchy links,
  initialization state (`uninitialized/in-progress/initialized/failed`), cached
  failure Throwable reference, static tagged cells and resolution caches;
* frame vector: class/method, PC, call PC, operand depth, tagged stack cells,
  locals plus initialized bits, constructor/init-continuation flags and receiver;
* heap: monotonically allocated handles, kind/class/rank, object field cells,
  primitive/reference array cells, quota counters and canonical Throwable arena;
* pending exception: active flag, kind/reference and fault PC, preserving ordered
  handler search and unwind state across a checkpoint;
* scheduler/platform roots: runnable queues, monitor ownership/waiters, virtual
  clocks, VFS root, virtual network namespace and input/output cursors; these are
  empty/deferred in the first slice but their versioned roots must not be confused
  with host services.

Mappings/chunks are the serialization. A resume should load only touched frame,
class and heap chunks. It must never decode the entire VM into EVM memory. Every
cell write is namespaced by instance/schema. Array/object handle identity and all
four raw IEEE bindings remain unchanged.

### Safe continuation and deterministic replay

A checkpoint is allowed only between complete JVM instructions or at an explicit
sub-operation cursor whose partial effects are not Java-visible. Complex
operations (class initialization, allocation, handler search, page parsing) need
phase/cursor records. Each phase either commits one uniquely sequenced delta or
reverts; resume cannot repeat a field write, output event, allocation, exception
raise, monitor transition or VFS write.

The implementation must reserve gas **before** beginning the next bounded phase
and retain enough for worst-case dirty-word commits, invariant checks and the
checkpoint event. `gasleft()` is a guard, not a gas estimator. If the reserve is
wrong, top-level revert is the safety backstop: all state and logs from that
transaction roll back. Out-of-gas must never be translated into Java OOM or a
successful pause.

Use `expectedEpoch` as optimistic concurrency control. Increment it exactly once
on successful commit. Emit output only after the corresponding output bytes and
cursor are stored; logs revert with state. Future external I/O is two-phase:
committed guest outbox first, opaque adapter acknowledgement/inbox in another
transaction. Block timestamp, sender ordering and transaction count must not
silently become Java time or scheduler choices. Virtual time/entropy/config are
committed inputs with deterministic update rules.

A replay record pins chain ID/fork rules, block context policy, module/code hashes,
artifact/config/input roots and ordered transaction calldata. Re-execution must
match every checkpoint tuple and final EVM state/output roots. A rolling digest is
useful evidence but is not a replacement for canonical state or page validation.

## Ignored prototype evidence

The trusted fixture was compiled locally with `javac --release 8 -g:none`. Its
unchanged classfile is 183 bytes, SHA-256
`a7e471f147529dd6b47980976723b73e30030b9f8562aee125e4945001bb20bc`.
`javap` shows `run()I` executing ordinary `iconst`, `istore`, `iinc`, `iload`,
`imul` and `ireturn` bytecodes. The trusted host-JVM oracle printed `12`
(`oracle.log` SHA-256
`a1fb50e6c86fae1679ef3351296fd6713411a08cf8dd1790a4fd05fae8688164`).
Host code does not extract its Code attribute; the deployed EVM module parses the
classfile constant pool/method attributes and locates `run()I` itself.

Solidity 0.8.30, optimizer 200, via-IR, Cancun target and metadata disabled
produced these modules. All-dev geth rules were used, including Osaka's
transaction cap. `core.ApplyMessage` used a 30,000,000 block gas pool but every
individual transaction was below 8,000,000 gas.

| Operation | Init/runtime bytes | Gas used |
|---|---:|---:|
| CREATE exact raw-class page | 198 / 183 | 91,996 |
| CREATE generic step module | 4,631 / 4,605 | 1,048,857 |
| CREATE persistent controller | 2,560 / 2,020 | 552,007 |
| deliberately low-gas resume (reverted) | - | 68,640 |
| successful resumes, budget 3 JVM instructions | - | 120,708; 123,255; 87,504; 124,646 |

The four successful transactions persisted PCs 165, 168, 175 and 177, sequences
1--4, then returned 12. Successful deployment plus resume gas was 2,148,973;
including the deliberately reverted transaction, submitted gas used was
2,217,613. The class-page runtime exactly matched the classfile and its keccak256
was `0x3c954446bb4da357f49b6c322ad17b80f631b143e1c5b042a73c925d9801b248`.

Key ignored evidence:

* `prototype.go` SHA-256
  `faccf007a9c8373cc7bae9b400682f771b15e6a97ee15a2dec19474140be867f`;
* `prototype.log` SHA-256
  `0c9d459655fa6cc3cb10970cf9263ba45d54214f839282c7f353ecc90ff91afc`;
* `audit.log` SHA-256
  `abf12c876cb6a6caa300e851dc035e028203d34642cf30183637d7dc62cae708`;
* `StockPrototype.sol` SHA-256
  `d5cab64617090920827046918258204bf16b344e8f4bea6e4032114a22a4b1b7`;
* `ResumeFixture.javap.txt` SHA-256
  `df388a60172b2ee4de0860d274036312ba0e7ee167fa7e168258cb1946ae5a9d`;
* generated module JSON hashes and tool lock are recorded in ignored
  `SHA256SUMS`.

Exact replay from the repository root:

```sh
cd build/java-diff-stock-evm-preflight
npm install --no-audit --no-fund --save-exact solc@0.8.30
javac --release 8 -g:none ResumeFixture.java OracleRunner.java
javap -c -p ResumeFixture > ResumeFixture.javap.txt
java OracleRunner > oracle.log
node compile.js
go run prototype.go
```

The prototype supports only one uniquely named static `run()I`, four locals,
eight stack cells, classfiles <= 4 KiB and a small integer opcode list. It does
not implement current M5d-a semantics, exceptions, calls, objects, arrays,
threads, libraries, JARs, Minecraft, or the proposed robust prefixed pages. It is
an architectural subset and must not replace or be counted with the 154,839-byte
interpreter or its 2,231 candidate cases.

## Proposed next SMALL slice for parent freeze

Suggested name: **S0 stock deployment/continuation skeleton**. It should remain
independent of M5d-a acceptance and must not edit the monolithic interpreter.
The parent may change/freeze this proposal; no implementation contract is active
from this document.

### Exact proposed write sets

Runtime worker owns only new paths:

* `jvmevm/stock/runtime/ArtifactPage.sol`
* `jvmevm/stock/runtime/TinyJvmStepModule.sol`
* `jvmevm/stock/runtime/VMCoordinator.sol`
* `jvmevm/stock/runtime/build.js`, `package.json`, `package-lock.json`
* generated artifacts under `jvmevm/stock/runtime/artifacts/`

Harness/test worker owns only new paths:

* `jvmevm/stockevm.go`
* `jvmevm/stockevm_test.go`
* `jvmevm/testdata/stock/ResumeFixture.java`
* `jvmevm/testdata/stock/ResumeFixture.class.hex`

Documentation/integration worker owns only this proposal or a new frozen
`JAVA_EVM_STOCK_S0_PLAN.md`. No worker edits
`jvmevm/runtime/JVMSubsetInterpreter.sol`, current runtime hex, existing tests,
consensus/EVM/params, precompiles, gas rules, limits or Minecraft files.

### Frozen-capability candidate

* safe `STOP || payload` pages deployed by ordinary CREATE;
* immutable module code-hash registry and schema version;
* classfile-side selection of unchanged trusted Java 8 `static ()I` Code;
* only the prototype integer opcodes, fixed stack/locals and persistent PC;
* bounded resumes with epoch, dirty-word and commit-gas guards;
* exact unsupported/malformed/revert outcomes, with no Java/host fallback.

This is deliberately not “modularized M5d-a.” Its purpose is to establish a
production-quality stock transaction and persistence foundation before migrating
one accepted semantic family at a time.

### Required gates and budgets

* Standard path: signed transactions on geth simulated backend **and** direct
  `core.ApplyMessage` replay; no test helper may call `SetCode` or mutate deployed
  code/storage to establish success.
* Size: every deployed runtime <= 12 KiB for S0 (stricter than EIP-170), every
  initcode <= 24 KiB, page payload <= 4 KiB.
* Transactions: each CREATE <= 8,000,000 gas; each resume <= 2,000,000 gas and
  <= 16 JVM instructions; <= 16 successful resumes and <= 32 dirty storage words
  for the fixture; all are below Osaka's 16,777,216 cap.
* Total: <= 8 deployment/call transactions and <= 30,000,000 successful gas for
  the acceptance fixture, excluding separately reported negative transactions.
* Semantics: unchanged trusted class bytes and hash; EVM-side method discovery;
  final result and failure behavior match a host JVM oracle; at least three
  successful continuation transactions.
* Atomicity: inject OOG, insufficient commit reserve, stale epoch and malformed
  page/hash failures at every phase; state/epoch/output/logs remain at the last
  committed checkpoint.
* Determinism: two clean signed replays match contract addresses, code hashes,
  per-checkpoint tuples, gas under the same fork context, final state root and
  output.
* Limits: executable EIP-170, EIP-3860 and EIP-7825 rejection tests remain exact;
  pin fork config and block gas in reports.
* Security/negative boundary: arbitrary callers cannot select module/PC or mutate
  pages; unsupported bytecode fails explicitly; no host parsing/evaluation,
  precompile, class-specific code generation, listener, EULA input or downloaded
  Java execution.
* Regression: current M5d-a candidate gates must finish independently; S0 cannot
  weaken expected outcomes or be added to the accepted JVM case count.

After S0, the next proposal should migrate only one existing semantic unit—most
likely classfile reader/predecode plus scalar integer frames—onto the persistent
schema and compare exact outcomes against the accepted monolith. Full module
partitioning should be frozen only after measured compiled sizes, cross-module
gas, dirty-word counts and all historical differential behavior are known.

## Remaining blockers before workload claims

1. No compliant deployment of the current 154,839-byte interpreter exists.
2. No persistent implementation of its complete frame/heap/init/exception graph
   exists; the prototype's tiny state is not representative.
3. No measured partition shows that all existing semantic SCCs fit EIP-170.
4. Existing cases often rely on transaction-infeasible 50--250m call ceilings;
   per-opcode and per-dirty-word continuation costs are not measured.
5. JAR paging has a multi-billion-gas lower bound and no funded/operational chain
   model has been selected.
6. Java SE libraries, deterministic VFS/time/scheduling/logging/network boundary,
   world generation and genuine marker provenance remain as inventoried in the
   Minecraft proposal.
7. EULA/config authorization is deliberately absent, so server execution must not
   begin.

Accordingly, this preflight supports freezing a small stock-execution foundation,
not a Minecraft run, an M5d-a acceptance, or a claim that the current interpreter
is deployable unchanged.
