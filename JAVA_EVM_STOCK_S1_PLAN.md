# Stock S1: reusable EVM parsing and unchanged M1/M2 workloads

FROZEN implementation contract; authority JAVA_EVM_PROGRAM.md. Supersedes
alternative choices in JAVA_EVM_STOCK_S1_{ARCHITECTURE,ORACLE}_PROPOSAL.md.
Accepted base a6adae7: S0 separate stock foundation, M5d-a2231-case monolith
unchanged154839bytes SHA dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929.
S1 NOT accepted yet; no full-interpreter deployment or Minecraft claim. Target
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
