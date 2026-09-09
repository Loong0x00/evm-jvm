# MC-LB0: LOCAL String literal and identity core

ACCEPTED; parent/independent review and final gates in JAVA_EVM_MC_LB0_REVIEW.md.
Frozen implementation contract retained below. Authority JAVA_EVM_PROGRAM.md: artistic
EVM->JVM->unchanged vanilla MC1.12.2/Java8, local finite high gas permitted. NO
complete JavaSE/standard deployment prerequisite. S2b-L accepted bbaa023 separately.
Proposals fec1faf/4dba0a2 reviewed; recommendations refined below. No server run,
EULA acceptance, listener, MC startup, VFS, scheduler or continuation in this slice.

## Parent decision / evidence boundary
String constants occur immediately in real startup; literal identity and UTF16
are a bounded prerequisite. Implement this first, not all platform services.
Keep the richer monolith and existing int-root ABI; Class/main/Throwable APIs,
String construction/composition/formatting and continuation are later slices.
Parent independently reran the finite lifecycle probe: repeated runtime.Execute
with reused StateDB reset teststorage1->1, runtime.Call preserved2->3 and OOG
rolled back. This is storage-mechanism evidence, NOT JVM resumability. Actual MC
main starts a server thread; Done on that thread precedes the tick loop. No main
return/temporary OOG log may be called readiness.

