# Stock S2b-L: production EVM call-metadata registration

FROZEN contract; authority JAVA_EVM_PROGRAM.md. Supersedes alternative/prototype
choices in JAVA_EVM_STOCK_S2B_{LINK,FRAME}_PROPOSAL.md. Accepted S2a ff28bcd,
S1/S0 and the2231-case monolith remain unchanged. This stage is REGISTRATION/LINK
ONLY: no frame store, Java call execution, SOE, 268-row stock-execution or MC claim.
No Minecraft/EULA/listener action. Goal remains genuine MC startup in original EVM.

## Parent review and scope decision
Parent integrated proposals acab8dd/07d483c, verified link SHA256SUMS from its
worktree ROOT and reran TestEVMRegistration: all14rawclasses and51M3a callrecords,
valid32methods/256literals/32calls cap7936payload,7864288gas at8M. This confirms
real EVM registration evidence, not execution through a Java frame machine.
Frame evidence is STORAGE-ONLY lower bound: reversible5physicalword frames and
4touched IDs are promising, but no integratedsemantic/reserve proof yet. Do not
mix unmeasured frame production into this link slice.

Prototype weaknesses MUST NOT ship:
- len+1 linear flow queue is not a general enqueue bound. Use a bounded ring/
  worklist with per-PC in-queue deduplication and prove convergence; no valid CFG
  rejected merely because nodes require revisiting.
- Call resolution must not read already-mutated analysis results of earlier
  methods. Separate immutable declaration/envelope analysis from final body/error
  results so equivalent declaration permutations do not change eligibility.
- Idempotence must return real counts, not zero placeholders.
- Bounded canonical analyzer response/provenance validation and S2a reparse adapter
  must be implemented/tested. Prototype hash pair is commitment, not attestation.

## Immutable execution boundary / write sets
All raw class parsing/CP/name+descriptor resolution, flow analysis, literal/call
cache generation, adapter source extraction and metadata issuance run in ordinary
EVM contracts. Host only opaque bytes/signing/ABI/artifacts/receipts and TEST
oracles. No host offsets/CP/callee/Code/metadata/outcome in production, no AOT or
fallback, SetCode/SetState/genesis code/storage injection, changes to core/EVM/
params/consensus/precompiles/gas/protocollimits/global settings. Fund TEST EOAs only.
No peer writes/push/agent spawning/untrustedJava/listeners/MC/EULA. Sol/high NOFast.

Runtime ONLY new jvmevm/stock/s2b/runtime/**: S2bTypes,MetadataPage,AnalyzeModule,
ClassLinker.sol, optional internalcodec/helper.sol, pinned build/packages/lock/
artifacts/README. NO FrameStore/Step/Coordinator executable yet.
Harness ONLY new jvmevm/stock/s2b/link.go,link_test.go and
jvmevm/testdata/stock/s2b-link/** (new registration catalogue/cap/CFG fixtures).
Verifier ONLY new jvmevm/stock/s2b/validation_test.go and README.md.
Package s2b, helpers stockS2bLinkHarness*/stockS2bLinkVerify*; parent owns Make/plans/
guide/integration/independent tests. Preserve ALL old stock/monolith/source/case/
gas/ABI files; use accepted stock.LoadArtifact(ArtifactPage) and s2a.LoadArtifact
(S2aClassParser) READ-ONLY for setup/adapter tests. New LoadArtifact(name) returns
stock.Artifact; names S2bMetadataPage,S2bAnalyzeModule,S2bClassLinker, with independent
immutable-reference access as prior. Ignored build/java-diff-stock-s2bl-ROLE/ allowed.

## Supported declaration/Code/link profile
Java52.0, raw1..4096, CP1..512, ordinary public direct-Object class, no interfaces/
fields/clinit, ASCII ordinary internal class names. Same bounded CP two-slot/tag/
chain/outer attribute checks as S2a. Declaredmethods<=32, eligibleCode1..256,
stack/locals<=8, eligibleliteralrecords<=256, eligiblecallrecords<=32.
Internal methods may be public/protected/package/private, but static, nonsynchronized,
nonnative/nonabstract and otherwise valid flags, exactlyone boundedCode/nohandlers,
exact(I{0..6})I or(I{0..6})V and maxLocals>=argc. Constructor reserved/ineligible;
clinit remains immediateclasserror. Future roots will require public unambiguous
name and I return, but L adds NO executable root selector or resume API.

Retain all S2a int instructions/branches and add pop57, invokestaticb8, returnb1.
All selected-profile method bytes predecoded inclunreachable widths/operands/local/
CP/branch targets. Flow checks tagged-int stack heights and definite locals. ireturn
requires I descriptor and exactlyone stackint; return requires V descriptor and
empty stack. pop needsone. Invoke needs descriptor argc, leaves I value or nothing.
Recursive call graphs are cached records, never recursive analyzer execution.
Unentered oversized Wide.populateIntegerPool Code793/260literals remainsineligible;
loadWide's one genuine wide literal remains. No partial ineligible caches leaked.

