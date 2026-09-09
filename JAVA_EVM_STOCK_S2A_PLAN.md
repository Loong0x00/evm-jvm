# Stock S2a: scalar integer completion and terminal arithmetic faults

FROZEN implementation contract. Authority JAVA_EVM_PROGRAM.md; overrides alternative
choices in JAVA_EVM_STOCK_S2_{ARCHITECTURE,ORACLE}_PROPOSAL.md. Accepted Stock S1
1b5150d and all S0/S1/monolith artifacts, ABIs, inputs, budgets and counts remain
unchanged. S2a is NOT accepted yet, not full M5d-a deployment or Minecraft startup.
Endpoint remains genuine unchanged MC startup-complete output in original EVM,
connectivity optional; no MC execution/EULA action in this slice.

## Parent decision: small arithmetic slice, not a hidden frame implementation
Migrate ALL201 existing M1/M2/M2b rows, adding119 to the82 stock-S1 workloads:
199 int values and2 actual ArithmeticException outcomes,60roots/11classes,
2642 attempted terminal instructions. Keep old manifest fields/limits exact.
Parent regenerated all6 added rawclass hashes from the oracle proposal with the
actual javac --release8/default-debug command. No host-generated Code metadata
or expected result enters any production call.

Choose the oracle proposal's SMALL one-frame increment. Do NOT implement the
architecture proposal's frame store, call records, private/void/six-arg analysis,
frame deltas or 268-row claim inside S2a. New schema3 here is this scalar/fault
profile, not the proposed speculative full-frame schema. Future call/frame work
will use an explicitly versioned adapter/reparse/new schema if needed; no promise
of live S2a-state upgrade or identical classId across changed parser versions.
This avoids forcing unmeasured call machinery into arithmetic acceptance.

S2b static-call/frame design remains proposal-only. Its measured16-child writes
already cost~3.8M BEFORE semantic/module/provenance costs. Moreover192 potentially
cold dirty words cannot be guaranteed by an800k commit reserve (192*22100 alone
exceeds4.2M). Do not freeze/copy that combination. Future frame design must measure
and reserve enough gas or reduce/compress the dirty slice, while keeping standard
EVM limits. S2a remains <=32dirty words/800kreserve/2Mresume, no frame batch.

## Boundaries/preservation
All parsing, resolution of selected methods/literals, instruction execution,
arguments/locals, fault detection and stored transitions execute in ordinary EVM.
Host only trusted compilation, opaque byte/entry/argument packaging, Solidity
artifact loading, signing/submission, receipts/checkpoints/outcome display. JVM
and oversized monolith are TEST oracles only, never production fallback. Bounded
TEST trace analysis may assert progress/locals/outcomes, but its metadata/results
must never be passed to the VM or used to skip guest execution.

No code-specific executable generation/AOT, SetCode/SetState or genesis executable/
contract-storage injection, core/EVM/params/consensus/opcode/gas/precompile/limit
change, downloadedJava/MC execution, EULA, listener, credentials, global settings,
peer writes, push or worker spawning. Genesis TEST EOA funding only. Sol/high
WITHOUT Fast/priority; never --fast/re-enable. One production Solidity writer.

Defer ALL calls/frames/SOE/heap/ref/arrays/long/FP/handlers/Throwable objects/APIs,
statics/clinit, interfaces, libraries and MC on this stock path. Known Java faults
are terminal here because handlers are outside the profile, not ignored handlers.
Methods with handlers remain ineligible; unsupported selected opcodes including
invokestatic fail even if unreachable. Do not fabricate stacktraces/messages/causes.

