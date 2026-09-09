# MC-LC0: LOCAL single-stack start/resume and durable checkpoint kernel

FROZEN next slice after MC-LB0 acceptance0f6f008. Authority JAVA_EVM_PROGRAM.md:
artistic LOCAL EVM->JVM->unchanged MC1.12.2/Java8, finite highgas allowed, no full
JavaSE/standarddeployment prerequisite. This slice is genuine VM continuation for
small trusted workloads, NOT MC/main/VFS/thread/scheduler/JAR/output implementation.

## Basis and parent choices
Accepted base Solidity SHA256 c2fab72e468a951e29fd069d3bf3dfa98ab1513138ed7ae33f219a2588fcea9d;
runtime166385B SHA256 ea94075540b8b66aa8e85823ee66e9dba4a2be65f29942855a8f59478bca0cbf.
Use this descriptor-fixed base, not olderf50fe14. Old monolith andstock remain
byte-for-byte unchanged in LC0; their tests are reference/regression gates.

Parent reproduced preflighta54abad's nine real-engine extraction rows with identical
measurementSHA25609c80552137a8b7e884bdf0639f4b6ea92fee733eecb5fd6741b76050c22f38f.
Max596480B/12883262gas, plus q10 pendingArithmetic fault evidence. These q profiles
start afresh; NOT resumes. Runtime.Execute resets storage even with reusedStateDB;
runtime.Call preserves state/OOGrollback in independently replayed mechanism probe.

Implement one versioned generic interpreter kernel derived from the acceptedbase,
with initialization separated from dispatch/internal units and all mutable state
in one carrier. No fixture-specific executables, name/hash whitelist, host PC/heap/
method metadata, trace recovery, AOT or fallback. Newversion may copy/refactor the
base in newpaths, but has ONE opcode dispatcher for all its start/resume paths.
No second substitute evaluator hidden behind checkpoint operations.

Use a compact, flat, checked binary machine stream rather than preflight's whole
nested ABI arena dump. Only allocated handles and activeframes are serialized.
Parser/selectedCode/hierarchy/field/handler/default/literal caches are rederived
insideEVM from the exactrawbundle; serialize no host-supplied cache. No speculative
fiber/VFS/output sections, fork/import/upgrade protocol, or general helper phases.