## Order-independent analysis and deferred errors
Phase A: establish immutable declaration envelopes for EVERY method: raw name/
descriptor hashes, access, descriptor effect and Code envelope or method error.
Phase B: predecode/link/flow each base-eligible body using ONLY those Phase-A
envelopes. Store body Analysis results separately; memory struct aliases must not
mutate envelopes during analysis. Phase C: build final method records/caches.

For b8: require operand CP tag10 (tag11 is unsupported call-kind), well-formed
Class/NameAndType/Utf8 references, owner name exactly thisclass, ordinary target
name, exact unique declared name PLUS descriptor. Target Phase-A envelope must be
static/profile-usable; private/protected/package access legal within this class.
Argument/return effects come from target's validated descriptor. Reserved init/
clinit targets forbidden. Missing/duplicate exacttarget, externalowner, wrongkind,
unusable access/descriptor/Code envelope get deferred caller call errors.

IMPORTANT: a valid symbolic call MAY reference a target whose final BODY has a
bytecode/call error. It still gets a stable callrecord derived from the immutable
usable envelope; do NOT transitively/order-dependently mark its caller invalid.
Target's own finalrecord retains the bodyerror. Future execution must check target
error before use/entry (not frozen here). Only Phase-A-unusable targets yield caller
Call4. A target bodyerror has cleared final argc/return fields, so consumers must
not equate those zeros to its descriptor effect; use record error first. This is
explicit selected/entered-profile policy, not full JVM verification conformance.

Discard ALL literals/calls/starts for any ineligible final method. Eligible-only
aggregatecaps checked after complete body analysis. First widths/operands, then
all signed-target checks, then reachable flow. Equal stack height at joins, init
bits intersect. Queue must support re-enqueue after stricter init joins. With max8
localbits each PC first-visits once and can lose bits at most8 times; a deduplicated
ring has at mostCodeLen queued simultaneously. Reject true invariant failures,
not valid revisits. Preserve first deterministic error within these passes.

## Exact schema-4 metadata
Runtime page=STOP||payload, immutableconstructor-only S2bMetadataPage(bytes payload),
max8191payload/8192runtime, bounded MCOPY. Payload exactly
256 + methods*160 + literals*8 + calls*16 (maximum7936, runtime7937).
Words big-endian32bytes; packed bitfields low-bit offsets; compact records big-endian.
H0=keccak256("JVMEVM:S2B:LINK:METADATA:4").
H1=uint160(rawPage)|(uint256(classAccess)<<160),bits>=176zero.
H2=rawPageCodeHash; H3=rawPayloadHash; H4=keccak256(rawclassname bytes).
H5=rawLength:u32[0..31]|cpCount:u16[32..47]|methods:u16[48..63]|
 literals:u16[64..79]|calls:u16[80..95],higherbitszero.
H6=ACTUAL analyzer runtime EXTCODEHASH (not prototype revision placeholder).
H7=zero.
Five words per declaredmethod, original order:
 M0 nameHash; M1 descriptorHash;
 M2 index:u16[0..15], access:u16[16..31], codeOffset:u32[32..63],
 codeLen:u16[64..79], maxStack:u8[80..87], maxLocals:u8[88..95],
 argc:u8[96..103], returnKind:u8[104..111](0V/1I),
 errorDomain:u8[112..119], errorCode:u8[120..127], errorLocation:u32[128..159],
 literalBase:u16[160..175],literalCount:u16[176..191],
 callBase:u16[192..207],callCount:u16[208..223],higherbitszero;
 M3 instruction starts bit pc; M4 zero.
Domains0eligible,1MethodError,2BytecodeError,3CallError. Eligible errors0. Ineligible
codeOffset/len/stack/locals/argc/returnKind/literalbase/count/callbase/count/M3 all0;
retainindex/access/name/descriptor and exacterror. Domain1location=methodindex;
domain2/3location=opcodePC. These are data records, not executable Java stubs.
Literals (method:u16,pc:u16,bits:u32),8bytes sortedmethod/PC.
Calls (caller:u16,pc:u16,cpIndex:u16,target:u16,argc:u8,returnKind:u8,
 flags:u16=0,reserved:u32=0),16bytes sortedcaller/PC. Bases are RECORDindices.
No trailing bytes, reservedbit misuse, duplicate/unsorted site records or fabricated
callee targets. Future executor must compare cached cpIndex against raw b8 operand.