## Versioned layout/write sets
New package jvmevm/stock/s2a, package name s2a; preserve stock and stock/s1.
Runtime ONLY new jvmevm/stock/s2a/runtime/**:
 S2aTypes,S2aMetadataPage,S2aClassParser,S2aCodec,S2aStepModule,S2aCoordinator.sol,
 pinned build.js/packageJSON/lock/artifacts/*.json/runtimeREADME.
Harness ONLY new jvmevm/stock/s2a/s2a.go,s2a_test.go and
 jvmevm/testdata/stock/s2a/** (catalogue/additional trusted probes/docs).
Verifier ONLY new jvmevm/stock/s2a/validation_test.go and README.md.
Helpers stockS2aHarness*/stockS2aVerify*. Parent owns plans/guide/Make/integration/
independent tests. Read accepted S1 implementation to reuse reviewed semantics;
no edits to S0/S1/monolith/old fixtures/tools/CLI/core. Ignored
build/java-diff-stock-s2a-ROLE/ probes allowed.

Reuse unchanged stock.LoadArtifact(stock.ArtifactPage) raw page. S2a LoadArtifact
returns stock.Artifact for names S2aMetadataPage/S2aClassParser/S2aStepModule/
S2aCoordinator, embeds only new artifacts; immutable-reference loader may mirror
S1. JavaFaultClass(kind uint8)(string,bool) maps ONLY1 to
java.lang.ArithmeticException;0/2/unknown return false. Outcome clients/tests must
also validate lifecycle and canonical fault fields, not map arbitrary words.

## Profile, metadata and error deferral inherited precisely from S1
Retain S1 raw Java52.0,1..4096-byte payload,CP1..512/two-slot/tag/name checks,
ordinary public direct-Object class, no fields/interfaces/clinit,32declared methods,
256 eligible cached literals, Code1..256, maxStack/maxLocals<=8, public static named
(I{0..4})I root, ASCII ordinary entry1..64, ambiguity-before-descriptor, args checks.
Keep unused unsupported/ineligible method records instead of rejecting the whole
class. Keep selected-method error domains, all-instruction predecode, signed branch
starts and bounded int-only height/definite-local flow analysis. This is not a full
StackMapTable/classfile verifier. No private/void/internal-callable profile added.

IMPORTANT WideIntegerConstant.class is a genuine3469-byte/CP277 input. Its unentered
populateIntegerPool()I has Code793 and260 static literal sites, whereas loadWide()
has Code4 and one real ldc_w (261 class-wide, independently checked with javap). Reject selecting the oversized method (method error5),
but retain/register the class and execute loadWide. Do not leak partial ineligible
literals into the256 aggregate cap or replace the wide load with host resolution.

Metadata retains EXACT S1 six-header/four-words-per-method/eight-byte-literal binary
layout and bit positions, including zeroed Code-derived fields for ineligible
methods. Header H0 becomes keccak256("JVMEVM:S2A:METADATA:3"); no frame/call fields
or spare pretend-call records. Preserve method ordering, literal slices, roots,
page bounds, idempotent registration, original error precedence and exact metadata
length192+128*methods+8*literals (max6336payload/6337STOP-runtime).
S2aMetadataPage cap8191payload/8192runtime; retain reviewed bounded MCOPY, not a
bytewise constructor copy that breaks the8M maximum gate. Raw pages remain S0.

Hash domains/encodings: identical abi.encode types/order to S1 except schema3 and
 Dclass=keccak256("JVMEVM:S2A:CLASS"), Dprogram=keccak256("JVMEVM:S2A:PROGRAM"),
 Dinput=keccak256("JVMEVM:S2A:INPUT").
classId H(Dclass,uint32(3),parserHash,rawPage,rawPageHash,payloadHash,metadataHash).
programId H(Dprogram,uint32(3),classId,uint16(methodIndex),entryHash,descriptorHash,moduleHash).
argsHash H(abi.encode(int32[] args)). inputRoot H(Dinput,programId,argsHash,uint64(maxTotalSteps)).
stateDigest H(uint32(3),inputRoot,parserHash,moduleHash,MachineV3,epoch:u64,totalSteps:u64).
H above means keccak256(abi.encode(...)), not packed ambiguous concatenation.