## Scope / ownership
ONE production Solidity writer. Runtime worker ONLY jvmevm/runtime/
JVMSubsetInterpreter.sol,.runtime.hex,build.js,README.md and NEW bootstrap/
{Comparable,CharSequence,String}.{java,class.hex}. Existing24bootstrap sources,
bytes/order/hashes MUST remain unchanged; compiler dependencies/settings unchanged.
Harness worker ONLY new jvmevm/mc_lb0_test.go and jvmevm/testdata/local/lb0/**:
64exacttrusted cases and JVM8/21/EVM harness. Unique mcLB0Harness* helpers.
Verifier ONLY new jvmevm/mc_lb0_validation_test.go; helpers mcLB0Verify*.
Parent owns Make/guide/plans/review/independentprobes/any reviewedobsoleteguard edits.
No oldtest/manifest/CLI/tool/stock/core/state/opcode/precompile/consensus/gas-accounting
changes by workers, no peer writes/spawn/push/globalsettings/MC execution. Sol/high
NOFast. Ignored build/java-diff-mc-lb0-ROLE/ diagnostics allowed, clearly labeled.
Host only builds trusted fixtures/runtime and transports rawclassbytes/entry/intargs.
No production host decoding/transcoding, Java execution, metadata injection or
String/native fallback. Every operation below executes in EVM bytecode.

## Bootstrap and representation
Append THREE parsed raw bootstrap images AFTER the existing contiguous19Throwable
images in BOTH entry APIs. Preserve userclassindices and throwableBootstrapAt.
Unlike proposal's tag8-only trigger, append them for EVERY invocation: null String
calls, casts and interface references can need them without any tag8. Do not scan
host reachability or invent speculative ClassKey/checkpoint ABI in this slice.
The default builtin set is now27 images (supplied legacyreplacements retain their
old rules); inputrawclasslimit64 stays. Measure overhead against ALL oldbudgets.

Reserve java/lang/String,java/lang/Comparable,java/lang/CharSequence in both APIs;
user replacement => BootstrapProfileError(1,inputIndex), index0 for single input,
after class parsing at existing reserved-bootstrap boundary, before root selection.
Keep old reservedThrowable errors unchanged. Appended String is public/final,
extends Object and directly implements Serializable,Comparable<String>,CharSequence.
Comparable<T> declares compareTo(T):I; CharSequence declares length(),charAt(I),
subSequence(II),toString(), with exactJava8descriptors and abstractflags. No defaults.
String owns privatefinal char[] value and privateint hash (Java8zero-cache sentinel).
It declares the8 supported native instance methods below, a publicnative deferred
subSequence(II):CharSequence, and a privateconstructor initializing value=null.
Compiler-generated compareTo(Object):I bridge is ordinary bytecode (checkcast then
compareTo(String)), not native. Runtime rejects new String before initialization/
allocation, so privateconstructor is never an exposed allocation path.
Trusted source may use ordinary modifiers/generics, not host classfile rewriting.
Build pins exactnew sources/hex/embeddedhex/hashes as for all previousbootstraps.
Parent compiled the exact3new source candidates alongside the24old sources with
javac --release8 -g:none: all24old images remained BYTE-IDENTICAL. New pins:
Comparable196B SHA2569d291a315ca765cdcb404feb72aa3d6f1216e542476ec071238fe105f2b85775;
CharSequence216B SHA256c996ea063c00b6a8e320c73d81660bf2a733e492c312a032205c8d4f1e051576;
String787B SHA2565582fd23db2e4bfeb3e6cc3b82de587c74cadb4773883e9bd71e08aafd95f4fe.
Use exact sources from canonical ignored build/java-diff-mc-lb0-parent/bootstrap-src/
{Comparable,CharSequence,String}.java and pin their bytes above in production build.
Do NOT run these minimal bootstrap replacements on a host JVM; hostoracles use its
normal Java library. This proves source/profile reproducibility, not String EVMgas.

A literal is an initialized ordinary HEAP_OBJECT of canonical String class backed
by an ordinary char[] heap handle. Use existing EVM-derived inherited fieldlayout;
do NOT assume supplied Object haszero fields. backingarray is inaccessible through
supported public API; normal private/final field guards remain enforced. No String
subclass/unsafe/reflection mutation. hash field starts taggedint0; backing value is
taggedref. All field/array/ref/tag and ordinary allocator invariants remain real.
Use ONE authoritative shared heap/handle stream and synchronized counters: String,
ordinary new/newarray/multianewarray and ExceptionArena must not retain divergent
lazy-registry aliases. Refactor a small allocation/context struct if needed, not a
second hidden heap or special reference type. Snapshot serialization is NOT added.
String identities/pool last one invocation, reset on the next Run as before.

## Literal decoding and intern pool
Support CONSTANT_String (tag8) through ldc and ldc_w; Class tag7 remains old
BytecodeError13. Oldbadldc operand/tag errors stay as before; a validtag8 whose
string_index is not an in-range tag1 is StringConstantError1 described below.
ForwardCP references must work. Decode ONLY insideEVM from originaltag1 rawbytes:
- ASCII1..7f as one UTF16unit, raw00 invalid;
- c080 is NUL, shortest2-byte forms for80..7ff;
- shortest3-byte forms for800..ffff, including paired OR unpaired surrogates;
- invalidlead/continuation/truncation/otheroverlong/four-byteUTF8 rejected;
- no normalization, scalar conversion, replacementcharacter or locale transformation.
Bound checks are against declaredUtf8payload, not followingCPbytes. Empty valid.

Every selected-method String load is structurally/MUTF8-validated at predecode,
even if unreachable, but allocates NO guest String merely by predecoding. Other
unselected methods are deferred as before. StaticString ConstantValue MUTF8 is
validated when actually prepared (see nextsection). No global eager validation of
all unrelated Utf8/names or unused strings. Caches are EVM-derived; repeated CPload
must not repeatedly allocate. Keep originalrawbytes immutable.

Resolve/intern globally across ALL classes/CPentries. Use a hash lookup with full
UTF16content/length collision comparison; hash alone never establishes equality.
Canonical strictMUTF8 equality may be used as an optimization only after validation,
with a documented equivalence argument. No host-interned strings. A hit returns
the same initializedref with NO object/array/element/field/handle allocation, even
at exhausted quotas. A miss preflights all quotas and stackcapacity, then atomically
allocates oneString+onechararray, installs fields/units, publishes ONE poolentry and
pushes the ref. Singlemiss failure leaves no half-object/poolentry/counter advance
apart from the normal separate exception allocation. Avoid duplicate full-sized
UTF16arrays: decoder buffers may transfer ownership to backingarray or usecompact
scratch. Only original ordinary quotas apply: objects1024,arrays1024,eacharray65536,
totalarrayelements262144,ordinaryfields65536,fields/object1024,sharedhandlelimit;
internpool<=1024. Preserve exception256+emergency and262144exceptionfields arena.
Quotaexhaustion routes through existing catchable JavaOOM7/pending/unwind, not an
EVM profileerror or a fabricated zero. EVM OOG is NOT JavaOOM.

## ConstantValue and initialization
Extend FieldInfo with retained String CPindex (not a truncatedref in uint64).
ConstantValue descriptor must be EXACT Ljava/lang/String; and CPtarget tag8 with a
validtag1 chain. Wrongdescriptor/tag/chain/duplicateattribute => existing FieldError5
andfieldindex. Primitive handling unchanged. Match existingJVMS rules: static
ConstantValue fields prepare regardless of FINAL; structurallyvalid INSTANCE
attributes are ignored, with no intern allocation merely from the attribute.

StaticString values use SAME pool and become taggedrefs at existing constant-
preparation point, before thisclass clinit and before its superclass initialization
as in current primitive implementation. Preserve reentrant initialization semantics.
A new allocation fault here needs correct bookkeeping: current code writes state1
before preparing constants and has not yet pushed its continuation. On OOM, mark
the failing initialized class erroneous, unwind dependent continuations correctly,
preserve actualOOM identity as Error (no erroneous EIIE wrap), and lateractiveuse
must yieldNCDFE12. Dormant root cannot catch its own initialization failure. Earlier
successful constant preparations need not be rolled back, but a singlefailedmiss
must not publish. Do not leave state1 stuck, silently skip preparation, or reset
all class/heap state. Any new continuation-frame requirement/ordering affecting
existing semantics must be reported to parent rather than hidden.

## Exact String method domain and invocation
8 supported publicnative INSTANCE signatures (ordinary EVM platform intrinsics):
 length()I; isEmpty()Z; charAt(I)C; equals(Ljava/lang/Object;)Z; hashCode()I;
 toString()Ljava/lang/String;; compareTo(Ljava/lang/String;)I;
 intern()Ljava/lang/String;.
length countsUTF16units. charAt returns unsigned16-bitunit ONLY for0<=index<length.
Badindex => hard StringProfileError2(callPC), not zero or wrong AIOOBE; full String
bounds exceptions await a laterexceptionprofile. equals handlesnull/nonstrings as
false, comparesfullUTF16; hash uses31*h+unit withJava int32wrap/cache0sentinel.
compareTo uses unsignedUTF16 lexicographic difference or lengthdifference, notlocale;
null argument => actualNPE6. toString returnsreceiver. intern usesglobalpool/sameref
for all representable Strings. GenericComparable.compareTo(Object) bridge executes
normalcheckcast: nonString initializedObject => actualCCE8; null thennativeNPE6.

Support invokevirtual on canonicalString and invokeinterface through the declared
CharSequence/Comparable members, including bridge. Preserve expressionprefix,
receiver/argument order, typed returnwidth and nullreceiver NPE6, at actualinvokePC.
Native null/argument checks precede consumption; faults use existingpendingstate/
handlers/unwind. Wrongnonnull typed String arg/corruptheap/tag is hardBytecode14,
not a fabricatedCCE; Objectbridge is the genuinecast path. Native methods create
no fictional JavaCode/frame or trace. Only exact reservedclass/method/descriptor/
flags/noCode can bind. Ordinary Code bridge wins over native handling. Preserve
all4Float/Doublebindings flags/ABI/behavior exactly, and all unrelatednative guards.
Do not globally allow native virtual/interface methods merely for this profile.

new String, all constructors, substring/concat/format/valueOf/getBytes/builders/
otherundeclared String APIs and deferredsubSequence => StringProfileError1(pc).
For symbolic String/CharSequence/Comparable outside thisprofile, failhard rather
than returning AME/defaultvalues to simulate a missing library method. Validate
malformedCP/descriptors under existingrules first. Access to nativefields remains
ordinaryFieldError rules. Object-owned getClass/equals/hashCode/toString declarations
are NOT added to the unchanged95B Object image in LB0; calls requiring those
missing Object declarations remain unsupported by existinglinkage guards. Do not
claim full String/Object API compatibility. No userStringreplacement/lookalike
owner can select an intrinsic; user implementations of represented interfaces
retain ordinary dispatch, not String-native behavior.

## ABI and exact new errors
Existing interpret/interpretClasses selectors, pure mutability and int32return
unchanged; root remains exact(I...)I, argsint32 only. No text output/main/scheduler.
Go JavaException decoder remains exactly1..12/36canonicalbytes; do NOT relabel new
harderrors,unknownselectors,noncanonicalreplies orOOG. No host runner change needed.
 BootstrapProfileError(uint256 code,uint256 inputIndex): code1reservednewname.
 StringProfileError(uint256 code,uint256 pc):1deferredAPI/new;2charAtindex.
 StringConstantError(uint256 code,uint256 classIndex,uint256 cpIndex,uint256 byteOffset):
 1invalidtag8 string_index chain (byteOffset0);
 2invalidlead/rawNUL/straycontinuation/fourbytelead;
 3truncatedsequence atlead;
 4invalidcontinuation atoffendingbyte;
 5forbiddenoverlong atlead.
For2..5 byteOffset is ABSOLUTE originalclassfileoffset; cpIndex is tag8 entry, not
its tag1 target. Test completepayloadend before continuationreads; invalidlead takes
precedence over potentialtruncation. NonString ldc errors retain originalBytecode13.
MalformedString ConstantValue chain staysField5; decodedpayload errors use2..5 at
actualclass/index. Schema is hardvalidation/profile boundary, nevercatchableJava.

## Gates / budgets / explicit exclusions
New LOCAL MC-LB0 ordinarycases100Mgas/30s watchdog; dedicated maximumlength/quota/
collision probes<=1Bgas/120s perprobe, boundedcasecounts. These are NEW explicit
ceilings, NOT raises to any existing test or stock gaslimit. Parent chooses1B
rather than the proposal's unmeasured250M boundary suggestion because backing
262144 UTF16cells alone occupies8MiB EVMmemory (~135M expansiongas), before decoder,
fields/heap/CP/otherbuffers. Record actualgas; reduce duplicatework without deleting
coverage. No infinitegas or startup feasibility claim. Local runtimeExecute remains
oversized direct-code execution, NOT standardCREATE/transactiongas evidence.

64 new exacttrusted catalogue rows in jvmevm/testdata/local/lb0/, preserved and
compared on Java8 and21 against EVM (intreturns/checksums/caughtfaultpredicates).
Include length/charAt/empty/NUL/2-3byteboundaries/paired-unpairedsurrogates/hashwrap/
lexicographic/equality/nulls/nonstrings/interface/bridge/identity/CPhits/crossclass/
clinit/statics. Avoid javacconstantfolding replacing tested methodcalls/fieldreads;
inspectbytecode and use boundedrawfixtures where needed. ResetbetweenRun verified.
Dedicated verifier matrices: allbadMUTF forms/forwardchains/ldc_w/sourceoffsets,
Class/tag/native/deferred/bounds guards, reservedinputnames, private/final backing
protection, wrongtypedargs, poolhashcollisions, longprefixes/maxCPUTF8length65535,
staticnonfinal/instanceConstantValue behavior, root/dependent preparationOOM and
laterNCDFE, mixed String/array/object/exception allocations and identity, exactone-
under/at/over isolatedobject/array/element/field/handle/pool resources where reachable.
No requirement to fabricate an impossible independentlyreachable counter boundary;
explain relationships and preserve all reachable limits. Internhit atfullheap must
work; failedmiss leaves pool/allocation consistent; no hugehostJava exhaustion.

Keep old2231manifest rows/sources/outcomes/per-casegas/timeouts unchanged. All24old
bootstrap hashes, GoCLI/36Python,1040smoke/1060fast, exception/init/fieldquota parent
probes, artifactreproducibility/demos/AOT/focusedvet and stockS0/S1/S2a/S2b-L gates
must pass. If new support obsoletes a prior NEGATIVE, report exactinput/oldexpectation/
newbehavior for parentreview; keep fixture and replace with a genuineguard, never
silently delete or rebaseline. No MCUstartup/libraryconformance claims from64rows.
Parent independently tests, accepts lastgreen, then freezes nextLOCAL dependency.