## Ownership / bounded tools
Runtime ONLY jvmevm/runtime/local/lc0/**: LC0Interpreter.sol, optionalTypes/Codec/
Engine/helper.sol, pinned build/package/lock/artifacts/README. OneSoliditywriter.
Harness ONLY jvmevm/localcontinuation/lc0/{lc0.go,session.go,session_test.go,README.md}
and jvmevm/testdata/local/lc0/**. Go package lc0; helpers lc0Harness*.
Verifier ONLY jvmevm/localcontinuation/lc0/validation_test.go; helpers lc0Verify*.
Parent owns Make/guide/plan/review/parenttests/integration. Ignored
build/java-diff-mc-lc0-ROLE/ allowed. No peer writes/spawn/push/globalsettings/Fast,
no oldruntime/oldfixture/oldGoCLI/core/state/opcode/precompile/consensus/gascharging
edits. New workers Sol/high NOFast. No MC execution/EULA/listeners/downloadedJava.
Trusted smallJava oracles only; no platform bootstrap replacement on hostJVM.

## Generic profile / limits
Input is1..4 unchangedrawclasses, aggregate<=65536bytes; otherwise samebaseJava
classfile/introot/member/type/heap/exception/String profile. Entryclass andmethod
ASCIIbytes length1..256 each, rootargs0..8ints and exact(I...)I. Reservedbootstrap
rules and27rawimages remain base-exact. No capability changes to String/Throwable.
Classpath/rawparse/link/heap/initialization/instructions run entirely in EVM.
Existing128frames,1024arrays/objects,65536arraylength,262144elements,65536ordinary
fields,1024fields/ordinaryobject,256+emergencyexceptions/262144exceptionfields and
1024intern entries remain. Additional LC0 checkpoint bound<=1MiB may stop a run
before these guestquotas; that is a hardcheckpoint resource failure, not JavaOOM.
No claim everybaseprofile workload or maximalheap fits LC0.

Ordinary LOCAL call100Mgas/30s; dedicatedboundary/malformedcall<=1B/120s.
Commit-reserve guard25Mgas. Measure decode/validation/encoding/commit costs on actual
stagegates, not preflightencode alone. Check beforeunits and aftereachunit: if no
progress and insufficientreserve, hardControl7; after progress stop/yield only with
adequatereserve. If an indivisiblehelper or finalcommit still exhaustsgas, rollback
is required; this is not a guarantee of progress for arbitrary lowgas/largeinputs.
Do not silently raise frozenbudgets; optimize/report. This profile is LOCAL only:
no signedtx intrinsic/EIP7825/block/CREATE compatibility claim. Runtime<=256KiB
localbuild ceiling; pinnedsolc0.8.30 optimizer200/viaIR/Cancun/metadataoff.

maxJvmSteps1..4096, maxInternalSteps1..4096 PER CALL. Parent chooses4096 rather than
proposal64 so the samegenericruntime can execute allthree fixtures in onecall as
control. Counters/epochsuint64 checkednooverflow. Hostgates bound<=256slices and
<=4096dispatchunits/case,20minwholegate/4GiBRSS. No production256epoch termination
or artificialsuccessfulcompletion; further valid calls may continue counters.

## Units and execution state
A JVM unit is ONE existing interpreter opcode-dispatch attempt, counted once at
fetch, including a faulting instruction. Be explicit: active-use initialization
may schedule completeinitcontinuations and rewindcallerPC, then redispatch after
initialization; these are distinct DISPATCH attempts, not a claim of a JVM-language
instruction counter. Never repeat completed allocation/write/call/constructor or
fault because of resume. Metadata parse/cache rebuild is NOT an execution unit.

One internalunit is either initialroot initialization scheduling, one complete
existing init-continuation advancement (possibly pushing an initializer frame),
or one complete existing pending-exception handler-search/unwind operation. Keep
whole existingunwind here, not a new per-handler/per-frame cursor. Constructor
completion remains inside its returnopcode unit. Preserve everybasesemantic flag.

At a unit boundary, terminal status wins if already determined. Otherwise stop if
EITHER per-call unit budget exhausted; then select pendingexception first, followed
by init/dormantroot continuation, then the next opcode. Thus a last-budget idiv may
yield RUNNABLE with pendingexception and alreadyadvancedPC. Next resume must handle
that pending state before newopcode, not yieldunchanged or repeatidiv. Internal-only
progress is legal. Start prepares the rawprogram/root and runs the sameunit driver;
there is no separatefake evaluator. At leastone unit executes for success unless
an already-normalized terminal transition determines the outcome. No successzero-
progress loop. No Java code/data recovered from EVM OOG/revert traces.

LC0 lifecycle0=absent(Head only),1=RUNNABLE,2=RETURNED,3=UNCAUGHT_JAVA. No WAITING/
UNSUPPORTED success states. Hardvalidation/profile/OOG errors revert, not Java
outcomes. Terminal RETURNED/UNCAUGHT has zeroactiveframes. RETURNED has int32result,
javaKind/ref0 andinactivezero pending. UNCAUGHT has result0, knownkind1..12 and
exactexceptionref, matching retainedactivepending (faultPC is the existing propagated
handler-searchPC, not a new original-stacktrace claim). RUNNABLE result/javaKind/
javaRef0; pending may be active. Inactivepending fields canonicalzero. Allclasses/
statics/allocatedheap/counters remain inspectable afterterminal, no garbagecollector.

## Frozen public Solidity ABI
Contract LC0Interpreter, no constructor arguments, no public legacyinterpret or
checkpointimport/fork/sethead/upgrade API. Oldpureinterpreter stays separate.

struct SliceResult {
 uint32 schema; uint8 lifecycle; uint64 epoch;
 bytes32 checkpointRoot; bytes32 machineStateRoot;
 uint64 totalJvmSteps; uint64 totalInternalSteps;
 uint64 executedJvmSteps; uint32 executedInternalSteps;
 int32 result; uint8 javaKind; uint32 javaRef;
}
start(bytes32 instanceId,bytes[] rawClasses,string entryClass,string entry,
 int32[] args,uint64 maxJvmSteps,uint32 maxInternalSteps)
 external returns(SliceResult result,bytes checkpoint);
resume(bytes32 instanceId,uint64 expectedEpoch,bytes32 expectedCheckpointRoot,
 bytes[] rawClasses,bytes checkpoint,uint64 maxJvmSteps,uint32 maxInternalSteps)
 external returns(SliceResult result,bytes childCheckpoint);
head(bytes32 instanceId) external view returns(address owner,uint64 epoch,
 bytes32 checkpointRoot,bytes32 machineStateRoot,bytes32 artifactRoot,
 bytes32 configRoot,bytes32 runtimeCodeHash,uint8 lifecycle);
validateCheckpoint(bytes[] rawClasses,bytes checkpoint) external view
 returns(bytes32 machineStateRoot);

validateCheckpoint performs bounded canonical decoding and semantic/sourcechecks,
NO execution/anchorwrite. It is NOT proof of EVM-issued provenance or authorization.
It permits TEST-created selfconsistent envelopes to reach decodernegative guards;
a changed but well-formed state cannot resume unless its exactblob matches head.
No semanticvalidator return value can update/register a livehead.

Event CheckpointCommitted(bytes32 indexed instanceId,uint64 indexed epoch,
 bytes32 checkpointRoot,bytes32 machineStateRoot,uint8 lifecycle,
 uint64 totalJvmSteps,uint64 totalInternalSteps), exactlyone on eachsuccessfulslice.
Store only per-instance owner/epoch/head/machine/artifact/config/runtime/lifecycle
anchor and a reentrancyguard, not host-generated Java storage. instanceIdnonzero,
startrequiresunused id/nonzero msg.sender; epoch1,parentroot0. Resume requires
existingRUNNABLE head, sameowner, expectedEpoch AND root, actualruntimecodehash,
exactrawbundle commitment andcanonicalparentblob. Child epoch=old+1,parentroot=old.
Commithead+event after childvalidation/encoding/hashing, only onsuccess. No setters.
Unknownhead allzero. Authorization is relative to local EVM msg.sender, not a claim
of signedtransaction/consensus verification. Tests set explicitnonzero origin.

## Exact commitments / checkpoint envelope
H=keccak256; abi.encode below is canonical Solidity ABI generated IN EVM.
DART=H("JVMEVM:MC:LC0:ARTIFACT:1"), DBOOT=H("JVMEVM:MC:LC0:BOOTSTRAP:1"),
DCFG=H("JVMEVM:MC:LC0:CONFIG:1"), DMACH=H("JVMEVM:MC:LC0:MACHINE:1").
artifactRoot=H(abi.encode(DART,rawClasses)) (ordered, exactbytes).
bootstrapRoot=H(abi.encode(DBOOT,bytes32[27] orderedRawImageKeccaks)); exactbase27,
Object/Cloneable/Serializable/Float/Double,19Throwable,Comparable/CharSequence/String.
User legacybootstrap replacement still binds its rawbytes in artifactRoot.
configRoot=H(abi.encode(DCFG,uint32(1),runtimeCodeHash,bootstrapRoot,artifactRoot,
 entryClass,entry,int32[] args)). No limit/history/owner/instance in configRoot.
machineStateRoot=H(abi.encode(DMACH,uint32(1),artifactRoot,configRoot,H(machineBytes))).
checkpointRoot=H(exactcheckpointBytes).

Checkpoint is custombinary, allfixedintegers BIG-ENDIAN, no alignmentpadding:
 magic8bytes ASCII JVMELC01; schema:u32=1; instanceId:bytes32; epoch:u64;
 parentCheckpointRoot:bytes32; runtimeCodeHash:bytes32; artifactRoot:bytes32;
 configRoot:bytes32; machineStateRoot:bytes32; machineByteLength:u32; machineBytes.
Header216bytes, exacttotallength216+machineByteLength<=1048576. No trailingbytes.
Currentruntime EXTCODEHASH bindscode; externalheaderhash is not an attestation by
itself. Resume checks hash against storedEVM-produced head BEFORE execution.

## Exact machine stream v1 (no caches / no duplicateheap)
Concatenate in this order, no implicitABIwords/padding:
1. magic4 ASCII LCS1, lifecycle:u8, result:i32, javaKind:u8,javaRef:u32,
 totalJvmSteps:u64,totalInternalSteps:u64.
2. entryClass:u16 byteLength+rawASCIIbytes, entry:u16 length+bytes,
 argc:u8 + argc i32initialargs. EVM reselectsroot and recomputesconfig fromthese;
 initializedframe locals may ofcourse differ from initialargs after execution.
3. classCount:u16 exactmaterializedclasscount. For EACH class in runtimeindexorder:
 initState:u8(0..3),initializerStarted:u8(0/1),staticCount:u16,
 staticrecords {declaredFieldIndex:u16, taggedValue:u256} in strictlyascendingfield
 order; everyandonly STATICdeclaredfield represented. Instancefieldscratch defaults
 are rederived, not persisted. Preserve partialpreparations/erroneousclasses.
4. activeFrameCount:u16 <=128; root->top Frame records:
 classIndex:u16,methodIndex:u16,nextPC:u32,callPC:u256,flags:u8,thisHandle:u32,
 sp:u16,sp taggedstack:u256 cells,localsCount:u16,
 initializedbitmap:ceil(localsCount/8)bytes (lowbit0=local0, unusedhighbitszero),
 localsCount taggedlocal:u256 cells (uninitialized exactly0).
 flags bits0initializer,1initContinuation,2constructor,3constructorLinked,4entered;
 higherbitszero. Onlyactiveframes; reconstruct max128capacity in memory onresume.
 Syntheticinitcontinuation has methodIndex/nextPC/thisHandle/sp/localsCount0 and
 onlyflagbit1, classowner andcallPCretained. RootcallPC/initialfaultsentinel isfull
 u256MAX, not truncatedu32. Pendingthrow may leave nextPC==CodeLength; handlerPC is
 pending.faultPC. Validate this against actualpendingoperation, not onlystartmap.
5. heapheader: nextHandle:u32,ordinaryObjectCount:u16,ordinaryArrayCount:u16,
 ordinaryArrayElements:u32,ordinaryFieldSlots:u32,emergencyRef:u32,
 exceptionObjectCount:u16,exceptionFieldSlots:u32.
 Then EXACT nextHandle records in order1..nextHandle:
 handle:u32(mustequalordinal),metadata:u256,classIndex:u16,rank:u8,count:u32,
 cells: count*u64 forarrays, count*u256 forobjects.
 Raw metadata/class/rank encodings are EXACT acceptedbase HeapRegistry encodings,
 including HEAP_OBJECT_MARKER andcanonical arena-kind lowbits. No missing/duplicate/
 reorderedallocatedhandles, no inactivecapacityrecords. Emptyallocatedarrays valid.
6. Pending: active:u8,kind:u8,ref:u32,faultPC:u256; inactive allzero.
7. internCount:u16; {handle:u32,javaHash:u32} ascending Stringallocationhandleorder,
 exactoneentry for everyrepresentablecanonicalString, no duplicates/fullcontent
 duplicates. Validate actualUTF16/backing/hash and fieldcache0-or-correcthash.

Primitive/reference/tag/category2/TOP/constructor semantics are base-exact. Full
u256tags carry KIND_INT1,REF2,UNINIT3,LONG4,LONG_TAIL5,FLOAT6,DOUBLE7,DOUBLE_TAIL8
abovebit63. INT/FLOAT/ref/uninit payload<=u32; long/double<=u64; tails payload0.
No tails onoperandstack, no activezero stackcells; locals have exactinitialized/
category2 companion shape. Heapcycles/sharedrefs retainedbyhandle, not expanded.
Countertotals/layouts/refcompatibility/exceptionkind/classes/emergency/internrecords
must agree; exceptions countseparate fromordinaryobjects/fields, emergencyref1 when
registryexists. CanonicalString literals may exist while StringinitState0; objects
may escape reentrantinitialization and remain when classlatererroneous. Do NOT
requireeveryobjectclass state2. Allnull/defaultreference checks retain baselaziness.

## EVM reconstruction / canonical validation
Bound checkpoint length/counts/remainingbytes BEFORE allocations; no nested ABI
length-driven allocation. Checksummed envelope, strictoneparse/exactend and byte-
identical re-encode required. Derive classes/fields/methodCode/descriptors/catches/
hierarchy/defaultlayouts from boundrawbytes insideEVM. Load onlyneededmethod Code;
do not eagerlyreject dormantunsupportedmethods/handlers/unresolvednull fieldtypes.
No serialized CP offsets, Selected tables or derivedcache claims are accepted.

Rebuild activeframeselections according to actualstatic/virtual/private-special/
constructor/initializer flags; invoking-type metadata must not reject a legitimate
private invokespecial frame on restore. Check livePCs, stackwordcapacity, local
bounds, tags/references, class-init continuations, states andfaults. Wholeunwindunit
avoids serializing mid-poison callerstack tombstones. Preserveordinary pendingfault
and nextPC without redispatching that fault. Terminalframes empty.

Decode HeapRegistry ONCE and make everydispatcher alias and ExceptionArena.heap
point to it. Rebuild counterfields and exceptionclass mapping, but do NOT allocate
an emergencyOOM merely to validate/reload a no-heap checkpoint. Rebuild lazy immutable
default/layout caches, not Javaobjects. Intern lookup caches may startempty and be
populated lazily from alreadyinterned heap objects on actualldc; never resolve every
unused/malformedString constant duringrestore. Validation must not populateguest
String.hash or mutate anyJava state. Omittedpurecaches are outside machineStateRoot,
so q1/q7/onecall terminal machine roots match; historycheckpointroots neednotmatch.

## Exact errors and failure boundary
LC0ControlError(uint256 code):1zero/duplicate/unknowninstance or terminalresume;
2owner/zeroorigin;3epoch;4expectedhead/checkpointbytehash;5runtime/artifact/config/
instance-envelope commitment;6budgets/counteroverflow;7reserve/no-progress;8reentrancy.
Check existingRUNNABLE beforeowner on resume; thenowner,epoch,expectedroot,budgets,
code/source/blob integrity,decode/execute. Tests isolateonefault.
LC0StateError(uint256 code,uint256 byteOffset):1checkpointsize;2truncation/trailing;
3header/magic/schema/hash/config;4counts/order/enum/reservedbits;
5frame/PC/value/category2;6heap/layout/ref/counters;7init/static/pending/intern.
Offsets absolute in checkpoint, or0 foraggregate/globalinvariants. Standalone
validate uses State errors. Rawclass parsing and guest unsupportedoperations retain
baseerrors, not Javaresults. A parsed changedbutvalidblob may validate yet fail
resumeControl4. No canonicality result grants provenance. All EVM failures leave
head/event unchanged; lowgas/OOG may have empty returndata, never misdecodedJava.

## LOCAL Go transport / durable state
Package jvmevm/localcontinuation/lc0. Runtime()([]byte,error), RuntimeHash()(string,error),
ABI()(abi.ABI,error) loaders consume only pinnedLC0artifact; no Java parser/codec
evaluation in productionGo. Go SliceResult/Head use exported PascalCase names of
all exactSolidity fields below; hash fields common.Hash, owner common.Address,
integers corresponding fixed-width Go types. Public:
 NewMemory(owner common.Address)(*Session,error)
 Open(directory string,owner common.Address)(*Session,error)
 (*Session).Start(instance common.Hash,rawClasses [][]byte,entryClass,entry string,
 args []int32,maxJvmSteps uint64,maxInternalSteps uint32,gas uint64)(Result,error)
 (*Session).Resume(instance common.Hash,expectedEpoch uint64,expectedRoot common.Hash,
 rawClasses [][]byte,checkpoint []byte,maxJvmSteps uint64,maxInternalSteps uint32,
 gas uint64)(Result,error)
 (*Session).Head(instance common.Hash)(Head,error)
 (*Session).ReadCheckpoint(root common.Hash)([]byte,error)
 (*Session).Close() error
Result has Slice SliceResult,Checkpoint []byte,GasUsed uint64,RevertData []byte,
Logs []*types.Log. SliceResult/Head have exactABI fields (Hash fields common.Hash).
Return hardEVMerrors aserrors, with rawrevertbytes; known Java faults are successful
Slice.lifecycle3, not Goerror. ProductionGo ABI-packs rawinputs, decodesouterresult/
head only, hashes/carries opaquecheckpoints; no machine parser or metadata builder.

Install newoversizedLC0 code into a LOCAL StateDB account ONCE (explicitly labeled
harness codeinstallation, neverCREATEproof); subsequent start/resume/head use
runtime.Call with fixedexplicitnonzeroorigin/zeroValue/reproducibleEVMcontext.
No hostSetState/head/Java storage injection. Reopen mustload committedStateDB/code,
NOT call CreateAccount/SetCode/runtime.Execute again. Missing/wrongcode/diskstate is
harderror, not silentfreshsession. Refuse an unrelated nonemptydirectory on Open;
preserve userfiles, no destructive cleanup beyondownedtesttempdirs. No RPC/P2P.

DiskStore uses actual persistedgeth StateDB/trie root plus exactopaque blobs; blob
files are NOT a guestVFS. Startnew session once, then filesystem records root/format/
owner/contract/codehash/context. After eachsuccess: write/fsync blob byhash, commit
StateDB+triedb, atomicallywrite/fsync durableheadmanifest last. Retain oldroot/parent
until newhead durable. Beforepublication failure restores/reloads OLDdurableStateDB;
if StateDB.Commit alreadyconsumedjournal, reloadoldroot rather than invalidsnapshot.
An after-publication fsync ambiguity must report unknowncommit and require reopen,
not pretendrollback. Extraunreferenced blobs/roots harmless; no fakecatchup.
Testfaultinjection seams for filewrite/triecommit/manifest publication are allowed,
never VMlogic hooks. Tests trace exactlyonecodeinstall; processrestart loadsDB+blob,
not a portable forgedstateimport. In-memory sessions retain sameStateDB similarly.

## Acceptance corpus / gates
Keep exactpreflighttrusted sources/classes as NEW lc0fixtures, not oldfileedits:
 LC0CallLoop.class SHA4970ae2e395e96b91231b5d19439ba4fdfd6b91ef61429904c9fa758058c8302;
 LC0AliasBox.class SHA43cb95765ad4f1568a12cc04ce2493aea08ad29916b60b7827231e40bae863c6;
 LC0AliasString.class SHAe7ec98bfb70650c23dfe2d1d63b86964d0aa35969b84c85db66945def6c0ec2f;
 LC0InitDep.class SHAac7aaf7e9d7d6ae457d55d52f1300060718e177fb8cc294f1fa80261b89e52c0;
 LC0InitException.class SHA0c8005f33deac53eba1afda833ee71df28de99e1451c8f074c6e720e75b5fa9d.
Paths/source/bundleorder in preflight. Results15(run5),36,10. No fixtureidentities or
results inruntime. CompareJava8/21, acceptedmonolith, LC0onecall4096 and actualq1/q7
resumechains (alsointernalbudget1). SamefinalmachineRoot/counters/sideeffects,
differentcheckpoint histories; negativeint andknownuncaughtfault supplementarytests.

Prove livecallprefix/locals/callPC/depth, uninitializedconstructoraliases, mutation
through static/object/refarray andinternString samehandles, exactlyoneclinit and
exceptionref acrosspendingfault thenhandler. Coverq10-equivalent pendingref2/PC15
viaactualexecution, not hostcheckpoint synthesis. Boundary snapshots include initial
initcontinuation, postconstructorreturn, classstate2 withpendingcontinuation, and
terminal. No repeatedopcode sideeffects when restore/retry or OOG happens.

Validate malformed streams/counts/header/frame/heap/static/pending/intern/category2
andforward/cyclicrefs; use validateCheckpoint for deepmutations with recomputedTEST
hashes, but prove allhostchangedstates fail livehead binding. Staleepoch/root, wrong
owner/instance/raworder/rawbytes/code/config, duplicate start, terminalresume,
checkpointlimit, lowgas/reserve and genuineOOG all preserveoldhead/nochildlog. Retry
fromoldsnapshot produces samechild ascontrol. No hosttrace-state reconstruction.

Persist/reopen in a NEW PROCESS at alias checkpoint and pendingfault checkpoint,
finishidentically; also failureafterblobwrite and aftertriecommit/beforemanifest.
Verify blobhash, database/trie/code/head, Codeinstallation count, no resetonresume.
Log everyepoch/root/units/selectedstate/gas/bytecount, exactartifacts and rawhashes.
Host TEST decoding for assertions is allowed, neverfeeds an executionpath.

Build/check/newtest/demo and focusedvet; preserve allacceptedLB0/2231/stock/Python/
bootstrap/artifact/AOT/demos withoutbudgetchanges. Oldpuremonolith notmodified;
LC0does notclaim migrating every2231row or allheapboundaries. Parent independently
probes/integrates/accepts lastgreen before next VFS/thread/main dependency slice.
