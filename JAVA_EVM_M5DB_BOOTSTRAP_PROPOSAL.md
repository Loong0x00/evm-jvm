# M5d-b bootstrap preflight: fresh Throwable identity and uncaught type transport

Status: **documentation/oracle-only proposal; not a frozen implementation contract
and not an acceptance claim**. Authority remains `JAVA_EVM_PROGRAM.md`. This was
prepared at base `fc9061c28fb7065097fff722915c3a5dd79b7b5d`, while the parent was
final-gating the 154,839-byte M5d-a candidate (2,231 differential cases and 187
parent semantic/field-quota probes). M5d-a must be accepted first. The parent must
freeze any implementation contract separately.

No Minecraft or third-party Java was executed, no EULA was accepted or written,
and no socket, server, or downloaded JAR was opened. The only executed Java was
bounded, trusted, self-authored oracle code on local Java 8 and Java 21 runtimes.
This proposal owns no Solidity, Go, fixture, harness, bootstrap image, or generated
runtime change.

## Recommendation

After M5d-a acceptance, take one small identity-complete slice, here called
**M5d-b0**, before String or general library bootstrap:

1. permit ordinary `new` plus normal constructor execution for the 18 concrete
   current canonical Throwable classes and for supplied user subclasses of
   `Throwable`, ending in the existing canonical no-argument constructor chain;
2. make `athrow` accept every initialized heap object whose dynamic class is
   assignable to canonical `Throwable`, preserving the exact reference and dynamic
   class through catches, calls, fields, arrays, rethrow, and initialization unwind;
3. preserve the exact `JavaException(uint256)` payloads for canonical kinds 1..12,
   and add a separate, strictly canonical uncaught ABI carrying only the dynamic
   class name for every other Throwable; and
4. preserve Java 8 class-initialization rules for freshly constructed custom
   `Error` and non-`Error` objects.

Do **not** add message, cause, stack-trace, `toString`, printing, `getClass`, Class
objects, String constants, `main(String[])`, reflection, monitors, native bindings,
or a host/JRE fallback in this slice. In particular, do not expose an API that
returns fabricated `null`, an empty stack, or a synthesized message merely to make
library calls appear to work.

This is useful to the Minecraft 1.12.2 route because ordinary libraries define and
throw their own exception/error subclasses, and preserving their dynamic identities
is a prerequisite for honest library execution. It is not enough to launch the
server: String/main/class objects and broad Throwable APIs remain explicit later
dependencies.

## Actual base inventory

The statements below refer to the checked source at `fc9061c`, not an intended
architecture.

* `JVMSubsetInterpreter.sol` has a shared one-based handle registry bounded by
  1,024 arrays + 1,024 ordinary objects + 256 arena exceptions + one emergency OOM.
  Ordinary objects have 1,024-field-per-object and 65,536-total-field limits;
  arena records instead have 262,144 total inherited field slots.
* `ExceptionArena` holds pending `{active, kind, ref, faultPC}`, class indices for
  kinds 1..12, cached per-dynamic-class default layouts, 256 fresh records, and the
  initialized emergency OOM at handle 1.
* The 19 reserved raw images are appended and parsed in the EVM. Each declares zero
  fields and only its compiler-generated no-argument constructor. The exact graph
  is the frozen M5d-a graph. User inputs may subclass it but may not replace any of
  the 19 names.
* `_resolveNewClass` deliberately rejects every class assignable to `Throwable`
  with `ObjectError(2, opPC)`. This is the precise gate M5d-b0 would relax.
* Ordinary `new` already initializes the target first, computes inherited layout,
  allocates an uninitialized object, and relies on normal `invokespecial` constructor
  execution and alias promotion. Abrupt constructors retain existing poisoning and
  unwind behavior.
