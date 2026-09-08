# S0: stock-EVM deployment and bounded persistent integer stepping

FROZEN implementation contract. Authority JAVA_EVM_PROGRAM.md; supersedes choices
in JAVA_EVM_STOCK_EXECUTION_PROPOSAL.md. Separate architectural subset, NOT a
replacement/migration of M5d-a, not Minecraft or full-interpreter deployment.
Last accepted full interpreter95fdcfd:154839bytes,2231 cases, SHA256
 dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929.
Keep its code, bootstrap images, APIs, fixtures, budgets and acceptance intact.
S0 counts/tests must remain separate. Ultimate goal unchanged MC genuine startup-
complete marker inside original EVM; connectivity optional.1.12.2 remains candidate,
no EULA acceptance/server execution authorized by this slice.

## Parent preflight findings / choice
Parent reproduced ignored stock prototype byte-for-byte log at
/tmp/stock-parent-prototype.log, verified SHA256SUMS. Ordinary CREATE/ApplyMessage,
three contracts/four resumes returned actual JVM value12; protocol negatives exact.
It is evidence of mechanism ONLY. Prototype flaws NOT carried into S0:
int256 arithmetic instead of Java int32 wrap; no local initialization bits;
insufficient CP/method/Code validation; no reliable selected-opcode predecode;
no explicit rejection of class initialization; raw page without STOP prefix;
no epoch/hash/state/budget contract suitable for independent replay.

S0 hardens that mechanism with real signed, in-process chain transactions as well
as ApplyMessage replay. It DOES NOT pretend the existing154839-byte memory VM has
been modularized. Fixed small value-state ABI copies are acceptable ONLY here;
full heap/class/frame state must later become paged persistent state, not enormous
per-call ABI copies. M5d-b0 Throwable proposal remains queued, NOT frozen/implemented.

## Non-negotiable execution boundary
All class parsing, entry selection, instruction validation/execution and state
transitions run in deployed ordinary EVM code. Host may compile trusted fixtures,
load Solidity artifacts, package opaque raw bytes, sign/send transactions, read
receipts/state/output, and run a trusted JVM as oracle. No production host class
parser, instruction evaluator, AOT/class-specific generated executable, fabricated
result or fallback to the monolith. Comparing monolith results in TESTS is allowed
as a separately labelled semantic oracle; stock result must come from stock calls.
No SetCode/SetState, genesis executable code/storage injection, EVM/opcode/gas/
precompile/consensus/limit modification. Genesis funding of a TEST-only EOA allowed.
No servers/listeners, credentials/EULA changes, downloaded Java execution or pushes.
Only one production Solidity writer. All new workers Sol/high WITHOUT Fast/priority.