classId=keccak256(abi.encode(keccak256("JVMEVM:S2B:LINK:CLASS:4"),uint32(4),
 ACTUAL linkerCodeHash,analyzerCodeHash,rawPage,rawPageHash,payloadHash,metadataHash)).
MetadataHash is EXTCODEHASH of STOP||metadata. Actual linker hash includes ctor
immutables, not raw compiler template. No programId/inputRoot/active frame yet.

## Frozen component ABI / issuance and adapter
S2bAnalyzeModule no constructor args:
 analyze(bytes calldata raw,address page,bytes32 pageHash,bytes32 payloadHash)
 external view returns(bytes metadata,uint16 methods,uint16 literals,uint16 calls).
Verify raw length/hash, actual page codehash/size/prefix and that pageHash commits
STOP||raw; analyze rawbytes only. H6 uses address(this).codehash. Stateless direct
analysis does not issue registry entries. Generic code never reads host field maps.

S2bClassLinker constructor(address analyzer_,bytes32 expectedAnalyzerHash_,
 bytes32 acceptedS2aParserHash_). Nonemptyanalyzer/hashmatch and nonzerolegacyhash.
Public immutable getters analyzer,analyzerCodeHash,acceptedS2aParserHash.
 registerClass(address page,bytes32 expectedPageHash,bytes32 expectedPayloadHash)
 external returns(bytes32 classId,address metadataPage,bytes32 metadataHash,
 uint16 methods,uint16 literals,uint16 calls).
 classRecord(bytes32 classId) view returns(address metadataPage,bytes32 metadataHash).
 registerFromS2a(address oldParser,bytes32 oldClassId) external returns SAME6fields
 as registerClass.
Event ClassRegistered(bytes32 indexed classId,address indexed rawPage,address metadataPage,
 bytes32 metadataHash,uint16 methods,uint16 literals,uint16 calls), only firstissuance.
Append-only/idempotent by rawpage+hashes: retry returns all REAL counts/sameID/page,
no secondCREATE/write/event. Unknownrecordzero. Check analyzer codehash on every
path including retry. Componenthash is configcommitment, not attestation; gates
pin actualdeployedcompiler bytes and acceptedS2a hash. No upgrades/setters.

Linker reads page itself, calls pinned analyzer, and accepts bounded canonical
returndata ONLY: fourheadwords (offsetexact128,three canonicalcounts), thenbyte length
and exactpaddedpayload. Maximum8096bytes; checkRETURNDATASIZE before allocating/
copying arbitraryreturn data. No malformed offsets/highbits/nonzero padding/trailing
bytes. Header/rawidentities/H6/magic/reserved/counts/dimensions must match; do not
reparse Java or duplicate analyzer's entireflow work. Per-record semantics are
analyzer responsibility under pinned-code attestation, not an excuse to trust any
selfdeclared hash as a real analyzer. Malformed responses fail hard, not Java faults.
Bounded call/revert propagation; metadataCREATE failure/outer OOG rolls back registry,
internalpage/nonce andevents. No fake pause or successful partial registration.

Adapter pins oldParser EXTCODEHASH to acceptedS2aParserHash, calls its classRecord
with bounded canonical64-byte response. Verify nonzeroissued oldpage/hash, actual
oldmetadata hash/STOP/size and exact six-header schema3S2a shape/count/length,
H0keccak256("JVMEVM:S2A:METADATA:3"), H1/H5reservedbits, and recompute oldClassId
using acceptedS2a DCLASS/schema3/oldparserhash/rawpage/rawhash/payloadhash/oldmetahash.
Extract ONLY rawpage/H2/H3. Use identical _registerClass raw-reparse path; nevercopy
S2a method/literal/Code-derived records as authority. Result equals direct new
registration for same rawpage, whether adapter or direct was first. Oldrecords/
pages/livecoordinators untouched. Test importing old-ineligible private/call/void
methods becoming correctly classified in schema4. No in-place state upgrade claim.