* Current `athrow` accepts only a non-null `HEAP_OBJECT` with a nonzero low-byte
  arena kind. Therefore an otherwise genuine ordinary user Throwable cannot be
  thrown. Null raises fresh NPE6; a non-arena object fails `BytecodeError(14, pc)`.
* Handler matching already uses `heap.classes[pending.ref]` and ordinary hierarchy
  assignability, so dynamic class matching is structurally ready once pending refs
  are no longer restricted to arena-kind objects.
* Final uncaught delivery is only `JavaException(uint256)`. The Go decoder accepts
  exactly 36 bytes, exact selector, zero high bytes, and kinds 1..12; unknown,
  noncanonical, and trailing payloads remain execution failures.
* Both external entry APIs still require a unique static exact `(I...)I` root.
  Although general method descriptors can contain references/arrays and void,
  neither `main([Ljava/lang/String;)V` nor a launcher return boundary is available.
* `ldc`/`ldc_w` currently admit only integer/float tags (and `ldc2_w` long/double),
  not `CONSTANT_String` or `CONSTANT_Class`. There is no `java/lang/String`,
  `java/lang/Class`, or `Object.getClass` bootstrap service.
* The checked artifact is 154,839 decoded bytes, SHA-256
  `dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
  It is executed by local `runtime.Execute`, remains far over EIP-170, and is not
  standard-deployment evidence.

The ignored evidence records source excerpts and hashes in
`build/java-diff-m5db-preflight/metadata/current-*.txt`.

## Java 8 reference findings

The normative anchors used here are Java SE 8 JVMS §5.5 (initialization),
JVMS §6.5 `new`, JVMS §6.5 `athrow`, and JLS §12.4.2, plus the Java SE 8
`Throwable` and `ExceptionInInitializerError` API contracts. Saved official HTML
and a bounded text extraction are listed under Evidence.

### Construction and throw identity

* `new` resolves the named class, initializes it if necessary, allocates a new
  instance whose instance fields have default values, and pushes its reference.
  Constructor invocation is a separate `invokespecial`; allocation must not mark
  an object initialized early.
* `athrow` requires a reference assignable to `Throwable`. A null reference causes
  NPE. A non-null throw searches the current method then callers, and the thrown
  object is the same object delivered to a handler. `athrow` does not allocate a
  replacement merely because the dynamic type is user-defined.
* The class of an object, not an internal numeric exception kind, controls catch
  assignability and the `Error` decision during failed class initialization.

The trusted oracle agreed on Java 8 and 21:

```text
fresh=true,17,M5dbOracle$CustomRuntime,true,false
override=override:hello
```

The first line proves fresh custom instance identity, constructor field effects,
exact dynamic class, RuntimeException ancestry, and non-Error status. The second
shows that real `Throwable.getMessage` virtual dispatch reaches a user override;
it does **not** make getMessage part of M5d-b0.

### The zero-field images are not Java 8 `rt.jar`

The local OpenJDK 8u504 `java/lang/Throwable.class` is 8,827 bytes, major 52, and
has five instance reference fields: `backtrace`, `detailMessage`, `cause`,
`stackTrace`, and `suppressedExceptions`. Its no-argument constructor:

1. invokes `Object.<init>`;
2. stores `this` as the internal uninitialized-cause sentinel;
3. installs stack/suppression sentinels; and
4. invokes virtual `fillInStackTrace()`.

A self-authored subclass override observed one `fillInStackTrace` call during
`super()` on both Java 8 and Java 21:

```text
fill-override=1,1,same=true,after=2
```

This is observable constructor behavior even without `getStackTrace`. Therefore a
zero-field/no-op bootstrap constructor is sufficient only for an explicitly narrow
identity profile. M5d-b0 must reject construction of a user Throwable hierarchy
that overrides exact `fillInStackTrace:()Ljava/lang/Throwable;`; silently skipping
that callback would be false Java semantics. Supporting that override is deferred
with writable stack traces/synchronization rather than faked.

The Java 8 `Throwable` metadata also exposes four public constructors and one
protected constructor:

```text
()V
(Ljava/lang/String;)V
(Ljava/lang/String;Ljava/lang/Throwable;)V
(Ljava/lang/Throwable;)V
(Ljava/lang/String;Ljava/lang/Throwable;ZZ)V   // protected
```

It declares message/cause, printing, stack trace, and suppression APIs, including a
private native stack-fill primitive and synchronized methods. The current 162-byte
bootstrap is intentionally not that class library implementation. The actual 19
Java 8 class bytes/hashes and current 19 profile-image bytes/hashes are recorded in
`metadata/java8-throwable-class-hashes.txt` and
`metadata/current-bootstrap-images.txt`.

### Message, cause, and initialization outcomes

The Java 8/21 oracle agreed that:

```text
empty=true,true
message=true,identity-message
cause-only=true,M5dbOracle$CustomRuntime: override:cause
message-cause=true,true
initCause=true,java.lang.IllegalStateException,java.lang.IllegalArgumentException
eiie-ctors=true,true,true,true,true,true
four-arg=disabled,true,suppressed=0,stack=0
```

Consequences:

* no-arg `Throwable` externally reports null message and null cause, but its hidden
  cause state is not simply a null field;
* a message reference is preserved by identity;
* the cause-only constructor invokes the cause's virtual `toString` to derive a
  message, so it cannot be implemented honestly without String/toString support;
* `initCause` is one-shot, rejects self-causation, and requires at least
  `IllegalStateException` and `IllegalArgumentException` behavior;
* `ExceptionInInitializerError(Throwable)` preserves the same Throwable for both
  legacy `getException()` and `getCause()`; and
* the protected four-argument constructor controls suppression and writable stack
  traces. Returning fabricated empty arrays for the ordinary writable case would
  be wrong.

The initializer oracle also established:

```text
init-runtime-first=java.lang.ExceptionInInitializerError,true
init-error-first=true,M5dbOracle$CustomError
```

Thus a fresh custom RuntimeException leaving `<clinit>` is wrapped and retains the
original as EIIE cause, while a fresh custom Error leaves `<clinit>` as the exact
same object. This follows JVMS/JLS: wrap only a thrown object not assignable to
`Error`; if wrapper allocation fails, throw OOM; mark the class erroneous; later
active use throws NCDFE.

Java 8u504 and Java 21.0.9 differed on an implementation-visible NCDFE cause:

```text
Java 8:  init-*-second=java.lang.NoClassDefFoundError,cause=null
Java 21: init-*-second=java.lang.NoClassDefFoundError,cause=java.lang.ExceptionInInitializerError
```

Java 8 is the selected compatibility target. A later cause API must pin Java 8
behavior and must not infer Java 21 behavior from a modern oracle. M5d-b0 keeps
NCDFE12's existing external class result and exposes no cause API. It should retain
an internal exact cause link for a newly created EIIE wrapper so a later API can be
implemented without inventing history; NCDFE12 gets no exposed or fabricated cause
in this stage.

The normal Java launcher printed this for the trusted uncaught probe and exited 1
on both runtimes:

```text
Exception in thread "main" M5dbUncaught$CustomProblem: uncaught-message
```

That text is produced through launcher/Throwable/String/stack-printing facilities,
not by `athrow` itself. M5d-b0 must transport only exact class identity. It must not
synthesize this line, its message, thread name, or stack trace.

## Proposed exact M5d-b0 semantic boundary

### Raw classes and bootstrap profile

1. Keep exactly 19 reserved Throwable names and their exact M5d-a parent graph.
   User replacement remains `LinkError(6, inputIndex)` in both entry APIs.
2. Keep the current 19 raw source/hex images byte-for-byte in M5d-b0. They have zero
   declared fields and only no-arg constructor bytecode. This makes the slice an
   explicit identity/throw profile, not Java SE Throwable API conformance.
3. A supplied public or package-accessible class may directly or indirectly extend
   canonical Throwable. Normal hierarchy/access/finality checks apply. Interfaces
   do not become throwable classes merely by name.
4. `new` may target any non-abstract, accessible concrete canonical/user Throwable.
   `VirtualMachineError` remains abstract. Class initialization occurs before
   allocation exactly as for ordinary objects.
5. Supported user constructor bodies are the existing constructor bytecode/profile:
   current primitive/reference descriptors, fields, calls, and handlers. Their
   chain must ultimately invoke an available canonical `()V`. User constructor
   arguments may refer only to supplied/profile-supported types; an absent String
   type is not made valid merely because the runtime value is null.
6. Canonical `(String)`, `(String,Throwable)`, `(Throwable)`, and protected four-arg
   constructors are absent and unsupported. Resolution/invocation must fail hard
   and explicitly; no constructor may discard those arguments and claim success.
7. Before permitting allocation, scan the constructed user Throwable ancestry for
   an exact user declaration overriding
   `fillInStackTrace:()Ljava/lang/Throwable;`. Reject it with
   `ThrowableProfileError(1, classIndex, methodIndex)`. This restriction is checked
   on the selected dynamic class and inherited user ancestors. It is lifted only by
   a later real stack/synchronization slice.
8. Other user methods/fields remain ordinary methods/fields. M5d-b0 may prove a
   user-defined primitive method dispatches normally, but it makes no claim that a
   declaration matching `getMessage`, `getCause`, `toString`, or a stack API is a
   working override through the missing canonical API surface.

This preserves unchanged self-authored classfiles: the restriction is a declared
supported-profile rejection, never a classfile patch or host translation.

### Heap and exception arena

1. Every explicit `new`, including `new ArithmeticException()` and a user subtype,
   is an **ordinary object allocation**. It consumes `MAX_OBJECTS`, per-object field
   limit, total ordinary field slots, and one shared handle. It does not consume the
   256-record VM exception arena.
2. The allocated dynamic class and all user/inherited field cells are normal heap
   data. The reference remains `KIND_UNINIT` until the normal constructor chain
   returns. Constructor failure never promotes aliases and does not refund the
   no-GC allocation.
3. VM-generated implicit exceptions, EIIE wrappers, NCDFE, SOE, and logical OOM
   continue to use fresh arena records and the emergency OOM exactly as in M5d-a.
   Their allocation remains possible when ordinary object quota is full.
4. Decouple “is a Throwable” from the low byte currently used for arena kind.
   `heapClasses[handle]` plus canonical hierarchy is authoritative for every object.
   Low-byte kinds may remain an internal optimization for VM-created exact canonical
   records but may not reject an ordinary Throwable or label a subtype as its parent.
5. Add internal wrapper-cause storage sufficient to bind a VM-created EIIE to the
   exact previous pending ref. It is not exposed in M5d-b0. Reusing emergency OOM
   remains cause-free. Do not store a fabricated String/message/trace.
6. `athrow` of an existing ordinary or arena Throwable allocates nothing, including
   after either arena or ordinary-object exhaustion. Null alone allocates NPE (or
   uses emergency OOM if the arena cannot allocate NPE).
7. All heap and wrapper state resets per invocation under the present runner. This
   is not persistent-server state.

### `athrow`, catches, and initialization

* Initialized non-null object: validate handle, require dynamic class assignable to
  canonical Throwable, then set pending with the same ref, dynamic class, and throw
  PC. Do not infer identity from source syntax or constructor owner.
* Null initialized ref: preserve M5d-a fresh NPE6/emergency behavior.
* Uninitialized ref, array, int/category mismatch, invalid handle, or initialized
  non-Throwable: hard `BytecodeError(14, pc)`/`ReferenceError(1, pc)` according to
  the existing malformed-bytecode split. Such verifier/profile failures are not
  catchable Java exceptions.
* Handler order, range PC, stack clearing, caller invoke PC, constructor poisoning,
  and same-ref rethrow remain exactly M5d-a.
* A custom subtype catches by exact type and all real supertypes. A sibling or a
  parent-specific canonical kind does not match merely because an internal kind
  number happens to be shared.
* An unhandled fresh non-Error leaving `<clinit>` marks that class erroneous and is
  replaced by a fresh canonical EIIE3 whose retained internal cause ref is the
  custom object. Arena exhaustion while making the wrapper yields emergency OOM7.
* An unhandled fresh custom Error/subtype leaving `<clinit>` marks the class
  erroneous and propagates the exact same custom ref without EIIE wrapping.
* A later active use still raises fresh canonical NCDFE12. No message/cause API is
  claimed. Errors from failed prerequisites continue to propagate per M5d-a.

### Canonical uncaught ABI

Preserve the existing ABI exactly for an uncaught object whose **dynamic class is
exactly** one of the 12 canonical kind classes:

```text
JavaException(uint256)  // exact existing 36-byte encoding, kinds 1..12
```

This applies whether that exact canonical object was VM-generated or explicitly
constructed. A user subclass of `ArithmeticException` is not kind1 at the boundary;
its dynamic class must not be erased.

For every other uncaught Throwable, add:

```text
JavaThrowable(bytes internalName)
```

`internalName` is the exact validated classfile internal binary name from the
EVM-resolved dynamic class, not a guest String, message, cause, object ref, or host
lookup. The final payload is canonical only when:

1. the selector is exactly `keccak256("JavaThrowable(bytes)")[0:4]`;
2. the first ABI word is exactly 32;
3. byte length is 1..65,535 and the total payload is exactly
   `4 + 32 + 32 + ceil(length/32)*32` bytes;
4. all padding bytes are zero and there are no trailing bytes; and
5. bytes are a valid classfile modified-UTF-8 internal binary name with nonempty
   slash-separated components and no `.`, `;`, `[`, NUL name character, empty
   component, or array descriptor.

The EVM validates/emits the dynamic name. The host decoder only validates canonical
ABI and modified UTF-8, converts the validated name to display UTF-8, and changes
`/` to `.` for `Result.ExceptionClass`. It does not inspect a classfile, resolve a
class, invoke Java, call `toString`, or guess a nearest known superclass. If safe
transcoding is not implemented, expose raw name bytes rather than accepting invalid
UTF-8. Unknown selectors, malformed offsets/lengths/padding/names, and trailing data
remain hard runner failures.

Examples:

| Dynamic class | Required uncaught payload |
|---|---|
| exact `java/lang/NullPointerException` | unchanged `JavaException(6)` |
| exact explicitly-created `java/lang/OutOfMemoryError` | unchanged `JavaException(7)` |
| `java/lang/RuntimeException` | `JavaThrowable(bytes("java/lang/RuntimeException"))` |
| `pkg/MyProblem` extends RuntimeException | `JavaThrowable(bytes("pkg/MyProblem"))` |
| `pkg/MyNPE` extends NullPointerException | `JavaThrowable(bytes("pkg/MyNPE"))`, not kind6 |
| custom Error escaping `<clinit>` | exact custom `JavaThrowable`, same guest ref internally |
| failed class's later active use | unchanged `JavaException(12)` |

Only the final external gateway emits a revert ABI. Modular interpreter components
must pass pending state explicitly; they must not use cross-contract revert decoding
as an exception/unwind implementation.

## Deferred dependency inventory

| Capability | Earliest dependencies | Why not M5d-b0 |
|---|---|---|
| `Throwable(String)` / message identity | String class/object representation, `CONSTANT_String`, immutable backing bytes/chars, constructor/call support | Discarding the String is observably wrong. |
| `Throwable(Throwable)` | cause storage plus virtual `cause.toString()`, therefore String and `toString` dispatch | Oracle proved derived message and override dispatch. |
| `getMessage` / `getLocalizedMessage` | real detail-message field and String return; virtual base declarations | A null stub is correct only for no-arg objects, not a truthful API. |
| `getCause` / EIIE `getException` | exact cause sentinel/state, EIIE link, Java-8-pinned NCDFE behavior; synchronized-method policy | Must preserve identity and distinguish uninitialized cause from explicit null. |
| `initCause` | above plus IllegalStateException, IllegalArgumentException and synchronized semantics | One-shot and self-cause failures are observable. |
| stack trace / `fillInStackTrace` | frame-to-StackTraceElement snapshots, arrays, String/Class metadata, writable/disabled rules and synchronization | No fabricated empty arrays or no-op fill. |
| suppression | Throwable arrays/collections, NPE/IllegalArgument failures, synchronized semantics | Four-arg constructor can disable it; final APIs are observable. |
| `toString` / printStackTrace | Class name, String/StringBuilder, append/formatting, PrintStream/Writer, cause/suppressed graph, cycle detection, trace data | Host must never synthesize launcher text. |
| `Object.getClass` / class literals | class-object heap identity, native/VM construction, `CONSTANT_Class` ldc, Class APIs and initialization rules | Uncaught ABI reads EVM class metadata; it is not a substitute guest API. |
| `main(String[])V` | void external root/termination result, String and String[] allocation, launcher class initialization, arguments/output boundary | Current root is exact `(I...)I`; keep M5d-b0 tests on it. |
| Minecraft launch | scalable class/artifact loading, String/main, JAR/resources, libraries, scheduler/time/VFS/logging/network and resumable state | Throwable identity is only one prerequisite. |

A sensible later order is: **M5d-b0 identity** → String/class-object data core →
message/cause constructors and read-only APIs → exact stack/suppression behavior →
void main launcher. Reachable 1.12.2 libraries should prioritize concrete APIs, but
unreachable Java SE completeness is not a prerequisite and missing APIs must fail,
not lie.

## Review of future canonical layout changes

M5d-b0 intentionally leaves the 19 zero-field images unchanged. When a later
Throwable-API slice changes them, it must atomically review all of the following:

1. Add only fields required by APIs whose semantics are actually implemented. A
   minimal library implementation need not be byte-for-byte OpenJDK, but each
   exposed constructor/method and every observable field relation must match the
   pinned Java 8 contract. Copying the 8,827-byte OpenJDK class is not viable by
   itself: it references Strings, collections, stack elements, I/O, synchronized
   methods, and native stack primitives.
2. `Throwable`'s Java 8 shape contributes five inherited instance references;
   EIIE contributes one more private `exception` field. `Error`, `Exception`, and
   RuntimeException add only static serial IDs in the inspected Java 8 classes.
3. Existing `_instanceFieldCount`, `_objectFieldDefaults`, arena
   `fieldDefaults[class]`, and `layoutsLoaded[class]` already cache full inherited
   layouts. Rebuilt raw images must invalidate old size/hash expectations and prove
   cached templates are distinct mutable allocations, not shared field arrays.
4. The emergency OOM is allocated first and consumes its real inherited field
   count. Every fresh arena record consumes its dynamic layout. Reprove the exact
   `MAX_EXCEPTION_FIELD_SLOTS=262144` boundary for emergency + up to 256 fresh
   records, including EIIE's extra field and a replaceable Object with inherited
   fields. Never silently fall back to a zero-field record.
5. Explicitly-created Throwables stay in ordinary quotas even after canonical
   fields grow; VM-generated records stay in arena quotas. Reprove the shared
   2,305-handle bound and no collision between both populations.
6. EIIE cause storage must have one canonical source of truth. Do not leave a side
   table and private field able to disagree when `getCause/getException` land.
7. Any static String/list/array sentinels imply real class initialization and heap
   objects. Do not hardcode fake handles or skip `<clinit>` to imitate OpenJDK.

## Modular stock-EVM fit

The parallel standard-deployment preflight should treat M5d-b0 as a state/interface
requirement, not a reason to enlarge the current monolith:

* heap records need stable `{dynamicClass, initialization status, fields}` across
  size-compliant modules and later continuation checkpoints;
* pending exception transport needs `{ref, dynamicClass, faultPC, origin}` plus an
  optional exact wrapper-cause ref, not only a kind byte;
* class/hierarchy and heap modules can determine assignability; the execution module
  performs handler order/unwind; only a final gateway selects `JavaException(1..12)`
  versus `JavaThrowable(bytes)`;
* raw bootstrap/class pages remain generic committed data parsed in EVM, never
  class-specific generated code; and
* a transaction boundary must serialize a pending custom ref and constructor/init
  state without converting it to a host exception or emitting an early uncaught ABI.

All modules must remain below EIP-170 and use ordinary CALL/DELEGATECALL/storage/code
paging under standard EVM rules. M5d-b0 on the present local `runtime.Execute` path
would be semantic evidence only, not deployment or continuation evidence.

## Suggested bounded gates

Append roughly 48–72 trusted Java 8 differential cases after preserving all 2,231
current cases and their budgets. Use only static `(I...)I` roots and no guest
printing/reflection/String APIs.

### Differential/oracle cases

* direct/indirect custom subclasses of Throwable, Exception, RuntimeException,
  Error, and one canonical leaf; exact/supertype/sibling/catch-all matching;
* canonical concrete no-arg construction, custom integer constructor fields,
  multi-level `super()` chains, constructor throw/poisoning, and class init before
  allocation;
* same-ref throw/catch/rethrow across all four invocation modes, locals, object
  fields, Throwable arrays, casts, `instanceof`, and finally;
* custom RuntimeException leaving `<clinit>` → EIIE3, custom Error leaving it
  unwrapped with identity, prerequisite propagation, then NCDFE12;
* uncaught exact canonical kinds retain all 12 old payloads; uncaught canonical
  non-kind roots and custom/subclass names use exact new payloads; and
* reset across invocation.

### Independent EVM/Go cases

* ordinary quota and field quota charge explicit Throwable construction; the 256+1
  arena remains independent; ordinary-full allocation raises catchable arena OOM;
* an existing custom Throwable can be rethrown after arena exhaustion without
  allocation; emergency OOM identity behavior remains unchanged;
* malformed `athrow` type/handle/uninitialized ref stays hard and uncatchable;
* fillInStackTrace override ancestry gets exact
  `ThrowableProfileError(1,classIndex,methodIndex)` before allocation;
* unsupported canonical constructor descriptors and absent String fail explicitly;
* strict `JavaThrowable(bytes)` decoder vectors: empty, bad offset, oversized length,
  truncation, nonzero padding, trailing bytes, malformed modified UTF-8, bad internal
  names, unknown selector, and a custom subclass of each old known kind;
* EIIE wrapper cause ref points to the original internally; custom Error path does
  not allocate a wrapper; wrapper arena exhaustion yields emergency OOM7; and
* old strict `JavaException` tests remain byte-for-byte unchanged for 1..12.

Initial finite budgets: ordinary identity/catch cases ≤30M gas, nested
constructor/init cases ≤80M, and quota/arena-only Go probes ≤250M. Use existing
10–30 second subprocess limits. Measure before changing any fixture budget; OOG
must remain a hard EVM failure outside guest catches. Rebuild/check all 24 current
bootstrap images and the runtime artifact, then run Go/CLI/Python/full differential,
smoke, named fixture fast tier, demos, AOT regression, and vet as the parent deems
proportionate. “Fast” here is only the existing fixture tier; new workers remain
Sol/high without Fast/priority.

## Suggested disjoint ownership if frozen

* **Runtime owner only:** pending/heap type identity, `new` gate, `athrow`, custom
  initialization propagation, internal EIIE link, final Solidity errors, raw artifact
  and only bootstrap files explicitly frozen. One Solidity writer.
* **Host/ABI owner only:** strict `JavaThrowable(bytes)` canonical decoder and Result
  representation, preserving the old decoder exactly; new uniquely prefixed tests.
* **Fixture owner only:** trusted differential sources/cases/README, no host harness
  semantic changes and no Java library calls in guest entries.
* **Independent verifier only:** malformed class/athrow/profile/ABI/quota tests with
  stage-prefixed helpers; no production runtime edits.
* **Parent only:** stage freeze, AGENTS/program/quickstart/Make targets, integration,
  bootstrap hash approval, full gates, and modular-deployment coordination.

No worker should run Minecraft/untrusted Java, accept an EULA, modify consensus/EVM
limits, add native services, push, alter global settings, or write peer-owned paths.

## Evidence

All evidence is ignored and not committed. It was produced on 2026-09-08 UTC.

* `build/java-diff-m5db-preflight/src/M5dbOracle.java` and
  `src/M5dbUncaught.java`: trusted self-authored probes.
* `run_probes.sh`: 30-second bounded compile/run/javap commands. Java 8 is local
  OpenJDK `1.8.0_504-b01`; Java 21 is Oracle `21.0.9+7-LTS-338`.
* `oracle/java8.stdout` (633 bytes) and `oracle/java21.stdout` (699 bytes): exact
  outcomes above. Both normal stderr files are empty.
* `oracle/java{8,21}-uncaught.{stdout,stderr,exit}`: both stdout files empty; both
  exits are 1; both first stderr lines are the exact launcher line quoted above.
* `metadata/java8-Throwable.javap.txt` and
  `java8-ExceptionInInitializerError.javap.txt`: private descriptors and bytecode
  from local Java 8 `rt.jar`.
* `metadata/java8-core-signatures.javap.txt` and `java8-probe.javap.txt`: selected
  Java 8 API/probe descriptors and generated classfile bytecode.
* `metadata/java8-*.class` plus `java8-throwable-class-hashes.txt`: bounded extraction
  of only the 19 relevant local library classes; they were inspected, not executed
  as external input.
* `metadata/java21-Throwable.java` and
  `java21-ExceptionInInitializerError.java`: local JDK 21 source snapshots used only
  as secondary comparison.
* `metadata/current-runtime-excerpts.txt`, `current-host-excerpts.txt`,
  `current-source-hashes.txt`, `current-artifact.txt`, and
  `current-bootstrap-images.txt`: exact base evidence.
* Local Java 8 `rt.jar`: 65,731,803 bytes, SHA-256
  `85fb70f0b55ac1c84f2a5b2bc70d128db81749cc8ae0b5cc99cf7ea2df2c6097`.
  Local JDK 21 `src.zip`: 45,510,546 bytes, SHA-256
  `56b50f2351b91cb1ac9703c64c3211c9109a36f4a30f7551dbbe9b27d00658d4`.
* `spec/*.html` are bounded snapshots of official Oracle Java SE 8 specification/API
  pages; `spec/sources.txt` lists exact URLs; `extract_spec.py` produced
  `spec/selected-sections.txt` without executing Java.
* `SHA256SUMS.txt` (45 evidence files), SHA-256
  `12712cf8d68b32636d96af94901ebfe6579e8ea2e2e1d83e1a190aa6ad300fa9`.
  `spec/SHA256SUMS.txt`, SHA-256
  `efa5916ea0c2d859392f3e3e2adfa7ed8bca3f7527903ccc7fde4a6d7ca77b76`.

These probes establish precise reference behavior and dependency boundaries only.
They do not prove M5d-b0, Java SE conformance, standard deployment, persistence,
Minecraft launch, EULA passage, or the genuine 1.12.2 `Done` marker.