## Package/write-set layout
Runtime worker ONLY new jvmevm/stock/runtime/**:
 StockTypes.sol, ArtifactPage.sol, TinyJvmStepModule.sol, VMCoordinator.sol,
 build.js, package.json/package-lock.json, artifacts/*.json, optional runtime README.
Harness worker ONLY new jvmevm/stock/stock.go, stock_test.go and
 jvmevm/testdata/stock/** (trusted Java source/hex/manifest/oracle, no downloaded code).
Verifier worker ONLY new jvmevm/stock/validation_test.go and jvmevm/stock/README.md.
Helpers stockHarness* vs stockVerify*; package stock. Parent owns Makefile, plans,
AGENTS/quickstart/program and integration/independent tests. No old jvmevm/runtime,
jvmevm/*.go, cmd, tools/java_diff*, historical fixtures or upstream core edits.
Each worker may use ignored build/java-diff-stock-s0-ROLE/ probes. No peer writes.

Go artifacts/ABI loader functions (harness-owned, small public helper surface):
 type Artifact struct { ABI abi.ABI; InitCode []byte; RuntimeCode []byte }
 func LoadArtifact(name string) (Artifact,error)
 Names exactly ArtifactPage, TinyJvmStepModule, VMCoordinator. Embedded JSON via
 //go:embed runtime/artifacts/*.json. Expose further metadata only if needed for
 verification of compiler immutableReferences; no Java parsing in this loader.
Verifier may independently read artifact JSON/pack calls rather than share harness
execution helpers; all Go sources in one package must compile together.

## Raw page and artifact identity
ArtifactPage constructor(bytes payload), payload1..4096 bytes, deploys EXACT
 STOP(0x00)||payload through normal CREATE. No writable page functions/state. Its
runtime starts STOP even for payload starting0xef; never depend on privileged code
insertion. Constructor rejects invalid size via StockPageError1.
Module reads size/prefix/hash with EXTCODESIZE/HASH/COPY. Valid page code size2..4097,
byte0==0, payloadHash=keccak256(exact bytes after prefix); pageCodeHash=keccak256
(STOP||payload). Prefix removal is EVM work. Parent/harness independently compare
actual deployed bytes with original raw fixture. This is one page, not a JAR system.

No host extraction of Code/method/CP. Entry is fixed literal name run and descriptor
()I selected by EVM from a generic classfile, not selected by fixture/class name.

## Exact selected Java profile
- Trusted ordinary Java8 classfile major52/minor0; total payload<=4096; CP1..512.
- Ordinary public class, Object superclass, no interfaces, no fields, no <clinit>.
  Reject any declared <clinit>, even if the selected method never mentions a field.
  No hidden superclass initialization. This profile only needs trivial Object init.
- Valid this/super Class->Utf8 references and ordinary internal names; no array,
  empty component, dot/semicolon/bracket name. This stage may restrict names to
  ASCII profile bytes; reject rather than misdecode unsupported names.
- One unambiguous declared run, public static ()I with exactly one Code attribute;
  no synchronized/native/abstract root or contradictory visibility flags.
- Other methods (including javac default constructor) are not entered/predecoded,
  but outer member/attribute indices and lengths are bounded/validated. Unused
  methods may contain other valid Java opcodes/types without expanding S0 support.
- Selected Code1..256 bytes, max_stack<=8 words, max_locals<=4, zero handlers.
  Parse/skip nested Code attributes within their actual declared boundary, class
  attributes too; consume exact full class length. No silent trailing truncation.
- CP tags legal in major52 may be structurally scanned:1,3,4,5,6,7,8,9,10,11,12,
  15,16,18. Long/double consume TWO slots, including last-slot bound. Validate all
  referenced CP indices/tags/name chains needed for class/member/attribute selection;
  do not claim whole-class JVM verification for unused relationships.
- Predecode ALL selected instructions before execution, including unreachable
  instructions: widths, CP operands, local indices and starts. No branch opcodes
  in S0; no branch target verifier implied. Entering non-start PC still fails.

Only supported opcodes:
 nop00; iconst_m1..iconst_5(02..08); bipush10; sipush11;
 ldc12/ldc_w13 ONLY CONSTANT_Integer;
 iload15/iload_0..3(1a..1d); istore36/istore_0..3(3b..3e);
 iadd60,isub64,imul68,ineg74,iinc84,ireturnac.
No div/remainder, calls, branches, reference/FP/long bytecodes, arrays, handlers,
monitors, class/library services or Java-origin exception ABI. Unsupported selected
opcodes fail explicitly, never fall back or produce a successful continuation.

Java int operations use signed32-bit semantics modulo2^32, including iinc and
MIN_VALUE negation, NOT Solidity int256 arithmetic. Signed immediates exact.
Loads/iinc require initialized local; stores mark it. Operand underflow, declared
max_stack/max_locals limits and exact single int at ireturn are checked. Falling
out of Code without ireturn fails. A return before later supported unreachable
instructions is legal, but those instructions were still predecoded.

## ABI and canonical state (frozen shared worker interface)
StockTypes.sol defines:
 struct Machine {
   uint32 pc; // JVM-relative opcode PC, NOT absolute classfile offset
   uint8 sp;
   uint8 initialized; // low4 bits, local initialization mask
   uint256[8] stack;
   uint256[4] locals;
   bool done;
   int32 result;
 }
Active int cells use current monolith representation (uint256(1)<<64)|uint32(bits).
No other bits allowed. Uninitialized locals and stack cells>=sp canonical zero.
Pop/return clears unused cells; locals/initialized mask persist. result0 until done.

TinyJvmStepModule has no state/constructor arguments and no mutable configuration:
 inspect(address page,bytes32 expectedPageHash,bytes32 expectedPayloadHash)
   external view returns(uint32 codeOffset,uint32 codeLength,uint8 maxStack,uint8 maxLocals)
 step(address page,bytes32 expectedPageHash,bytes32 expectedPayloadHash,
      Machine calldata beforeState,uint8 budget)
   external view returns(Machine memory afterState,uint8 executed)
It may reparse/predecode<=4KiB on each step call (bounded small-subset compromise).
No trusted host-provided parsed metadata. budget1..16, executed>=1<=budget. Validate
input-state invariants and PC start as well as classfile. Direct stateless calls do
not alter a VM or waive coordinator checks. Module does not invoke other modules.

VMCoordinator constructor(address module_,address page_,bytes32 expectedModuleHash_,
 bytes32 expectedPageHash_,bytes32 expectedPayloadHash_). Pin all as immutables;
validate module extcodehash/nonempty at construction and every resume, validate page
via inspect at construction and step every resume. Constructor calls module inspect
in EVM and starts Machine(pc0,sp0,initialized0,zero cells,donefalse,result0), epoch0,
totalSteps0. No caller-supplied PC/state/module on resume, no upgrades/mutable pages.
A supplied module hash is a configuration COMMITMENT, not an attestation: tests and
reports MUST match deployed module to the pinned compiler artifact, not trust an
arbitrary caller's address/hash pair as proof of a JVM.

 resume(uint64 expectedEpoch,uint8 maxJvmSteps,uint8 maxDirtyWords)
   external returns(uint64 newEpoch,bool done,int32 result,uint8 executed,uint8 dirtyWords)
 checkpoint() external view returns(uint64 epoch,uint64 totalSteps,bytes32 stateDigest,Machine memory machine)
Public immutable getter names module,page,expectedModuleHash,expectedPageHash,
expectedPayloadHash. Any caller may pay for a correctly sequenced resume; cannot
choose instruction/result or mutate committed input. Reentrancy protection required.
Lifecycle RUNNABLE vs RETURNED only. Further resume after return fails, not a new run.

stateDigest=keccak256(abi.encode(uint32(1),expectedPayloadHash,expectedModuleHash,
 machine,epoch,totalSteps)). Schema1 is fixed; never call this full M5d-a VM state.
Emit exactly one Checkpoint event on success:
 Checkpoint(uint64 indexed epoch,uint64 totalSteps,uint32 pc,uint8 sp,bool done,
            int32 result,uint8 executed,uint8 dirtyWords,bytes32 stateDigest)
No checkpoint/output logs on failure. Integers in ABI use canonical Solidity signed
encoding; display host int32, no synthesized Java text.

## Transaction/commit atomicity and budgets
Use sibling STATICCALLs with bounded fixed-state envelopes for S0. No pretend
shared EVM linear memory. Full interpreter later needs different paged state;
S0 is an explicit small architectural foundation, not a mechanical module split.

Each successful resume executes complete JVM instructions only, increments epoch
ONCE and totalSteps by executed, and commits one canonical Machine. Reject stale
epoch, bad budgets, wrong hashes, invalid state/module response, malformed guest,
insufficient reserve and OOG; never commit a partial opcode/result or return OOG as
successful pause/Java OOM. Module errors bubble as hard EVM validation failures.
If any instruction in a batch fails, ALL that transaction's VM changes/logs revert;
previous committed checkpoints survive. Normal EOA gas charges/nonces from failed
transactions do NOT roll back; don't falsely assert whole-chain state rollback.

maxJvmSteps1..16; maxDirtyWords1..32. Dirty-word accounting is a CONSERVATIVE count
of changed canonical state scalar/cell words plus epoch,totalSteps,digest, not a
claim that Solidity packed each scalar into its own storage slot. Count pc,sp,
initialized,done,result and each8stack/4local word if changed; plus3 header words.
Actual changed persistent storage slots must be <=reported count; lock scratch is
not part of committed machine but all its gas counts. Reject if count>requested
budget BEFORE committing. Max32 safely bounds the fixed state; no fake zero count.

Reserve gas BEFORE entering module. Commit reserve800000gas is an initial hard
lower bound for worst32 cold dirty words plus bookkeeping. Ensure module call cannot
consume it (explicit call gas stipend); check post-call reserve before writes.
If measured bound insufficient, report parent freeze issue, don't raise protocol gas
limits or silently waive rollback. No reliance on Solidity try/catch as guest Java
exception implementation (S0 has no guest handlers).

Limits: runtime each<=12KiB, initcode each<=24KiB (data page4097runtime). All below
standard EIP170/3860. CREATE<=8Mgas, resume<=2Mgas, all below Osaka MaxTxGas2^24.
Pin chainID1337/all-dev rules including Osaka and blockGas30000000. No disabled
transaction/nonce checks, no NoBaseFee hack on signed path. Direct replay uses same
signed transaction sender recovery/rules with explicit deterministic block context.
Canonical demo <=8 successful tx INCLUDING deployment, at least3 resumptions;
other small fixtures <=19 successful tx (3 deployments+up to16 resumes). Each case
<=30M successful aggregate gas; separately bound/report negatives. No blanket
claim16resumes plus3deploy fits the prototype's8tx demo ceiling.

## Build/reproducibility
Pinned solc0.8.30, optimizer200, viaIR,Cancun,metadata disabled. package-lock exact.
Build/check modes; no changing old compiler/dependencies. Artifacts JSON contains
contractName,abi,bytecode(hex),deployedBytecode(hex),immutableReferences and compiler/
source hash metadata in stable ordering. Build reads Solidity ONLY, never Java
fixture/classes/results. Verify deployed module byte-for-byte; coordinator full
runtime has constructor immutables, so verify using compiler immutableReferences
AND getter/actual deployed hashes. Record actual deployed code, not raw placeholder
artifact hash. Page exactSTOP||raw byte equality. No redistributed MC artifacts.

## Independent acceptance matrix
Harness: at least8 trusted Java8 source fixtures, small deterministic arithmetic,
negative immediates, int overflow/add/mul/neg/iinc, locals/live stack split across
resumes, ldc/ldc_w where practical via natural unused CP-generating helper methods.
Compile --release8 -g:none; store source+class.hex and hash pins with regeneration
checks, or deterministic generation manifest. The CLASS bytes supplied to stock
transactions and actual JVM oracle are identical, no host conversion/evaluation.
Multiple step budgets (1,3,16) produce identical final value/canonical terminal
state except expected epoch/step-batching digest differences. Verify local/stack
contents and actual executed count at checkpoints; do not infer only from final12.

Required TWO paths: signed transactions/receipts on geth simulated backend and
core.ApplyMessage replay from the same signed transactions (TransactionToMessage,
nonce/transaction checks enabled). No actual P2P/HTTP/WS/IPC listeners: in-process
backend only, explicit empty listen hosts, P2P MaxPeers0/NoDiscovery. Fund test EOA
at genesis only, no deployed contracts/state injected. TEST keys only, no real funds.

Replay twice: same key/nonce/calldata yields same contract addresses, code hashes,
VM checkpoint tuples/digests and gas under same active fork. ApplyMessage runs with
identical explicit contexts must match full final state root. SimulatedBackend.Commit
uses wall time: record actual headers, do NOT pretend distinct wall-time blocks have
identical hashes/global state roots. Signed replays compare canonical VM state and
gas; full-chain root equality only when all contexts actually match.

Verifier: exact error selectors/arguments for EOF/count/CP tags/indices/2-slot CP,
class flags/super/interface/fields/<clinit>, missing/overloaded/invalid root, Code
length/count/handler/trailing attributes, unsupported UNREACHABLE instructions,
truncated immediate, ldc wrongtag, local bounds/uninitialized, stack bounds/return,
canonical tagged cells/PC, page prefix/length/hash, module hash, stale epoch/terminal,
step/dirty/gas budgets. Valid unused constructor/body must not be silently executed.
Run rollback probes BEFORE first checkpoint and AFTER nonzero progress; insufficient
reserve and actual OOG distinct, no committed VM changes or logs. Corrupt page/hash
cases use ordinary newly deployed mismatching inputs, never SetCode/SetState.
Protocol limit negatives use ordinary raw initcode/transactions, not the stricter
S0 guards: runtime24577 -> EIP170 failure; initcode49153 -> EIP3860 rejection;
transaction16777217gas -> Osaka EIP7825 rejection. Preserve original error identity,
empty failed contract code and nonce/gas semantics. Simulated txpool vs execution
rejection timing may differ; document exact layer, don't relabel.

Frozen custom errors:
 StockPageError(uint256 code):1 size,2 prefix,3 page code hash,4 payload hash.
 StockClassError(uint256 code,uint256 offset):1 trunc/outer length;2 magic/version;
 3 CP/tag/index/name chain;4 class profile/fields/interfaces/super/<clinit>;
 5 root missing/ambiguous/access/descriptor;6 selected Code count/caps/handlers.
 StockBytecodeError(uint256 code,uint256 pc):2 truncated instruction;3 underflow;
 5 return shape;6 unsupported opcode/ldc kind;7 fallthrough;8 local range;
 9 stack capacity;11 uninitialized local;12 non-start/out-of-range PC;
 14 malformed machine/tag/cell state.
 StockControlError(uint256 code):1 terminal;2 module/address/hash;3 stale epoch;
 4 invalid step/dirty budget range;5 gas reserve;6 dirty cap;7 invalid module result.
Offset is offending raw payload byte offset (prefix excluded), PC relative to Code.
Range/cap vs physically truncated attributes have explicit errors above; isolate
single mutations for exact assertions. No opaque Solidity panics on malformed input.

Parent integrates runtime->harness->verifier; preserves full M5d-a gates, adds
separate java-stock-build/check/test/demo targets. Parent independently reruns JVM,
signed/direct replay, malformed/state/budget/stock-limit cases and source audit.
No S0 acceptance until deployed bytes, canonical checkpoint correctness, measured
gas and replay evidence all hold. Then plan S1 migration of actual accepted integer/
parser state on measured module interfaces; do not claim all2231 cases run on S0.
