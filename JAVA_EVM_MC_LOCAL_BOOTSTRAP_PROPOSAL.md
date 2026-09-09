# LOCAL Minecraft 1.12.2 Java bootstrap proposal

Status: **bounded documentation/oracle proposal only; not a frozen implementation
contract and not an acceptance claim**. The parent owns any later freeze and is
final-gating stock S2b-L separately. This proposal was prepared at `a6f9646` from
the accepted M5d-a monolith. It owns no production source, fixture, harness, EVM,
consensus, peer, or global-setting change.

No Minecraft code was executed. No EULA was accepted or written, no server was
started, no listener was opened, and no artifact was downloaded or redistributed.
The pinned JAR was only read with bounded ZIP/classfile/`javap` tooling. The only
executed Java was a small self-authored String/Class/Throwable oracle under finite
Java 8 and Java 21 processes.

## Recommendation: one slice, MC-LB0

Take **MC-LB0: literal String identity core** as the next LOCAL monolith bootstrap
implementation slice. Keep the existing integer-root ABI for this slice. Add:

1. EVM-side validation and decoding of `CONSTANT_String`'s classfile modified
   UTF-8 into exact UTF-16 code units;
2. ordinary guest `java/lang/String` objects backed by guest `char[]` data;
3. one per-VM intern pool shared by every class/constant-pool entry;
4. `ldc`/`ldc_w` String resolution and String `ConstantValue` preparation;
5. a very small exact method profile needed to inspect and compare representable
   literal Strings: `length`, `isEmpty`, valid-index `charAt`, `equals`,
   `hashCode`, `toString`, `compareTo`, and `intern`; and
6. explicit hard profile rejection for every deferred String constructor/method
   or out-of-profile `charAt`, rather than a guessed value or wrong Java exception.

Do **not** combine MC-LB0 with Class mirrors, a `main(String[])` launcher,
Throwable API expansion, formatting/builders, logging, VFS, JAR loading, threads,
continuation, or Minecraft execution. Those are separate dependency slices below.
MC-LB0 is useful because the selected server's real root reaches String constants
immediately, while Class mirrors are not used by the five statically inspected
entry/startup methods. It is still only a semantic nucleus, not a launch attempt.

This recommendation intentionally revises the older M5d-b preflight's general-JVM
ordering in light of the user's LOCAL artistic-workload priority. It does not
invalidate M5d-b0: fresh Throwable identity remains required before honest message,
cause, and stack-printing support, and only one worker may edit the monolith at a
time.

## Artifact and static startup evidence