S2aClassParser no constructor args. registerClass(address page,bytes32 expectedPageHash,
bytes32 expectedPayloadHash) returns(bytes32 classId,address metadataPage,bytes32 metadataHash,
uint16 declaredMethods). classRecord(bytes32) view returns(address metadataPage,bytes32 metadataHash).
Keep ClassRegistered event/types and append-only/idempotent behavior from S1. Actual
parser-issued data/provenance required; address/hash declarations are configuration
commitments, not attestations. Gate deployed bytes against pinned artifacts.

## Integer instruction semantics
Retain ALL S1 opcodes and add exactly:
 idiv6c,irem70,ishl78,ishr7a,iushr7c,iand7e,ior80,ixor82,i2b91,i2c92,i2s93.
No pop/return-void/invokestatic yet. Dataflow widths and stack effects must include
the new opcodes. idiv/irem/shifts/bitwise need2 ints and normally leave1; conversions
need1 and leave1. Category/tag/underflow/cap/initialization failures are hard errors,
never JavaFault. Preserve ordered signed branch and local behavior.

Java int32 modulo arithmetic and tagged payloads unchanged. idiv truncates toward
zero, irem has dividend sign. MIN_VALUE/-1 ->MIN_VALUE and MIN_VALUE%-1 ->0,
NOT Solidity signed-overflow panic. Widen checked arithmetic or explicitly handle
that edge, then return low32bits. Shift distance is low5bits even fornegative/large
counts; ishr sign-extends, iushr zero-extends, ishl truncates to32bits. i2b/i2s
sign-extend low8/16bits; i2c zero-extends low16bits. No floating/host arithmetic.

For a zero divisor, first validate operands/type/arity, then terminal JavaFault1
BEFORE popping/modifying any operand/local or advancing the instruction PC. Count
the faulting bytecode ONCE. Preserve the exact pre-FAULT-instruction machine, not
necessarily the pre-resume machine if earlier instructions in that batch ran.
Fault PC is the actual idiv/irem opcode PC. Do not execute following instructions.
Earlier successful instructions in the same resume commit together with the fault.
EVM OOG/invalid bytecode still roll the entire transaction back, no Java label.

## Frozen ABI/state (S2aTypes)
struct MachineV3 {
 uint32 pc; uint8 sp; uint8 initialized; uint8 lifecycle;
 uint256[8] stack; uint256[8] locals; int32 result;
 uint8 javaFaultKind; uint32 faultPC;
}
Machine is23 static ABI words. Existing int=(1<<64)|uint32(bits), canonical inactive/
uninitialized/out-of-range cells0. lifecycle0RUNNABLE,1RETURNED,2STEP_LIMIT,3JAVA_FAULT.
result0 unlessRETURNED; RETURNED sp0. faultKind/faultPC MUST be0 outsideJAVA_FAULT.
JAVA_FAULT requireskind1,result0,pc==faultPC at a valid idiv/irem start,sp>=2 and
zero-divisor tagged top operand. Its throwing method is the immutable ProgramContext
methodIndex; there is one root frame, no fabricated object/frame references.
STEP_LIMIT preserves current valid stack/locals/PC, result0 and faultfields0.

ProgramContext is EXACT S1 ten-field tuple (new S2aTypes):
 address parser;bytes32 parserCodeHash;bytes32 classId;address rawPage;
 bytes32 rawPageHash;bytes32 payloadHash;address metadataPage;bytes32 metadataHash;
 uint16 methodIndex;bytes32 programId.
S2aStepModule no ctorargs/state. step(ProgramContext calldata program,MachineV3 calldata
beforeState,uint16 budget) view returns(MachineV3 afterState,uint16 executed).
Input lifecycle0 only; budget1..128; return24 ABI words. Verify actual component/
registry/header/method/root/literal provenance as S1; no caller-authoritative metadata.
Module returns0/1/3, neverSTEP_LIMIT. Complete normal budget or terminate return/fault.

