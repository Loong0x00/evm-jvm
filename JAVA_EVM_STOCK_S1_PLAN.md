# Stock S1: reusable EVM parsing and unchanged M1/M2 workloads

ACCEPTED after parent integration, independent review, fixes and final gates below.
Authoritative contract; authority JAVA_EVM_PROGRAM.md. Supersedes
alternative choices in JAVA_EVM_STOCK_S1_{ARCHITECTURE,ORACLE}_PROPOSAL.md.
Accepted base a6adae7: S0 separate stock foundation, M5d-a2231-case monolith
unchanged154839bytes SHA dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929.
S1 acceptance covers only this integer profile, not full-interpreter deployment
or Minecraft. Target
remains genuine unchanged MC startup-complete marker in original EVM; connectivity
optional,1.12.2 candidate. No server execution/EULA decision in this slice.

## Goal and evidence boundary
Migrate ALL82 unchanged M1/M2 manifest rows (5 rawclasses/39 roots), not wrappers
renamed run or a deduplicated subset. Named public static(I...)I entries,0..4 args,
6 observed locals, signed branches/goto/loops. Parent independently regenerated
all5 class hashes from the oracle proposal (javac --release8, default debug attrs):
Comparisons1115/Constants824/LocalsAndArithmetic845/Loops512/M1Baseline308bytes.
Raw vs STOP-prefixed page is +1 byte, not a disagreement between proposals.
82 JVM8/21/monolith outcomes agree; observed total2213 instructions, sum100806,
fibonacci30368, selectedCode<=24, CP<=28, stack<=2, locals<=6, entryname<=18.

Architecture prototype used host-supplied offsets/start maps and omitted production
parser/provenance. It is LOWER-BOUND cost evidence ONLY, never S1 conformance.
Production register/selection/cache/execution MUST derive everything in EVM.
Freeze budgets now as acceptance requirements; if complete parser/modules fail
measurements, report/refactor or parent re-freeze, not a silent cap increase.

## Non-negotiable boundary / preservation
Unchanged raw class bytes, opaque host packaging/ABI/signing/receipts only. All
class parsing, descriptors, selection, predecode, cached literals, branches,
argument-local initialization and transitions execute in ordinary deployed EVM.
No host class/Code metadata passed to execution, no host result/branch choices,
AOT/specialized generated executable or fallback to the monolith. JVM and monolith
are TEST oracles only. A bounded TEST-only trace model may assert checkpoints,
provided its results independently agree with actual JVM outputs and its metadata
never enters production calls.

Preserve S0 contracts/artifacts/ABI/tests and old2231 corpus/source/inputs/budgets.
S1 has new versioned contracts/package/counts. Do not edit core/vm/state/types,
consensus,params,precompiles,opcodes,gas rules/limits, or use host SetCode/SetState
or genesis executable/storage injection. Fund TEST EOAs only; ordinary CREATE and
signed transactions. No listeners/credentials/downloadedJava/EULA/global settings/
push/spawning agents/peer writes. Sol/high WITHOUT Fast/priority for all workers.

Defer calls, statics/clinit, classes beyond directObject, heap/ref/arrays, long/FP,
handlers/Throwable, libraries, String/main, JAR/platform and MC. Retain S0 integer
features even where the82 corpus does not use them. No full-class verifier claim.