`JAVA_EVM_PROGRAM.md` pins vanilla server 1.12.2 at 30,222,121 bytes, SHA-1
`886945bfb2b978778c3a0288fd7fab09d315b25f`, SHA-256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`.
Before relying on the existing read-only artifact I ran `sha256sum` and `stat`; both
size and SHA-256 matched. `sha1sum` also matched. The manifest still names
`net.minecraft.server.MinecraftServer`.

Static `javap` findings make the ordering concrete:

* `MinecraftServer.main:([Ljava/lang/String;)V` is 201 decoded instructions. At
  PC 0 it calls `ni.c:()V`; after that returns, PC 7 executes `ldc_w "."`.
  Its argument parser has ten further String loads and invokes
  `String.equals(Object)` at PCs 68, 79, 95, 129, 154, 179, 205, and 222.
* Java initializes `MinecraftServer` before entering `main`. Its `<clinit>` calls
  `LogManager.getLogger()` at PC 0, then loads `"usercache.json"` at PC 10 and
  constructs `File`. A launcher alone therefore does not bypass logging/String/VFS
  bootstrap.
* `ni.c:()V` is 47 instructions in that method alone and invokes a long registry
  initialization chain. Its own directly visible error paths load three Strings.
* `MinecraftServer.F:()V` is 11 instructions: it loads `"Server thread"`, creates
  `Thread(Runnable,String)`, stores it, and calls `Thread.start()` at PC 19.
  `main` calls `F()` at PC 403 and later returns at PC 440.
* The server thread executes `MinecraftServer.run()`. `run` calls virtual `j:()Z`
  at PC 1 and, if startup succeeds, enters the tick loop (back edge to PC 62 while
  its running flag remains true). The overridden `nz.j:()Z` is 526 instructions
  and has 64 String loads.
* In `nz.j`, level preparation is called at PC 950. Only after it returns does the
  guest call `System.nanoTime`, compute a duration, box a `double`, call
  `String.format("%.3fs", Object[])`, then pass
  `"Done ({})! For help, type \"help\" or \"?\""` and the formatted duration to
  `Logger.info(String,Object)` at PC 994.

Thus **root-main return cannot establish readiness**. The genuine `Done` event is
produced on the spawned server thread before the infinite tick loop. A later root
launcher must hand control to an explicit cooperative scheduler/continuation model;
it may not terminate the workload, skip `Thread.start`, or reinterpret main return
as `Done`.

A bounded whole-JAR structural scan (not reachability analysis) parsed all 19,007
classfiles and 64,620,541 uncompressed class bytes with no parse error. It counted:

| Whole-JAR static count | Count |
|---|---:|
| decoded Code instructions | 3,478,439 |
| `ldc`/`ldc_w` String uses | 35,572 |
| distinct String payloads used by `ldc` | 15,209 |
| payloads used in more than one declaring class | 3,343 |
| largest used MUTF-8 payload | 54,992 bytes |
| Class-literal `ldc` uses | 2,586 |
| distinct Class-literal targets | 1,315 |
| classes containing Class-literal loads | 1,185 |
| `Object.getClass()` calls | 512 |
| calls with symbolic owner `java/lang/Class` | 1,271 |
| calls with symbolic owner `java/lang/String` | 5,256 |
| `PrintStream.print*` calls | 61 |
| selected `Throwable` rendering/query calls | 92 |

These are conservative whole-distribution counts. Optional/client/error/library
paths are included, obfuscated calls were not semantically classified, and no
result is proof of startup reachability. The five specifically inspected methods
(`main`, `F`, `run`, `ni.c`, `nz.j`) had String loads but no Class-literal load;
that is why Class mirrors rank immediately after, rather than inside, MC-LB0.

## Exact current monolith blockers

The statements here describe `jvmevm/runtime/JVMSubsetInterpreter.sol` at
`a6f9646`, not an intended JVM architecture.

### Entry and class profile

* `interpret` and `interpretClasses` select a static method by name. `_loadRoot`
  and `_isExactIntRoot` require exact `(I...)I`; therefore the unchanged selected
  `main:([Ljava/lang/String;)V` first fails `MethodError(11)`.
* `_execute` accepts only `int32[] calldata args`, initializes root locals as ints,
  returns `int32`, and says explicitly that the external root can only return int.
  General descriptors and internal void returns already work, but there is no void
  external completion result or allocated `String[]` launcher local.
* `interpretClasses` accepts at most 64 supplied raw classfiles. The selected JAR
  contains 19,007 classfiles plus missing platform classes/resources. There is no
  JAR/manifest/resource parser, namespace loader, VFS, or scalable class paging.
* VM state is Solidity memory in one `pure` invocation and resets on return. There
  is no committed checkpoint, scheduler queue, persistent intern pool, or VFS.

### String constants and static fields

* `_readConstantPool` records tags 7 and 8, but a tag-8 word is only an unresolved
  `string_index`. `_validUtf8` validates only “nonzero CP slot with tag 1”; it does
  not validate or decode modified UTF-8.
* Both `_predecode` and the live `ldc`/`ldc_w` branch admit only tags 3 and 4.
  A String load is currently hard `BytecodeError(13, pc)`.
* `FieldInfo.constantValue` is only 64 bits. `_readFields` permits `ConstantValue`
  only for int/long/float/double, so a static final String constant is rejected by
  `FieldError(5, field)` instead of being interned during preparation.
* There is no `java/lang/String` bootstrap, backing representation, pool, or
  String method binding. `_nativeBinding` recognizes exactly four static raw-bit
  methods on Float/Double and no instance/platform method.

### Class and Throwable

* There is no `java/lang/Class` bootstrap or Class-object heap kind. Class metadata
  indices are internal array positions, not guest mirrors. `ldc` Class is rejected
  by the same tag check, and `Object.getClass` has no binding.
* `_resolveNewClass` explicitly rejects every class assignable to canonical
  Throwable with `ObjectError(2, pc)`. `athrow` accepts only an initialized object
  whose heap metadata low byte is a current arena kind.
* The 19 Throwable bootstrap images are zero-field identity stubs with only `()V`.
  Message/cause/stack APIs and String constructors are absent. The exact M5d-b0
  implications and the observable Java 8 `fillInStackTrace` callback are already
  documented in `JAVA_EVM_M5DB_BOOTSTRAP_PROPOSAL.md`; MC work must not paper over
  them.
* Synchronized methods, monitor bytecodes, general natives, `invokedynamic`, method
  handles, reflection, files, clocks, logging, networking, and real thread start
  remain unsupported. A no-op implementation of any required path would be false
  progress.

### Finite limits and deployment label

Current limits include CP 4,096, Code 65,535 bytes, 128 frames, 1,024 arrays,
65,536 elements per array, 262,144 total array elements, 1,024 ordinary objects,
65,536 ordinary field slots, and a separate 256-record exception arena. The actual
whole-JAR largest CP (2,805) and Code body (9,625) fit their individual current
caps, but the class count, heap, library, state lifetime, and platform do not.

The checked runtime is 154,839 decoded bytes, SHA-256
`dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
It is useful through local `runtime.Execute`, remains far above EIP-170, and is not
ordinary-deployment evidence. LOCAL MC work may use explicit large finite gas; it
must not alter opcode semantics, gas charging, consensus/core code, precompiles,
or historical stock budgets. The checked fork still has no diff against pinned
upstream in `core/vm`, `core/state`, `core/types`, `consensus`, or `params`, and
`core/vm/runtime/runtime.go` matches upstream SHA-256
`822478c26ca1eb4313ab83da97576cbc4d93397f8f1cfddebbffcb6afd7d9c26`.

## Proposed MC-LB0 semantic contract

### Bootstrap classes and stable identity

1. Preserve all current 24 raw bootstrap images byte-for-byte and preserve their
   order. Keep `throwableBootstrapAt` pointing to the same contiguous 19-image
   graph. Append new images only after that graph.
2. Add versioned raw profile images for `java/lang/Comparable`,
   `java/lang/CharSequence`, and `java/lang/String`. String is public/final,
   extends Object, and declares the Java 8 direct type relations Serializable,
   Comparable<String>, and CharSequence. Unsupported methods may remain declared
   profile natives, but invoking one must produce a specific hard
   `StringProfileError`, never a default value.
3. Reserve those three names. A supplied replacement is a hard
   `BootstrapProfileError(1,inputIndex)` in both entry APIs. Server/application
   bytes remain unchanged; the bootstrap library version is a separately pinned
   platform input.
4. Activate/append this profile when any supplied constant pool contains tag 8
   (including a String `ConstantValue` target); do not require host reachability
   analysis. Legacy inputs without tag 8 retain the exact 24-image class layout.
   Replace hard-coded class-count arithmetic with a checked bootstrap plan rather
   than relying on another magic total.
5. Define stable semantic keys independent of transient array indices:
   `ClassKey = keccak256(namespaceId || kind || validatedInternalNameOrDescriptor)`.
   MC-LB0 needs the String key; the same scheme must later cover mirrors and
   checkpoints. Internal numeric class indices and heap handles are not ABI and
   may not be serialized as identity without their key.
6. A String's identity is one ordinary `HEAP_OBJECT` of canonical String class with
   private guest `char[] value` and cached 32-bit hash fields. The backing array is
   immutable through the supported API. Reflection/unsafe access is unsupported,
   not a route to mutate it.
7. Identity is stable within one VM lifetime. The current invocation resets the
   pool. A later continuation implementation must serialize String objects,
   backing arrays, intern entries, ClassKeys, and next-handle state exactly; it may
   not recreate handles from host-decoded text.

### Modified UTF-8 and literal resolution

For tag-8 CP entry `S`, resolve `S.string_index` to exactly one tag-1 entry and
decode its raw classfile bytes **inside EVM** to UTF-16 code units:

* raw `00` is invalid; U+0000 is exactly `c0 80`;
* nonzero U+0001..U+007f use one byte;
* two-byte forms use valid continuation bytes and are shortest form, except the
  required NUL encoding;
* three-byte forms use valid continuations and are shortest form;
* UTF-16 surrogate code units are retained exactly, including an unpaired
  surrogate; a supplementary character is therefore the two decoded surrogate
  units present in classfile MUTF-8;
* four-byte standard UTF-8, truncation, stray continuation, forbidden overlong
  form, or any decoded sequence beyond the declared byte length is invalid; and
* there is no Unicode normalization or locale conversion.

Malformed metadata is a canonical hard
`StringConstantError(code,classIndex,cpIndex,byteOffset)`, following the current
malformed-class/profile boundary; it is not a catchable fabricated Java exception.
MC-LB0 needs to validate tag-1 payloads reached from tag 8, not silently redefine all
existing raw-name comparisons. A later classfile-validation stage may make global
MUTF-8 validation eager with separately reviewed negative-test error ordering.

`ldc` and `ldc_w` then perform an atomic resolve/intern operation:

1. decode or use a per-CP validated decode cache;
2. hash and compare the complete UTF-16 sequence against the VM-global pool;
3. on hit, push the existing initialized String reference without allocation;
4. on miss, preflight one ordinary object, one char array, all field/element/handle
   quotas, and `MAX_INTERNED_STRINGS = MAX_OBJECTS` (1,024 in MC-LB0); allocate
   both only after the full preflight;
5. copy every code unit, install the initialized String, publish one intern entry,
   and push the reference; and
6. on quota exhaustion, raise the existing catchable OOM7 without a partial pool
   entry or half-visible String.

Hash collisions require full length/code-unit comparison. Pool lookup is shared
across classes, so equal literals from different CP entries are `==`. Empty and
NUL-containing literals obey the same rule. Resolution does not initialize an
unrelated class represented by text and never asks the host to transcode.

A static final field whose descriptor is exactly `Ljava/lang/String;` and whose
single `ConstantValue` points to tag 8 stores the same interned reference at the
existing class constant-preparation step, before `<clinit>`. Extend field metadata
to retain the CP index, not a truncated handle. Every other reference
`ConstantValue`, duplicate attribute, wrong tag/descriptor, or malformed payload
fails explicitly.

The measured 54,992-byte whole-JAR maximum fits the current 65,536 element
per-array cap because MUTF-8 decoding cannot produce more UTF-16 units than input
bytes. That says nothing about the current 1,024-array/object and 262,144-total-
element limits being enough for reachable startup.

### Narrow String method domain

Implement these exact calls in EVM bytecode or tightly keyed Solidity platform
bindings against the reserved raw image; no host Java/native service is involved:

* `length:()I`, `isEmpty:()Z`;
* `equals:(Ljava/lang/Object;)Z` over exact UTF-16 units, including null/non-String;
* `hashCode:()I` using Java's `h = 31*h + codeUnit` modulo 32 bits;
* `toString:()Ljava/lang/String;` returning the same reference;
* `compareTo:(Ljava/lang/String;)I` with Java UTF-16 lexicographic order;
* `intern:()Ljava/lang/String;` returning/publishing the canonical same-content
  reference; and
* `charAt:(I)C` only for a valid index in MC-LB0.

Null receivers retain current implicit NPE behavior; a null `compareTo` argument
raises the same implicit NPE. An invalid `charAt` must hard fail
`StringProfileError(2,pc)` in MC-LB0 because `StringIndexOutOfBoundsException` and
its honest message constructor are not yet present; returning zero or raising
ArrayIndexOutOfBoundsException would be false Java semantics. Every constructor,
substring/concat/case/charset/regex/format/valueOf/getBytes/builder API and any
other String method is explicitly unsupported. `_resolveNewClass` must reject
canonical String before initialization or allocation, so a failed `new String`
does not leak a half-object. In particular, MC-LB0 cannot yet execute marker
formatting or create arbitrary command-line Strings.

Only exact reserved owner/name/descriptor/flags may select a binding. A user class,
lookalike method, overridden owner, wrong static/instance form, or altered bootstrap
image must never reach it. Refactor `_nativeBinding` into an explicit platform
binding descriptor that records receiver/arguments/return kind; do not broaden the
current four Float/Double bindings accidentally.

### Concrete runtime touch points

A freeze should name, at minimum, these monolith changes rather than authorizing a
broad library rewrite:

* `_readConstantPool`: retain tag-8 indices and run a checked post-CP structural
  pass (forward CP references are legal); do not host-decode bytes.
* `_readFields`/`FieldInfo`: retain a String constant CP index without truncating it
  into `uint64 constantValue`; keep all primitive handling byte-for-byte.
* class assembly in both public entry paths: compute an overflow-checked optional
  bootstrap plan, append the three new images after the 19 Throwables, and keep the
  raw-input maximum 64.
* `_predecode`: admit tag 8 only for `ldc`/`ldc_w`; tag 7 remains deferred to
  MC-LB1 and all other old tag/error rules remain exact.
* `_initializeClass`: resolve String `ConstantValue` through the same pool at the
  current constant-preparation point and carry arena/heap counters atomically.
* `_execute`: add one lazy `StringState` containing CP decode caches, hash buckets,
  canonical handles, and explicit pool size; route tag-8 loads through
  `_resolveStringConstant`, not a second implementation.
* invocation dispatch: extend the exact binding descriptor only for the named
  reserved String methods, including receiver and reference-return validation.
  No generic native fallback is permitted.

Helpers should be bounded and single-purpose (`_decodeModifiedUtf8`,
`_resolveStringConstant`, `_allocateLiteralString`, `_internString`, and full
collision comparison). Solidity stack-depth/code-size pressure is an implementation
risk to measure, not a reason to move decoding or String evaluation to Go.

### ABI and resource boundary

MC-LB0 deliberately leaves both public ABI selectors and return encoding unchanged:

```text
interpret(rawClass, entryName, int32[] args) -> int32
interpretClasses(rawClasses<=64, entryClass, entryName, int32[] args) -> int32
```

This lets trusted `(I...)I` fixtures test String behavior with integer checksums and
identity predicates without pretending to launch Java. No guest text is exported
and no output line can be fabricated.

Initial LOCAL test ceilings are finite: 100,000,000 gas and 30 seconds for ordinary
literal/method cases; 250,000,000 gas and 120 seconds for maximum-length, collision,
and quota-boundary verifier probes. These are new `mc-local-lb0` labels only. Measure
actual thresholds before freezing them. Do not raise any old fixture, S0/S1/S2a/
S2b-L, block, or standard-deployment budget.

## Bounded MC-LB0 gates

Use trusted new sources only; do not edit or regenerate old fixture sources.
Suggested acceptance is 48--64 new cases:

* same CP entry, duplicate CP entries, same payload across two classes, static final
  String `ConstantValue`, `<clinit>`/ordinary method identity, and reset between VM
  invocations;
* empty, ASCII, U+0000, two-byte boundaries, three-byte boundaries, paired and
  unpaired surrogates, and mixed strings;
* exact `length`, valid `charAt`, `equals`, `hashCode`, `compareTo`, `toString`, and
  `intern` results against Java 8; Java 21 remains a secondary cross-check;
* hash collisions with unequal content and long common prefixes;
* malformed tag/index, raw NUL, truncation, stray continuation, overlong non-NUL,
  and four-byte UTF-8, each with exact hard error location;
* String `ConstantValue` wrong descriptor/tag, duplicate attributes, and class-init
  failure ordering;
* one-under/exact/one-over object, array, element, intern, and shared-handle limits;
  intern hits allocate nothing, failed misses publish nothing, and OOM remains the
  existing catchable exact kind; and
* negative binding tests for wrong owner/descriptor/access flags, deferred
  constructor/method calls, and invalid `charAt`.

Retain all 2,231 accepted M5d-a rows with **unchanged sources, manifest outcomes,
per-case gas, and timeouts**. Retain parent exception/init/field-boundary probes,
all 24 current bootstrap source/hex hashes, strict old `JavaException(1..12)` ABI,
Go/CLI/Python tests, artifact reproducibility, smoke/full differential, demos, AOT,
and vet as proportionate. The runtime artifact hash will legitimately change only
from the pinned reproducible build and must be parent-reviewed; old bootstrap bytes
must not.

The ignored oracle for this proposal observed identically on OpenJDK 8u504 and Java
21.0.9:

```text
literal-cross=true
intern=true,true,true
utf16=7,0,7ff,800,d83d,de00,d800
class=true,true,true,int
throwable-message=true,java.lang.RuntimeException: same-payload
```

The Java 8 classfile encoded the edge literal as
`c08041dfbfe0a080eda0bdedb880eda080`: MUTF-8 NUL, ASCII, two/three-byte units, a
surrogate pair, and an unpaired high surrogate. This is oracle evidence only, not
an implementation or a Java SE claim.

## Next dependencies, kept separate

| Later slice | Minimum honest contract | Why not MC-LB0 / startup relevance |
|---|---|---|
| **M5d-b0 identity** | ordinary fresh Throwable/subclass construction, exact same-ref throw/catch/unwind, dynamic uncaught type ABI, Java-8 init wrapping | Required for library-defined exceptions. Reuse the queued proposal; do not add fake messages or traces. |
| **MC-LB1 Class mirrors** | one mirror per ClassKey for ordinary/interface/array/primitive types; `ldc` Class and `Object.getClass`; no target initialization by class literal; exact mirror identity across CPs/getClass/checkpoint | Whole JAR has 2,586 class loads and 512 getClass calls, but none appeared in the five directly inspected entry methods. Reflection APIs remain evidence-driven later work. |
| **MC-LB2 String construction/composition** | Java 8 char/byte constructors, copying/bounds exceptions, builders/buffers, boxing/valueOf, locale-pinned formatting and charset subset reached by startup | `nz.j` requires Double boxing and `String.format("%.3fs", Object[])` before `Done`. MC-LB0 literals alone cannot render it. |
| **Throwable message/cause core** | String/message identity, all actually reached constructors, exact cause sentinel and EIIE link, getMessage/getCause/toString; honor Java 8 fillInStackTrace behavior | `main` catches Exception and passes it to `Logger.fatal(String,Throwable)`. Success need not exercise this path, but unsupported errors must remain visible rather than be swallowed. |
| **Guest printing/logging** | guest Log4j formatting/configuration and PrintStream/Writer byte path ending in an EVM-owned ordered event sink; pinned UTF-8/default locale | The host may display events, never generate/search for `Done`. A Throwable event requires real guest trace/message data, not a synthesized launcher line. |
| **Main root** | separate public selector for exact public static `main:([Ljava/lang/String;)V`; EVM-decoded external UTF-8 arguments; allocated String[]; void root termination distinct from scheduler state | Root return only means the launcher fiber ended; `F()` has already started the server fiber. Empty args and `nogui` are different pinned workloads. |
| **Platform/continuation** | EVM VFS/JAR/resources, virtual clock/entropy/network bind, cooperative fibers/monitors/wait/notify as reached, and complete finite checkpoints | Required tasks execute; no blanket no-op threads/locks/I/O. World preparation and later tick loop cannot fit invocation-local reset semantics. |

The smallest honest Throwable API follow-up is not a no-op constructor set. First
land M5d-b0 exact object identity. Once String construction exists, add real
`Throwable()`, `Throwable(String)`, and `Throwable(String,Throwable)` state plus
only the forwarding constructors of exception/error classes proven reachable.
Preserve detail-message and cause references by identity. Defer
`Throwable(Throwable)` until virtual `cause.toString()` is real, and continue to
reject a user `fillInStackTrace` override until genuine guest frame snapshots are
available, as the queued M5d-b proposal requires. `getMessage`, `getCause`, and
`toString` may then expose only stored guest state. `printStackTrace` must wait for
real frame-to-StackTraceElement capture, cause/suppressed traversal, cycle
protection, and Writer/PrintStream output; an empty array, no-op, or host-generated
launcher line is not a minimum implementation.

Likewise, the minimum printing primitive is an EVM-owned ordered byte/event sink
under a pinned charset, stream, thread/fiber id, and sequence. Guest PrintStream,
Writer, and Log4j code must perform conversion and formatting before that boundary.
A host adapter may display committed bytes but cannot turn a Logger call plus raw
arguments into the message or special-case the `Done` literal. Whether the exact
reachable Log4j stack can be reduced to this primitive requires a separate static
and then in-EVM dependency trace.

For MC-LB1, mirror identity must use ClassKey, not current class-array position.
Class literals resolve/load/link but do not initialize the represented class;
`getClass` on an object/array returns that exact canonical mirror. Primitive class
literals compile through wrapper `TYPE` fields and need a separately pinned wrapper
profile. `Class.getName`, reflection, resources, annotations, and class loaders are
not implied by mirror existence.

For a future launcher, prefer a separate versioned interface conceptually like:

```text
startMain(rawPages, artifactCommitment, entryInternalName,
          utf8Args, platformCommitment, LocalLimits)
  -> {YIELDED | BLOCKED | ROOT_TERMINATED | UNCAUGHT, checkpoint, outputDelta}
```

Command-line input is canonical external UTF-8 (not classfile MUTF-8) decoded by
EVM. `ROOT_TERMINATED` does not discard runnable fibers. `outputDelta` contains
already guest-produced ordered bytes/events and provenance; it has no `READY`
shortcut. Every call has explicit finite gas, instruction, heap, output, checkpoint,
and wall-time watchdog bounds. A continuation transaction commits complete Java,
scheduler, intern/mirror, VFS, clock, and pending-output state before yielding;
the host transports opaque bytes/pages and never computes Java state or recovers
intermediate state from reverted OOG execution.

The genuine marker gate remains the program-pinned rendered body:

```text
Done (<one-or-more digits>.<exactly three digits>s)! For help, type "help" or "?"
```

Acceptance must additionally prove the guest returned from `nz.j`'s world
preparation call preceding PC 989 and that the logger event came from the server
fiber. Neither a literal test, a void main return, a `Thread.start` no-op, an early
banner, nor a host-matched hardcoded String is readiness.

## Suggested disjoint implementation ownership if frozen

This is a proposed split, not authorization to edit:

* **One runtime owner only:**
  `jvmevm/runtime/JVMSubsetInterpreter.sol`,
  `jvmevm/runtime/JVMSubsetInterpreter.runtime.hex`,
  `jvmevm/runtime/build.js`, and only new
  `jvmevm/runtime/bootstrap/{String,Comparable,CharSequence}.{java,class.hex}`.
  Own String state, MUTF-8, allocation/interning, field constants, and exact
  platform bindings. Do not touch stock S2b paths.
* **Fixture owner only:** new
  `jvmevm/testdata/differential/bundle/mclb0strings/` sources and a new local
  `mclb0-cases.fragment.json`; no edits to old sources, `cases.json`, README,
  runtime, or harness.
* **Independent verifier only:** new
  `jvmevm/mc_local_strings_validation_test.go`, with `mcLocalLb0*` helper names;
  malformed CP/MUTF-8, binding spoof, quota, and bootstrap-order checks only.
* **Parent only:** merge the fragment into `cases.json`, update README/build hash,
  resolve integration/error-code ordering, run all historical gates, and coordinate
  with M5d-b0, S2b-L, and the separate continuation/platform study.

Only one Solidity writer runs at once. No worker executes Minecraft, accepts EULA,
changes host-Java production behavior, touches EVM/core/consensus/precompiles,
raises stock budgets, edits peer work, pushes, changes global settings, or enables
Fast/priority.

## Evidence and uncertainty

Ignored evidence is under `build/java-diff-mc-local-bootstrap/` and is not part of
the commit:

* `inspection/MinecraftServer.javap.txt`, `nz.javap.txt`, and `ni.javap.txt` are
  bounded static disassemblies; SHA-256 respectively
  `7c00d11bc6efe0865647f483b33cd805ef1442b7c84ea6480d84d9088394ee6c`,
  `f02779977685aff3ba02f9eee59d32ac90f4f4c70624770606e6d492e1e6a95f`, and
  `3bc85b36b258b00d7f4623f506211b6dfa7b78d9e996eae095afe049d8cdb8fd`.
* `static_literals.py` is a read-only bounded prototype (64 MiB JAR, 25,000
  classes, 2 MiB/class, 128 MiB aggregate class bytes). Its JSON is SHA-256
  `82e9c1820b810f5c13626bdda3352d95e9bdb42e2d8cba67cd9931f4091b13f4`.
* `oracle/` contains only self-authored sources, separately compiled Java-8-target
  classes, ten-second/64 MiB Java 8 and 21 outputs, and raw CP evidence. Both
  stdout files have SHA-256
  `38cf0f63aba482ad1ae287d9ef71d3261cc275e0a506c4acc42ae8ff4b0a944a`.
* `metadata/current-runtime.json` records the current artifact size/hash;
  `metadata/jar.{sha1,sha256,size}` records the read-only pin checks.

The scan is not a call graph, cannot establish the reachable Java SE subset, and
may include client/optional/error code. No gas was measured for MC-LB0 because no
implementation exists. Exact reachable String/Class/Throwable/printing APIs,
heap/state scale, bootstrap-library provenance, scheduler semantics, virtual VFS
contents/configuration, EULA authorization, and total continuation budget remain
unfrozen. These uncertainties are reasons for measured later slices, not permission
to execute libraries on the host, fake platform success, or attempt all Java SE at
once.