S2aCoordinator constructor SAME argument types/order as S1:
(address parser_,bytes32 expectedParserHash_,bytes32 classId_,address module_,
 bytes32 expectedModuleHash_,bytes entry_,int32[] args_,uint64 maxTotalSteps_).
Same immutable getters/parser selection/argument initialization as S1 plus
programContext() view. maxTotalSteps1..4096, no mutable configuration/upgrades.
resume(uint64 expectedEpoch,uint16 maxJvmSteps,uint8 maxDirtyWords) returns
(uint64 newEpoch,uint8 lifecycle,uint8 javaFaultKind,int32 result,uint16 executed,uint8 dirtyWords).
checkpoint() view returns(uint32 schema,bytes32 classId,bytes32 programId,bytes32 inputRoot,
 uint64 epoch,uint64 totalSteps,bytes32 stateDigest,MachineV3 machine).
Event CheckpointV3(uint64 indexed epoch,bytes32 indexed programId,uint64 totalSteps,
 uint32 pc,uint8 sp,uint8 lifecycle,uint8 javaFaultKind,int32 result,uint16 executed,
 uint8 dirtyWords,bytes32 stateDigest). Exactlyone per successful resume.

## Continuation/caps/fault outcome/rollback
Keep S1 loop-safe progress: count>=1<=effectiveBudget and totalSteps/epoch increase,
not a changedPC/cell requirement. EffectiveBudget=min(requested1..128,remainingcap).
RETURNED and JAVA_FAULT win when their instruction lands EXACTLY on maxTotalSteps;
only stillRUNNABLE becomesSTEP_LIMIT. Further resume after1/2/3 rejectsControl1.
A cap reached before a divide executes is STEP_LIMIT, not earlyArithmeticException.

Decode lifecycle3/kind1 ONLY as ArithmeticException outcome withclass/method/PC
provenance from committed state. It is a SUCCESSFUL terminal EVM checkpoint, not
an EVM custom-error revert. Unknownkind2(SOE notimplemented)/255, badfaultPC/opcode/
stack/value/nonfault fields or contradictory lifecycle are malformed module/state
failures. Never report lifecycle2 as value0, Java exception, OOG or success return.
No message/cause/trace/handler/Throwable/native-library API claim.

Preserve S1 reentrancy/component checks, exact canonical ABI/result decoder,
post-state/calldata gas recheck before stipend subtraction, bounded STATICCALL,
800000commitreserve+margin. Dirty count=3changedheaderwords(epoch/steps/digest)+
changed pc/sp/initialized/lifecycle/result/javaFaultKind/faultPC+changed16cells,
conservative<=26logicalwords. Validate actual persistent-slot bound, caller cap1..32
BEFORE writes; fault-only/header-only transitions still counted. EVM/module failure,
insufficient reserve/dirty cap, malformed reply etc revert ALL transaction VM state
and logs; previouscheckpoint survives, EOA nonce/gas effects normal. A fault-bearing
response rejected bydirty cap must retry from unchanged pre-resume state/epoch.

## Exact error domains
Retain S1 code meanings/precedence/locations, renamed S2aClassError(uint256,uint256),
S2aMethodError(uint256,uint256),S2aBytecodeError(uint256,uint256),S2aControlError(uint256).
Class1bounds/extra,2version,3CP,4classprofile,5aggregatecaps,6metadataCREATE/registry;
Method1missing(MAXindex),2ambiguous(secondindex),3access,4descriptor,5Code/caps/handlers,
6reserved,7argcount,8invalidentry(MAXindex); Bytecode2trunc,3underflow,5shape/join,
6unsupported,7fallthrough,8localrange,9stackcap,11uninitialized,12PCstart/range,
14noncanonicalmachine/cells,15branchtarget,16literalcache; Control1terminal,
2provenance/components,3stale,4budgets/cap,5reserve,6dirty,7invalidmoduleresponse/counters.
Reuse StockPageError1..4 for raw page errors. Faultlifecycle is NOT an error domain.
New malformed incoming faultfields ->Bytecode14; malformed module faultreply ->Control7.
No Solidity panic or unknown outcome may replace an exact specified failure.