## Write sets (one production Solidity writer)
Runtime ONLY new jvmevm/stock/s1/runtime/**: S1Types.sol,S1MetadataPage.sol,
S1ClassParser.sol,S1StepModule.sol,S1Coordinator.sol, optional shared metadata
codec/helper.sol, pinned build.js/packageJSON/lock/artifacts/*.json/runtimeREADME.
Harness ONLY new jvmevm/stock/s1/s1.go,s1_test.go and
jvmevm/testdata/stock/s1/** (catalogue commitments/additional trusted probes).
Read old cases.json/five sources/OracleMain without editing or copying modified
variants. Verifier ONLY new jvmevm/stock/s1/validation_test.go and README.md.
Package s1, helpers stockS1Harness*/stockS1Verify*. Parent owns Make/plans/guide,
integration and independent tests. Ignored build/java-diff-stock-s1-ROLE/ allowed.
Use accepted stock.LoadArtifact(stock.ArtifactPage) for raw pages, no S0 changes.
S1 LoadArtifact(name) returns stock.Artifact, names exactly S1MetadataPage,
S1ClassParser,S1StepModule,S1Coordinator. Embed only new runtime/artifacts/*.json;
additional immutable-reference access may mirror S0 without modifying S0 loader.

## Profile and error deferral
Raw Java52.0, payload1..4096, CP1..512 legal52 tags/two-slot/bounds as S0. Public
ordinary class directly extends java/lang/Object, no interfaces/fields/<clinit>;
class-level malformed structures/profile violations fail registerClass. Ordinary
ASCII internal class names as S0; no fake Object root or missing superclass.
Declared methods<=32; total cached integer literal records<=256. These NEW S1
profile caps keep metadata bounded, not changes to S0 or the monolith. Code cap
1..256, stack<=8, locals<=8 apply to selected entries; no handlers.
Entry bytes1..64, ordinary ASCII unqualified method name (reject NUL,nonASCII,
. ; [ / < > and empty). One unambiguous declared name regardless of descriptor.
Root public static, no contradictory visibility/synchronized/native/abstract flags,
exact(I...)I argc0..4, maxLocals>=argc, exactly one valid bounded Code attribute.

Register scans all outer method/attribute structures. It records per-method
eligibility/errors instead of failing the whole class for an unused unsupported
method/constructor. Selection priority: missing/ambiguous -> access -> descriptor
-> Code count/caps/handlers -> bytecode validation. Public eligible int Code is
predecoded completely, including unreachable instructions; record first precise
bytecode error, don't execute/skip it. Later selecting that record raises its exact
recorded error. A malformed outer member/attribute length/index remains a class
error at registration. Internal malformed/unsupported Code is a method error when
selected, not false success. Discard partial literal records for invalid methods.

S0 opcodes plus99..a4 (unary/binary signed-int conditional branches),a7 goto.
Signed16 offsets relative to BRANCH OPCODE PC. Second predecode pass validates ALL
branch targets: signed math before unsigned cast,0<=target<CodeLen, target startbit.
Zero-offset self-loop valid. Step rechecks target defensively, including incoming
PC start. Java int32 modulo behavior, exact tagged cells and initialized loads/iinc
retained. No division/exceptions or other unsupported opcode fallback.

## Parse once and exact metadata format
S1ClassParser reads accepted STOP||raw pages with EXTCODE*, verifies code/payload
hashes, parses/derives metadata in EVM, then ordinary internal CREATE of
S1MetadataPage(bytes payload). Metadata runtime EXACT STOP||payload, no mutable API,
payload<=8191/runtime<=8192. Raw ArtifactPage stays S0's<=4096 payload.

Metadata payload is6 header words,4 words per declared method, then8-byte literal
records. Header/words ABI-style32-byte big-endian; packed fields use low bits as
below. Literal tuple fields explicitly big-endian. No self-hash cycle.
 H0=keccak256("JVMEVM:S1:METADATA:2").
 H1=uint160(rawPage) | (uint256(classAccessFlags)<<160); bits>=176zero.
 H2=rawPageCodeHash; H3=rawPayloadHash; H4=keccak256(raw declared class-name bytes).
 H5=rawLength:u32[0..31] | cpCount:u16[32..47] | methodCount:u16[48..63]
    | literalCount:u16[64..79]; bits>=80zero.
For each declared method (in original order), four words:
 M0=keccak256(raw method-name bytes); M1=keccak256(raw descriptor bytes).
 M2 packed:
  declaredIndex:u16 bits0..15; access:u16 bits16..31;
  codeOffset:u32 bits32..63 (payload-relative, prefix excluded);
  codeLength:u16 bits64..79; maxStack:u8 bits80..87; maxLocals:u8 bits88..95;
  argc:u8 bits96..103; errorDomain:u8 bits104..111;
  errorCode:u8 bits112..119; errorLocation:u32 bits120..151;
  literalBase:u16 bits152..167; literalCount:u16 bits168..183;
  bits>=184zero.
 M3=256-bit instruction starts, bit pc set for opcode at relative pc.
errorDomain0 eligible,1 S1MethodError,2 S1BytecodeError. Ineligible codeOffset,
codeLength,maxStack,maxLocals,argc,literalBase/literalCount and M3 are all zero;
errorLocation for domain1=method index,domain2=offending relative PC. Domain0 has errorCode/location0. Preserve original
name/descriptor hashes/index/access even when ineligible. Error checks need not
invent a truncated maxStack/argc; clear Code-derived fields when outside profile.
Literal records (only valid methods) sorted by method index then PC:
 (methodIndex:u16,pc:u16,bits:u32),8bytes each. literalBase is RECORD index, notbyte
address. Header+32*128+256*8<=6336 bytes, below8KiB. Exact payload length must match
counts, no trailing bytes. Metadata code hash commits all literals; no extra root
word required. Step resolves ldc/ldc_w from this EVM-derived table, no CP rescan.

Domain-separated roots use abi.encode (NOT ambiguous packed concatenation):
 Dclass=keccak256("JVMEVM:S1:CLASS"), Dprogram=keccak256("JVMEVM:S1:PROGRAM"),
 Dinput=keccak256("JVMEVM:S1:INPUT").
 classId=keccak256(abi.encode(Dclass,uint32(2),parserCodeHash,rawPage,
          rawPageCodeHash,payloadHash,metadataCodeHash)).
 programId=keccak256(abi.encode(Dprogram,uint32(2),classId,uint16(methodIndex),
          entryHash,descriptorHash,moduleCodeHash)).
 argsHash=keccak256(abi.encode(int32[] args)).
 inputRoot=keccak256(abi.encode(Dinput,programId,argsHash,uint64(maxTotalSteps))).
 stateDigest=keccak256(abi.encode(uint32(2),inputRoot,parserCodeHash,moduleCodeHash,
          machine,uint64(epoch),uint64(totalSteps))).

Parser no constructor args. registerClass(address page,bytes32 expectedPageHash,
bytes32 expectedPayloadHash) returns(bytes32 classId,address metadataPage,
bytes32 metadataHash,uint16 declaredMethods).
classRecord(bytes32 classId) view returns(address metadataPage,bytes32 metadataHash).
Append-only registry, no update/delete. Same raw page/hashes registration is
idempotent: same classId/page, no second CREATE/write/event. Maintain an internal
lookup keyed by page/hashes if needed to deduplicate before metadata creation.
Unknown classRecord returns zero pair. Internal CREATE failure reverts whole
registration; no partial registry/code remains. ClassRegistered event ONLY first:
 ClassRegistered(bytes32 indexed classId,address indexed rawPage,address metadataPage,
                 bytes32 metadataHash,uint16 declaredMethods).
A hash supplied for arbitrary parser/module is a configuration commitment, NOT
attestation: actual deployed bytes must match pinned compiler artifacts in gates.

## Frozen shared Solidity ABI (S1Types)
struct MachineV2 {
 uint32 pc; uint8 sp; uint8 initialized; uint8 lifecycle;
 uint256[8] stack; uint256[8] locals; int32 result;
}
lifecycle0RUNNABLE,1RETURNED,2STEP_LIMIT. Int=(uint256(1)<<64)|uint32(bits), noother
bits. Inactive stack/uninitialized or out-of-range locals zero. Args initialize
locals0..N-1 with lowN initialized bits. result0 unlessRETURNED; returnedsp0.
STEP_LIMIT preserves current stack/locals/PC, not fabricated Java result/exception.

struct ProgramContext {
 address parser; bytes32 parserCodeHash; bytes32 classId;
 address rawPage; bytes32 rawPageHash; bytes32 payloadHash;
 address metadataPage; bytes32 metadataHash; uint16 methodIndex; bytes32 programId;
}
S1StepModule has no constructor args/state. step(ProgramContext calldata program,
MachineV2 calldata beforeState,uint16 budget) view returns(MachineV2 afterState,
uint16 executed). budget1..128, input lifecycle0 only. Verify parser/metadata/raw
code hashes and parser.classRecord(classId), header/root consistency and exact
method record/provenance; don't treat caller metadata as authority. Recompute
classId/programId with actual executing module codehash. Copy only selected raw
Code/needed metadata/literals. Selected error records fail, cached-literal mismatch
fails. ProgramContext passes no host Code/offset/startmap values.

S1Coordinator constructor(address parser_,bytes32 expectedParserHash_,bytes32 classId_,
address module_,bytes32 expectedModuleHash_,bytes entry_,int32[] args_,uint64 maxTotalSteps_).
Verify nonempty deployed parser/module and hashes, registry-issued metadata/page
hashes/header, computed classId; select entry IN EVM, enforce ambiguity and recorded
errors, check args count, initialize tagged locals; commit programId/argsHash/inputRoot.
maxTotalSteps1..4096. No mutable entry/args/cap/component configuration afterward.
Expose public immutable getters parser,expectedParserHash,module,expectedModuleHash,
classId,programId,argsHash,inputRoot,maxTotalSteps; expose programContext() view
returns(ProgramContext). No requirement to retain raw entry/args bytes aftercommit.

resume(uint64 expectedEpoch,uint16 maxJvmSteps,uint8 maxDirtyWords) returns
(uint64 newEpoch,uint8 lifecycle,int32 result,uint16 executed,uint8 dirtyWords).
checkpoint() view returns(uint32 schema,bytes32 classId,bytes32 programId,bytes32 inputRoot,
uint64 epoch,uint64 totalSteps,bytes32 stateDigest,MachineV2 machine).
Event CheckpointV2(uint64 indexed epoch,bytes32 indexed programId,uint64 totalSteps,
uint32 pc,uint8 sp,uint8 lifecycle,int32 result,uint16 executed,uint8 dirtyWords,
bytes32 stateDigest). One per success, none survives failed transaction.

## Loop-safe progress, step limit and atomicity
No S0 same-PC guard! An identical PC or even identical Machine can be legitimate
loop progress. Require executed1..effectiveBudget, epoch+1, totalSteps+=executed.
EffectiveBudget=min(requested1..128,remaining committed maxTotalSteps). Module
returns lifecycle0 or1; coordinator sets2 iff remaining allowance consumed AND
no return. RETURNED wins at exact step cap. STEP_LIMIT never reported asJava int0,
JavaException or EVM OOG. Further resume after lifecycle1/2 rejectsControl1.

Safepoints between COMPLETE instructions only. No arbitrary gas-derived skip/pause
or partial branch. Reentrancy protection, immutable component/hash checks, canonical
module result/ABI validation, current-gas recheck AFTER calldata/state preparation,
explicit bounded STATICCALL stipend retaining800000 reserve+margin. Retain S0
861c8c2/c62cec4 lessons. Module reverts/OOG bubble unlabelled, not Java outcomes.
Validate changed-word count before committed writes; all transaction VM changes/
logs rollback on error, previous checkpoint remains. EOA gas/nonce effects normal.

Dirty count=3(header epoch,totalSteps,digest)+changed pc/sp/initialized/lifecycle/
result logical words+changed8stack/8local words (<=24). Verify conservative>=actual
changed persistent slots; lock scratch gas included but not committed machine.
maxDirtyWords1..32; insufficient count rejectsControl6 beforewrite. cap-induced
lifecycle change counted. uint64 counters guarded, although total<=4096 bounds them.
No outside actor can choose PC/state/branch/result through resume.

## Exact errors
Reuse StockPageError(uint256 code) semantics1size/2prefix/3codehash/4payloadhash
for raw pages. Metadata/component/provenance malformed errors are S1Control2.
S1ClassError(uint256 code,uint256 offset):1 outer trunc/boundary/extra bytes;
2 magic/version;3 CP/tag/index/two-slot/name chain;4 class profile/name/super/fields/
interfaces/clinit;5 class/method/literal/metadata count or capacity;
6 metadata CREATE/registry consistency. Offset rawpayload-relative; wholeclass cap
location use method_count offset for method cap,0 for aggregate literal/metadata cap.
S1MethodError(uint256 code,uint256 index):1 missing(MAXuint256 index),2 ambiguous
(second matching declared index),3access,4descriptor,5Code count/caps/handlers/
malformed internalCode/locals<argc,6reserved unsupported method,7args count,
8invalid entry bytes(MAXuint256). Recorded domain1 uses declared index as location.
ClassError remains immediate for malformed outer attr bounds/CP refs.
S1BytecodeError(uint256 code,uint256 pc): retain S0 meanings2trunc,3underflow,
5returnshape,6unsupportedopcode/ldc kind,7fallthrough,8localrange,9stackcapacity,
11uninitialized,12nonstart/inputPCrange,14invalidMachine/tag/state;15invalidbranch
target,16missing/mismatched cached literal. Record first failed predecode with exact
PC; second target pass only after widths/operands valid. Incoming malformed Machine
or unavailable selectedmetadata in direct step cannot cause opaque Solidity panic.
S1ControlError(uint256 code):1terminal,2component/hash/provenance,3staleepoch,
4budget/caprange,5gasreserve,6dirtycap,7invalidmoduleresponse/counterstate.
STEP_LIMIT is an explicit success checkpoint lifecycle, NOT an error code.
Checks select/access/descriptor/Code before args mismatch; component validation before
selection. Isolate single mutations in negatives; don't erase precise failure layers.

## Budgets and reproducibility
Pinned solc0.8.30 optimizer200 viaIR Cancun metadataoff, stable JSON as S0 with
abi/bytecode/deployedBytecode/immutableReferences/sourceHashes. Build reads Solidity
ONLY; no Java/case inputs. Reuse S0 raw ArtifactPage artifact exactly. New parser
runtime<=16KiB, other executables<=12KiB, initcodes<=24KiB; metadata runtime<=8KiB.
CREATE/registerClass<=8Mgas, resume<=2M, reserve800k, Osaka2^24 txlimit and30M block
context unchanged, chain1337. Parser gas/provenance not proven by host-metadata
prototype; failure to fit demands measured design change, not hidden caps/shortcut.

82 primary cases ALL run signed at64 and128 steps, maxTotalSteps1024. At64 atmost
13resumes(sum100), isolated setup4tx(parser,module,rawpage,register)+coordinator+
resumes<=19 external success tx. Internal metadata CREATE gas included inregister.
Each isolated case full setup+execution<=30M positivegas. Shared gate setup12external
tx (parser/module +5rawpages+5register), then82freshcoordinators perbudget; report
actual setup, registration, coordinator, each resume, positive/failed aggregate,
per-case isolated vs shared/amortized costs separately. Never edit oldcasegas_limit.
Small-budget1/7/16 fully test every non-loop82case; longloops use boundedprefixes
and whole64/128 runs, not pretend806 quantum1resumes meet19txcase bound. Explicit
samePC sum100/64 and quantum16 prefix; finite selfloopEVM-only reachescap1/128/4096
without running infinite host Java. Protocol-negative transactions separatelycounted.

## Harness and independent gates
Read ALL82 rows stage m1/m2 in existing cases.json order, preserving IDs,args,sources,
legacy gas budgets. Compile same5sources/command (--release8 WITHOUT -g:none),
check exact5hashes in oracle proposal/parent rebuilt evidence, actual JVM8/21 and
monolith values. Produce catalogueCount82 and deterministic test-only commitment:
 leaf=keccak256(abi.encode(uint32(2),uint16(index),keccak256(bytes(caseId)),
 rawPayloadHash,keccak256(bytes(binaryClassName)),entryHash,descriptorHash,argsHash));
 root=keccak256(abi.encode(uint32(2),uint16(82),bytes32[] orderedLeaves)).
Pin/check catalogue in NEW testdata; bind each row to actual coordinator program/
input roots and receipts, no source filtering or dropped argumentvectors. Expected
outcomes/trace metadata are assertions ONLY, never supplied to production VM.
Five parsed pages reused across39programIds/82inputs; retryregistration reusespage,
changedentry/args gives appropriatechangedroots but unchanged classmetadata.

Signed in-process simulated backend (noP2P/HTTP/WS/IPC listeners) plus direct replay
of signed transactions with sender recovery/nonce/transaction checks. Repeatdirect
replay with identical explicit contexts for exactroots; signed walltimeheaders
reported, compareVMdigests/gas not fictitious globalroot equality. Exactactualcode/
pagebytes/metadatahash/getters/immutableRefs checked; no code/storage injection.
Tests may independently decode raw/metadata and trace trusted Java for assertions,
not pass that analysis into on-chain parsing. Real JVM validates every finalvalue.

Independent negatives include catalogue46 intents with frozen codes above; invalid
branches inclunreachable/middleoperand/MINsigned target; arg min/max/count/local6;
unused unsupported vsselectederror; CP512/Code256/literal table/order/cap; matching
fake metadata not issuedbyparser, wrongpage/parser/module/root/hash; duplicate
registration; malformedrecord/responses; staleepoch/dirty/OOG/reserve threshold
before andafter progress; exactcap vsreturnprecedence/selfloop; all-dirtybounds;
parserregistration failure leaves no entry/page; standardEIP170/3860/7825 layers.
Use normally deployed mismatching inputs for negativeprovenance, never SetCode.

Retain S0all8fixtures/parent80+42/reviewboundary and old2231/allGoCLI/Python/artifact/
bootstrap/demos/AOT/vet gates. Parent adds separate java-stock-s1-* targets/counts,
integrates runtime->harness->verifier and independentlyprobes beforeacceptance.
Then choose next real semantic migration by measureddependencies, not an assumed
mechanical split or a claim that one integer stage supplies Java/Minecraft.

## Parent acceptance record

Integrated runtime da94a82, harness/catalogue38cfa43, verifierb01b9e6 and independent
review2160e65. Parent optimization/valid-boundary/probes c4391cc, gates2259e4a,
review success-required transition921d822. Final logs:
/tmp/stock-s1-legacy-main.log and /tmp/stock-s1-final-other.log; both .exit files0.

All82 unchanged rows,5rawclass hashes,39programs and2213 exact dynamic instructions
passed JVM8/JVM21/monolith comparisons and signed Stock S1 at64/128, plus small
budgets/prefixes, same-PC progress and deterministic direct signed replays. Catalogue
root0xf98038bd7cb12d165c0b22dd7feca869803efce86a8194f4a3ddb1973f84764b
binds all82 rows; no deduplication of argumentvectors or oldgas-limit changes.

Real EVM parser/factory issued five immutable metadata pages, reused for all roots/
arguments. Shared setup12transactions/11790544gas on final artifacts. The full signed
harness matrix (including repeated small-budget/prefix instances and idempotence
checks) reports1173 transactions/831940953gas, NOT one transaction/case. Per-case
stock costs are separate from legacy invocation budgets. Representative full costs:
- sum(100),64steps:13resumes/18isolatedtx,11211708isolatedgas, value5050/806steps;
- sum(100),128steps:7resumes/12isolatedtx,10324488isolatedgas;
- fibonacci(30),64steps:6resumes/11isolatedtx,9562809gas,value832040/368steps;
- fibonacci(30),128steps:3resumes/8isolatedtx,9055443gas.
Signed wall-time headers are recorded, not falsely claimed identical. Direct replay
under identical explicit contexts compares exact roots, gas and canonical checkpoints.

Parent independently addressed both review findings, not by raising budgets:
1. The aggregate fixture's27 no-literal methods read uninitialized local0. Replace
   with same-length iconst0/ireturn; method/literal/metadata sizes unchanged. Real
   JVM8/21 executes all31 public methods; EVM executes all four nonempty literal
   slices and the final zero-literal method. Original invalidshape retained as
   negative: all27records domain2/code11/pc0, selecting m04 throws exactBytecode11.
2. Bytewise metadata-page constructor copying caused the valid maximum to exceed
   8M. Standard Cancun MCOPY into fresh STOP-prefixed allocation reduces the SAME
   valid parent sequence8449776->6923070gas, keeping32methods/256literals/6336payload.
   Review sequence now6942970gas at8M, after a separate6M failure proving parsernonce,
   registry, internalCREATE code and logs roll back. No12M acceptance-test budgets.

Parent additionally ran48 JVM8/21 eight-local/min-max/overflow/loop cases at64/128,
including a quantum1prefix and dirty-budget rollback/retry;52 gas-threshold probes
with four args/eight locals before andafter progress. All pass. S1 parser includes
bounded int-only stack-height/definite-local flow checks with deferred method error
records; this is NOT a full classfile/StackMapTable/Java verifier.

Final pinned runtime templates:
- S1ClassParser15271bytes SHA256
  72003f0a79f1d724f667afb38d869c9c48e94585a0f60d82ac7871a7b230ec80;
- S1StepModule8408bytes SHA256
  9c70f525c57139efdae676555ada7fc28dfc307be1694376f7e525a675dcee35;
- S1Coordinator6328bytes SHA256
  957472808404f19124cb5b5f8440e5186d8d3f7eec60da9451fb150a2a37e9f8.
Metadata dynamic actualmaximum tested6337bytes (STOP included), cap8192. Coordinator
actualdeployedhashes/immutable references/getters verified, not confused with template.
All contracts registered/deployed through ordinary CREATE, not host code injection.

Pinned S1 build/check/test/demo, S0 check/test/demo, all2231 legacy JVM/EVM cases,
GoCLI/36Python/24bootstraps/artifact/1040smoke/1060fast/demos/AOT/focusedvet green.
No modifications to S0 runtime, monolith, legacy inputs/budgets, core/EVM/params/
consensus. Evidence and historical measurements: JAVA_EVM_STOCK_S1_REVIEW.md.

Next proposal preflight: measured completion of integer families and ordinary
static-call/frame migration (compare exact M2b/M3a workloads), with persistent
frame/state design rather than copying the whole interpreter memory graph. No
next implementation frozen. S1 still has no calls/heap/FP/handlers/libraries/MC;
M5d-a's full2231 profile remains a separate local-runtime interpreter.