## Error contract
Raw pages: existing StockPageError(uint256) codes1size/2prefix/3codehash/4payloadhash.
S2bClassError(uint256 code,uint256 rawOffset):1 outerbounds/trailing;2version;
3globalCP/tag/index/namechain/two-slot;4classprofile/field/interface/clinit/name;
5methods/literals/calls/metadata caps;6metadataCREATE/registryconsistency.
Aggregatecapoffset0; methodcountcap at method_count offset. Outer malformedCPchains
fail Class3 even if a method would later have a Call error.
S2bMethodError(uint256 code,uint256 methodIndex), represented domain1:
3internal flags/static/profile;4descriptor;5Codecount/caps/handlers/locals<argc/
malformedinternalCode;6reservedconstructor. No rootselection API in L.
S2bBytecodeError(uint256 code,uint256 methodIndex,uint256 pc), domain2:
2trunc;3underflow;5returnshape/descriptor mismatch/joinheight;6unsupported;
7fallthrough;8localrange;9stackcapacity;11uninitialized;12invalidPC;
14true internalanalysis invariant;15branchtarget;16literalcache.
S2bCallError(uint256 code,uint256 callerMethodIndex,uint256 pc), domain3:
1b8operandindex/tag (including tag11) or remaining malformedcall chain;
2externalowner;3missing/duplicate exactname+descriptor;
4reserved target or unusable Phase-A flags/descriptor/Code envelope.
These metadata errors are deferred, not registration reverts unless class-level.
S2bLinkError(uint256 code):1analyzeraddress/hash;2analyzerreply/header/ABI;
3legacyparserhash;4legacyregistryreply/page/hash;5legacyheader/classidentity.
No Java-origin faults/outcome decoder in registration-only L. No Solidity panic
or guessed success replaces a specified error. Negative tests isolate one defect.

## Gates, caps and ownership discipline
Pinnedsolc0.8.30/optimizer200/viaIR/Cancun/metadataoff; artifact JSONsame priorformat
with abi/bytecode/deployedBytecode/immutableReferences/sourceHashes. Build consumes
Solidity ONLY. Go LoadArtifact returns stock.Artifact for S2bMetadataPage,
S2bAnalyzeModule,S2bClassLinker; embeddednewJSON. No executable frames or hostmetadata.
Analyzer<=20KiB runtime (prototype17710 does NOT fit prior16KiBproject target);
linker<=12KiB, initcodes<=24KiB, rawpage<=4097/metadata<=8192. All originalprotocol
limits unchanged. CREATE/register/direct AND adapter registration<=8M gas, standard
Osaka2^24 and30Mblock/chain1337. No resume budget because no resume operation yet.
Actual production checks/ring/adapter must preserve8M gate; refactor/report, never
raise it or omit dense valid CFGs. Replay gas includes internalmetadata code deposit.

Require all14 exactrawclass hashes from proposal, realEVM registrations with
14+16+21=51M3a call records independently decoded against rawb8/name/descriptor/
flags/target/argc/return. Preserve268-row/94root catalogue and originalJVM/monolith
outcomes in TEST evidence ONLY, no 268stock-execution count. Direct andadapter
registration sameclassID/page/counts; adapt11S2a classes plus at leastone M3a class
oldS2a can register but notexecute. Metadata pointsprivate/void/sixarg/overloads/
recursive graphs correctly, all oldS2a opcode/literal/cache cases retained.

Pin exact prototype validcap rawSHA256
0e3e962a3de46d9c019c8e8e3e846b304622fc969144713f9ad6922c33946f33
(3574raw/32methods/256literals/32calls/7936metadata) as additional NEW testfixture,
unchangedbytes to JVM8/21 andEVM. KeepClass32/33, literal256/257, call32/33, metadata
limits and maxCode/CP, plus dense/revisit CFG valid regressions. Prototype queue
shortcut must not be counted as proof. Counterexamples require actualJVM validation
when feasible; malformed-target negatives are EVMpolicy tests, not fake JVM parity.

Independent negatives: all malformedCP/tag/chains, external/interface refs, missing/
duplicate exacttarget, reserved/nonstatic/native/abstract/sync/bad descriptor/Code;
return I/V mismatch, pop/invoke arity andsixargs, bad signedtargets/uninitialized/
joinheight, unreachableunsupported; declaration-order permutation invariance with
invalidbody target andstable phaseAcall cache; unknown/wrongpage/analyzer/metadata/
legacyparser/classId, adapterS2a-vsS2b namespace mismatch; malformedanalyzerABI/
reservedheader/counts; retryidempotence/failureatomicity (no code/registry/event),
true OOG and8Mboundary; standardEIP170/3860/7825 layers. Use ordinarydeployed inputs,
nevermutate code/state to set up a passing path. No new host infiniteJava/SOE/OOM.

Both signed in-process geth receipts (all listenersoff) and direct signed
TransactionToMessage/ApplyMessage with sender/nonce/transactionchecks. Replays
under identical explicit contexts compare roots/gas/addresses/hashes/records/events;
record walltime signedheaders honestly. Verify actual deployed analyzer/linker
code vs pinnedartifact/immutableRefs and getterconfiguration, not selfdeclaredhash.
Report eachCREATE/register/adapter/negative gas andtotalsetup; finite14class suite,
no single-block-total claim. Parent adds separate java-stock-s2bl-* targets, reviews
and integrates runtime->harness->verifier, independentprobes and ALL oldS0/S1/S2a/
2231gates beforeacceptance. Then freeze a measured frame/execution stage separately.