## Budgets/build
Same pinned0.8.30/optimizer200/viaIR/Cancun/metadataoff, stable JSONABI/bytecode/
deployedBytecode/immutableReferences/sourcehashes; compiler reads Solidity ONLY.
Raw page unchanged S0 artifact. Parserruntime<=16KiB, otherexec<=12KiB, initcodes<=24KiB;
metadata<=8192runtime. CREATE/register<=8M, resume<=2M,800kreserve,dirty<=32;
Osaka txcap2^24/30Mblock/chain1337 unchanged. Refactor/report ifactualsizes/gasfail,
no silent project or EVM limit increases. Retain CPoffset cache and metadata MCOPY.

All201 primary rows at64/128, totalcap1024; max13resumes at64, isolatedsetup4tx+
coordinator+resumes<=19 externalpositiveTx/30Maggregate. Share parser+module and
11raw+11registration pages (24setupTx), thenfreshcoordinator percase/budget; report
shared/amortized vsisolated costs and failedgas separately. No edits to original
casegas_limits. Smallcase1/7/16 complete; longloops boundedprefixes as S1. Extra
infinite-loop/4096cap negatives are EVM-only and separatelybounded, no host infinite
Java. No M3a 268-case execution claim. All protocol/source-boundary tests retained.

## Acceptance matrix
Read exact201 stage m1/m2/m2b manifest rows in order; allIDs/sources/args/expectedkind/
timeouts/oldbudgets untouched. Compile same11 sources --release8(defaultdebug,
NOT-g:none), verify class hashes in S1/S2oracle proposals; parent rechecked6new ones.
Actual JVM8/JVM21/monolith outcomes plus signedstock:199values+2arithmeticfaults,
60programs/11classmetadata pages,2642 attempted instructions. No dropped argument
vectors/dedup-only count. Catalogue root uses S1 leaf/order encoding with schema3,
count201; outcomes and trace are TEST assertions, neverproduction inputs.

Signed in-process simulated backend (no listeners) and direct replay from SAME
signed transactions/sender recovery/nonce/transaction checks. Replaytwice under
identical explicit contexts for exactroots; signed walltimeheaders reported, not
fake globalroot equality. Pin actual module/parser bytes, metadata/code hashes,
coordinator immutableRefs/getters, input/program roots andstep counts/cells at every
checkpoint. Retain test-only traces independent of actualJVM final outcomes.

Extra required tests: dividend/divisor sign matrix inclMIN/-1 andMIN/-1 remainder0;
shift distances -1/MIN/MAX/0/31/32/33/63, unsigned high-bit results; signed/unsigned
narrowing; faultoperand prefix/local preservation, exactPC andsingle-count fault;
fault atcap vsbeforecap/return atcap; capbeforefault mustnotpredictfault; terminal
resume reject; dirty/reserve/OOGrollback before and after nonzeroprogress andwhile
attemptingfault, malformed replykind/pc/stack/lifecycle/tags. Wide unusedCode793 /
260literals discarded while loadWide's additional literal works; valid maximum32methods/256literals/
6336payload registration<=8M andliteral-heavy execution<=2M. Correctfixturebody
validity verifiedonJVM, not mislabeled uninitialized methods. Retain all S1 same-PC
loops, args0..4 (not6), eight-local and exact profile checks. No host SOE.

Parent adds separate java-stock-s2a-* targets; integrate runtime->harness->verifier,
independent probes plus S0/S1/legacy2231 allGoCLI/Python/artifact/boot/demos/AOT/vet.
Accept only after measuredgreen. Then re-evaluate static-call/frame architecture
with honest dirty/commit reserve before freezing S2b or another versioned stage.
