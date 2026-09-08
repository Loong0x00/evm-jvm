# M5d-a architecture preflight: implicit exceptions, handlers, and unwind

Status: **proposal only; not a frozen implementation contract**. Parent review must
freeze or amend it before production, fixture, or verifier work starts. Base inspected:
`c6b6584951aa426212deb085e3d3ee359bf1fc46` (accepted M5c-d).

This proposal deliberately chooses an **implicit-exceptions-first vertical slice**.
It makes every Java outcome already produced by the interpreter a real, catchable,
initialized guest reference; parses and executes ordered exception tables; unwinds
through Java calls and class initialization; and adds only the `athrow` behavior needed
to rethrow a previously captured VM exception. It does not add public Throwable
construction, constructors, messages, stack traces, reflection, or other JRE APIs.

## 1. Recommended bounded stage

Accept M5d-a atomically only when all of the following work together:

1. Parse and validate exception tables for every entered `Code` attribute.
2. Represent kinds 1..11 as pending `{kind, ref, faultPC}` exceptions instead of
   immediately reverting.
3. Search handlers in classfile order, with `[start_pc,end_pc)` coverage,
   catch-all and subtype matching, clear the selected frame's operand stack, and
   push exactly the same exception reference.
4. Unwind across ordinary calls using the callee frame's `callPC` as the caller's
   fault PC.
5. Make class-initialization failure and erroneous-state behavior coherent,
   including one-time EIIE wrapping and catchable later NCDFE kind 12.
6. Admit opcode `athrow` only for null (which raises NPE) or an initialized,
   registry-known VM Throwable reference previously captured by guest code.
7. Allocate VM-created Throwables in a bounded arena independent of ordinary
   object and array quotas, including a reserved emergency OOM reference.

Do not split acceptance into “athrow first” or “handlers for arithmetic only.” Either
would leave other existing Java kinds bypassing handlers and would establish the wrong
unwind/init abstraction. Implementation may use reviewable subcommits (bootstrap and
parser, pending/unwind core, initialization, tests), but the externally claimed stage
must remain atomic. One Solidity writer is required because these changes meet in the
single dispatcher and shared heap namespace.

Explicitly deferred to M5d-b or later:

- `new` of any `Throwable` subtype, user Throwable constructors, and arbitrary
  user-created throwable identities;
- `Throwable`/`Exception` methods, message/cause/stack-trace APIs, printing,
  suppressed exceptions, and native fill-in-stack-trace behavior;
- Java library fallback, host Throwable objects, host class loading, or host-side
  exception matching;
- monitors/synchronized unwinding, `finally` language transformations beyond the
  ordinary catch-all table entries already emitted as bytecode, `jsr`/`ret`, threads,
  asynchronous exceptions, and a full verifier.

## 2. Current implementation findings at c6b6584

The production path is the monolithic
`jvmevm/runtime/JVMSubsetInterpreter.sol`; runtime artifact is 135,652 bytes,
SHA-256 `cf68495083ebcd2df93f6d676e16afad87192a3401bd743a0301d805d5a8cd15`.
The execution boundary remains local `runtime.Execute`, not EIP-170 deployment.

### Current rejection and throw paths

- `Selected` records Code offset/length and stack/local limits but no handler table.
- Root `_readCode` rejects every nonzero `exception_table_length` as
  `MethodError(8)`. `_readCallCode` returns false for it, which callers surface as
  `CallError(4, callPC)` or `InitError(1, classIndex)`.
- `_instructionWidth` does not admit `0xbf`; entered `athrow` is `BytecodeError(6,pc)`.
- There are 19 `_throwJava` call sites: I/J division, array load/store/null/bounds/
  store checks, object and array allocation, field/call null checks, checkcast, and
  array store. `_throwJava` immediately reverts.
- There are seven direct `revert JavaException(2)` frame-cap paths: initializer
  body scheduling, four ordinary call forms plus interface-special, and
  `_initializeClass` continuation scheduling.
- Kind 10 is directly reverted by `_findInterfaceMethod`. Kind 11 is directly
  reverted by `_selectInterfaceImplementation`, `_selectVirtual`, and
  `_resolveInterfaceSpecial` paths. These helper reverts currently cannot carry a
  handler-visible fault PC.
- `_throwJava` uses `_hasActiveInitializer` and immediately turns every non-Error
  kind into kind 3 if *any* initializer frame is active. Consequently it cannot
  first search a helper's or `<clinit>`'s handlers.

All of those Java paths—not only `athrow`—must migrate. Solidity custom errors for
validation and EVM OOG must not migrate.

### Frames, calls, initialization, and heap today

- Every ordinary child created by invokevirtual, invokespecial, invokestatic, or
  invokeinterface receives the invoking instruction's `opPC` in `Frame.callPC`.
  Normal return already reads this field for caller stack-capacity attribution.
  It is the correct unwind PC as well.
- The 128-frame array currently contains Java frames and synthetic initialization
  continuations. A root Java frame is created before root initialization and is
  suspended while continuations and initializer frames run.
- Initialization state is `0` uninitialized, `1` initializing, `2` initialized;
  there is no erroneous state. Continuations retain only a class index.
  `initializerStarted` is a separate Boolean array. A caught scheduling failure
  would currently leave state 1 if direct reverts were merely replaced in place.
- Arrays and ordinary objects share one one-based handle registry, while logical
  limits are independent: 1,024 arrays, 262,144 aggregate array elements, 65,536
  elements per array; 1,024 ordinary objects, 1,024 fields per object, and 65,536
  aggregate ordinary field slots. There is no GC. Registry tables are currently
  sized to 2,048 handles and allocated lazily.
- Initialized references already move through locals, stacks, static/instance
  fields, arrays, calls, returns, casts, `instanceof`, and reference comparisons.
  Canonical exceptions should use that machinery, not a second fake reference kind.

## 3. Normative semantic basis

The implementation contract should cite these Java SE 8 sections directly:

- [JVMS 2.10, Exceptions](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-2.html#jvms-2.10): precise synchronous exceptions, current-frame-first search,
  abrupt frame completion, inter-frame rethrow, subtype matching, and table order.
- [JVMS 4.7.3, Code](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.3): table encoding, significant order,
  `start_pc` inclusive, `end_pc` exclusive, handler instruction boundary, and
  catch type/catch-all rules.
- [JVMS 4.9.1/4.9.2](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.9): code boundaries and verifier obligation that nonzero catch types are
  `Throwable` subtypes.
- [JVMS 5.5, Initialization](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html#jvms-5.5): four states, recursive success,
  erroneous-state NCDFE, prerequisite propagation, EIIE wrapping only at the
  actual initializer boundary, and OOM replacement if wrapper creation fails.
- [JVMS 6.5, `athrow`](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html#jvms-6.5.athrow): same reference is thrown/pushed,
  null becomes NPE, selected stack is cleared, and intervening frames are discarded.

The stage is still a supported-profile VM, not verification conformance. It should
implement the listed constraints deterministically and reject unsupported/malformed
input as EVM validation errors rather than claim full JVMS 4.10 dataflow checking.

## 4. Canonical Throwable class graph

### Exact minimal graph and kind binding

Append the following **19 canonical raw classfiles** in addition to the existing five
bootstrap images. Names and direct superclass edges are fixed. “Family” controls
initializer wrapping; matching itself always uses graph assignability.

| Kind | Canonical internal name | Exact direct superclass | Family |
|---:|---|---|---|
| — | [`java/lang/Throwable`](https://docs.oracle.com/javase/8/docs/api/java/lang/Throwable.html) | `java/lang/Object` | root |
| — | [`java/lang/Error`](https://docs.oracle.com/javase/8/docs/api/java/lang/Error.html) | `java/lang/Throwable` | Error |
| — | [`java/lang/VirtualMachineError`](https://docs.oracle.com/javase/8/docs/api/java/lang/VirtualMachineError.html) | `java/lang/Error` | Error |
| 2 | [`java/lang/StackOverflowError`](https://docs.oracle.com/javase/8/docs/api/java/lang/StackOverflowError.html) | `java/lang/VirtualMachineError` | Error |
| 7 | [`java/lang/OutOfMemoryError`](https://docs.oracle.com/javase/8/docs/api/java/lang/OutOfMemoryError.html) | `java/lang/VirtualMachineError` | Error |
| — | [`java/lang/LinkageError`](https://docs.oracle.com/javase/8/docs/api/java/lang/LinkageError.html) | `java/lang/Error` | Error |
| 3 | [`java/lang/ExceptionInInitializerError`](https://docs.oracle.com/javase/8/docs/api/java/lang/ExceptionInInitializerError.html) | `java/lang/LinkageError` | Error |
| 10 | [`java/lang/IncompatibleClassChangeError`](https://docs.oracle.com/javase/8/docs/api/java/lang/IncompatibleClassChangeError.html) | `java/lang/LinkageError` | Error |
| 11 | [`java/lang/AbstractMethodError`](https://docs.oracle.com/javase/8/docs/api/java/lang/AbstractMethodError.html) | `java/lang/IncompatibleClassChangeError` | Error |
| 12 | [`java/lang/NoClassDefFoundError`](https://docs.oracle.com/javase/8/docs/api/java/lang/NoClassDefFoundError.html) | `java/lang/LinkageError` | Error |
| — | [`java/lang/Exception`](https://docs.oracle.com/javase/8/docs/api/java/lang/Exception.html) | `java/lang/Throwable` | Exception |
| — | [`java/lang/RuntimeException`](https://docs.oracle.com/javase/8/docs/api/java/lang/RuntimeException.html) | `java/lang/Exception` | Exception |
| 1 | [`java/lang/ArithmeticException`](https://docs.oracle.com/javase/8/docs/api/java/lang/ArithmeticException.html) | `java/lang/RuntimeException` | Exception |
| — | [`java/lang/IndexOutOfBoundsException`](https://docs.oracle.com/javase/8/docs/api/java/lang/IndexOutOfBoundsException.html) | `java/lang/RuntimeException` | Exception |
| 5 | [`java/lang/ArrayIndexOutOfBoundsException`](https://docs.oracle.com/javase/8/docs/api/java/lang/ArrayIndexOutOfBoundsException.html) | `java/lang/IndexOutOfBoundsException` | Exception |
| 6 | [`java/lang/NullPointerException`](https://docs.oracle.com/javase/8/docs/api/java/lang/NullPointerException.html) | `java/lang/RuntimeException` | Exception |
| 4 | [`java/lang/NegativeArraySizeException`](https://docs.oracle.com/javase/8/docs/api/java/lang/NegativeArraySizeException.html) | `java/lang/RuntimeException` | Exception |
| 8 | [`java/lang/ClassCastException`](https://docs.oracle.com/javase/8/docs/api/java/lang/ClassCastException.html) | `java/lang/RuntimeException` | Exception |
| 9 | [`java/lang/ArrayStoreException`](https://docs.oracle.com/javase/8/docs/api/java/lang/ArrayStoreException.html) | `java/lang/RuntimeException` | Exception |

`Throwable` should directly implement the already bootstrapped
`java/io/Serializable`; the remaining direct interfaces are empty. Public/abstract
flags should agree with Java 8 (`VirtualMachineError` is abstract). This is an exact
name/parent/type graph, **not** the fields, constructors, serialization form, or API
surface of the Java SE classes.

### Raw bootstrap and anti-spoofing policy

- Keep source plus `.class.hex` for each class under `jvmevm/runtime/bootstrap/`.
  Compile all bootstrap sources together with `javac --release 8 -g:none
  -Xlint:-options`, record exact lengths and SHA-256 values, compare source, checked
  hex, fresh javac output, and Solidity-embedded bytes in `build.js`, then parse
  every embedded image through `_parseBundleClass` inside EVM.
- The 19 names above are VM-reserved. Reject a user input declaring one with
  proposed `LinkError(6, inputIndex)` in both entry APIs; never let user bytes replace
  or duplicate canonical Throwable classes. Existing supplied/bootstrap policy for
  Object, Cloneable, Serializable, Float, and Double is unchanged.
- Preserve max 64 **user** classes. Worst case is 64 users + five existing internal
  classes + 19 Throwable classes = 88 runtime classes. Add
  `MAX_RUNTIME_CLASSES = 88` and assert the graph stays below
  `ARRAY_CLASS_BASE == 256`; valid runtime class indices are therefore 0..87.
- Reject `new` for the canonical classes **and every user class assignable to
  canonical Throwable** as `ObjectError(2,pc)` in this stage. This makes fresh user
  Throwable construction explicitly unsupported even though minimal bootstrap
  classfiles contain compiler-generated constructor metadata.
- VM-created instances bypass Java constructors and are born initialized. No
  `<clinit>` or Java method is executed to raise an implicit exception.

A user class may extend a canonical Throwable class so its catch type can be validated,
but it cannot be allocated in M5d-a. An ordinary heap object is never accepted by
`athrow` merely because malicious bytecode gives it a suggestive class name.

## 5. Shared registry and separate exception arena

Choose a finite arena of **256 fresh VM-exception objects plus one reserved emergency
OOM object**. This is intentionally smaller and cheaper than 1,024; the cap is visible
Java resource semantics and must be tested, not hidden. Parent may choose 1,024 before
freeze, but the number must then be one constant everywhere.

Proposed constants and accounting:

```text
MAX_ARRAYS             = 1024       (unchanged)
MAX_OBJECTS            = 1024       (ordinary objects; unchanged)
MAX_EXCEPTION_OBJECTS  = 256        (fresh arena objects)
EMERGENCY_EXCEPTION_OBJECTS = 1
MAX_HANDLES = 1024 + 1024 + 256 + 1 = 2305
```

Registry contract:

1. Preserve one nonzero, unforgeable handle namespace. Extend `heapKinds`,
   `heapClasses`, `objectHeap`, and validity metadata to `MAX_HANDLES + 1`.
   Add `exceptionKinds[handle]` (zero means not a VM Throwable) and optional
   `exceptionCauses[handle]`. All handles are checked by registry membership;
   zero remains only Java null.
2. Reserve handle 1 for one initialized canonical OutOfMemoryError. Lazily creating
   the registry initializes this real `HEAP_OBJECT` entry before any ordinary or
   exception allocation and sets `nextHandle = 1`. It is not a magic packed value,
   hidden zero ID, or out-of-table sentinel.
3. A normal implicit throw allocates a fresh zero-field `HEAP_OBJECT`, assigns its
   canonical dynamic class, records its kind, and increments only
   `exceptionObjectCount` and `nextHandle`. It does **not** increment ordinary
   `objectCount` or `totalFieldSlots`.
4. Ordinary objects and arrays continue incrementing only their existing counters.
   Their quotas and no-GC behavior do not change merely because exceptions were
   caught. Separate maxima mathematically guarantee `nextHandle <= MAX_HANDLES`;
   still guard this invariant before every registry write.
5. If a 257th fresh exception is needed, raising any kind is replaced by pending
   kind 7 using the reserved emergency OOM reference. The arena remains exhausted;
   later raises continue to use that same emergency reference. Reuse at this
   emergency boundary is an explicit bounded-resource deviation, analogous to
   VM-preallocated OOM/SOE objects, and identity before that boundary remains fresh.
6. Logical ordinary OOM (array/object/count/slot limits) allocates from this separate
   arena. Therefore `catch (OutOfMemoryError e)` works even after all 1,024 ordinary
   objects, all 1,024 arrays, or aggregate ordinary slots/elements are consumed.
7. If EVM memory expansion or gas itself fails while setting up/using the arena,
   that is still uncatchable EVM OOG. Never relabel it Java OOM.

Because canonical objects are ordinary initialized `KIND_REF` values with real dynamic
classes, captured references automatically support identity comparisons, locals,
static and instance fields, reference arrays, call/return transport, `checkcast`, and
`instanceof`. Throwable classes have zero guest fields in this slice, so arena objects
do not consume ordinary field slots. `exceptionCauses[wrapper] = originalRef` is a
useful future-proof internal relation for EIIE; no guest cause/message API is exposed.

## 6. Pending exception state and precise fault PCs

Add execution-local state conceptually equivalent to:

```solidity
struct PendingException {
    bool active;
    uint8 kind;       // canonical ABI kind 1..12
    uint32 ref;       // nonzero registry handle with exceptionKinds[ref] == kind
    uint32 faultPC;   // opcode start in the Java frame currently being searched
}
```

`MAX_CODE < 65536`, so `uint32` is ample; implementations may use full words if that
is cheaper in Solidity. There must be exactly one source of truth. Never encode a
pending exception as a Solidity revert and then try to recover it through an external
self-call.

A `_raiseKnown(kind, opPC, ...)`-style helper allocates/falls back to an exception
reference, writes all three pending fields, and returns control to the dispatch loop.
After a raise, the opcode branch must perform no later guest-visible mutation. The
main loop processes pending state before fetching another opcode.

### Current Java path migration

- All 19 `_throwJava` sites pass their own `opPC` and become `_raiseKnown` paths.
- All bytecode-call frame-cap checks raise kind 2 at the invoking `opPC` without
  creating a child frame. The current frame can therefore catch SOE without needing
  the unavailable frame.
- Initialization scheduler cap handling follows section 8 below.
- `_findInterfaceMethod`, `_selectInterfaceImplementation`, `_selectVirtual`, and
  `_resolveInterfaceSpecial` must return an explicit Java-fault status (10 or 11)
  to the dispatcher, which raises it at the original invoke `opPC`. They must retain
  direct reverts for malformed/unsupported EVM validation cases.
- Kind 3 is created only at an escaping actual `<clinit>` boundary. Kind 12 is
  created only on active use of a class already in erroneous state.
- `_throwJava` and `_hasActiveInitializer` are deleted; “some initializer exists”
  is not a valid wrapping criterion.

## 7. Handler table representation, validation, and resolution

Add an ordered handler array to each loaded `Selected`, containing at least
`startPC`, `endPC`, `handlerPC`, raw `catchType`, and a lazy resolved-class cache.
Use a per-entered-method cap:

```text
MAX_EXCEPTION_HANDLERS = 1024
```

The classfile field is u2, but admitting 65,535 entries would make one fault scan an
unreasonable gas/memory operation. No GC and finite gas still apply. Preserve table
order exactly; overlapping/non-nested entries and duplicate entries are legal.

### Proposed exact validation error

Add:

```solidity
error HandlerError(
    uint256 code, uint256 classIndex, uint256 methodIndex, uint256 entryIndex
);
```

Use `entryIndex = type(uint256).max` for whole-table/method errors.

| Code | Meaning |
|---:|---|
| 1 | `exception_table_length > MAX_EXCEPTION_HANDLERS` |
| 2 | `start_pc >= end_pc`, `end_pc > code_length`, or `handler_pc >= code_length` |
| 3 | start/handler is not an instruction start, or end is neither an instruction start nor `code_length` |
| 4 | nonzero `catch_type` is not a valid `CONSTANT_Class` -> valid non-array internal class name chain |
| 5 | a range-applicable nonzero catch class cannot be found in the supplied/internal class graph |
| 6 | resolved catch class is not a class assignable to canonical `java/lang/Throwable` |
| 7 | method has a handler but `max_stack < 1` |

Truncation or inconsistent outer Code attribute lengths retain the existing
mode-appropriate Code/Class/Call/Init errors; do not read beyond the attribute and
misreport a range error. HandlerError is an EVM validation failure and is uncatchable.

Parsing/validation policy:

1. `_readCode` and `_readCallCode` retain all entries instead of rejecting nonzero
   length and still parse nested attributes after the table.
2. Validate code-relative integer ranges and catch CP shape while loading.
3. `_predecode` returns/retains the instruction-start map long enough to validate
   start, end, and target boundaries. Handler entry is valid even if ordinary
   control flow does not branch there.
4. Resolve a nonzero catch class **lazily, when its entry is reached during a pending
   scan and its PC range applies**. Cache the class index per method/entry. Resolution
   does not initialize the catch class.
5. Do not skip an applicable earlier entry because resolving it fails. Raise
   HandlerError 5/6 before considering later entries. A structurally malformed CP
   entry is already HandlerError 4 at method load. Catch-all (`catch_type == 0`)
   needs no resolution.
6. User catch classes are allowed if normal EVM hierarchy validation proves they
   are Throwable subtypes. Missing classes remain bounded-profile EVM linkage/
   handler failures; do not fabricate NCDFE for them. Kind 12 is reserved for an
   already-attempted failed initialization.

This timing is deterministic and avoids resolving never-applicable catch classes,
while being honest that it is not a full eager verifier/linker.

## 8. Handler search and inter-frame unwind algorithm

For a pending exception, inspect the current **Java** frame's table from entry zero:

```text
rangeMatches := startPC <= pending.faultPC && pending.faultPC < endPC
typeMatches  := catchType == 0 || thrownDynamicClass <: resolvedCatchClass
```

The first entry satisfying both wins. On a match:

1. retain the Java frame and all initialized locals (subject to constructor poisoning
   below);
2. set `pc = handlerPC`;
3. set logical `sp = 0`, ignoring all stale backing cells;
4. push exactly `_packRef(pending.ref)` as one category-1 word;
5. clear pending state and resume dispatch.

`max_stack >= 1` was validated, so handler entry cannot itself fabricate a stack
capacity fault. The reference is the same identity on rethrow or across frames.

If no entry matches, discard the Java frame. Before searching its invoker, set
`pending.faultPC = popped.callPC`. This is essential: the callee's throwing opcode is
used only against callee handlers; the caller's handler range is tested against the
invoke opcode. Continue until a handler is found or no eligible Java frame remains.
Uncaught known pending state becomes the external ABI outcome in section 10.

Synthetic initialization continuations have no handlers. They run the transition
rules below and forward the pending reference to either another continuation or the
Java instruction that initiated initialization. EVM validation errors and OOG never
enter this loop.

## 9. Class initialization and erroneous states

Use four explicit states:

```text
0 UNINITIALIZED
1 INITIALIZING_BY_THIS_EXECUTION
2 INITIALIZED
3 ERRONEOUS
```

This remains a single-thread VM, so state 1 recursively requested by the same execution
completes normally. No monitor/thread claim is made.

### Scheduling and continuation metadata

Replace Boolean-only continuation state with a tagged frame/continuation that records:
class, current phase (prerequisite versus own `<clinit>`), whether an initializer body
was actually started, and the Java `requestPC`/entry origin to which an abrupt result
must be delivered. Continuations still count against `MAX_FRAMES = 128`.

Capacity must be checked **before** changing a target from state 0 to state 1 or
applying ConstantValue preparation when a continuation is required. If no slot exists,
raise SOE at the requesting Java opcode and leave that not-yet-started target state 0.
If an already-active owner's attempt to schedule a prerequisite fails, unwinding its
installed continuation marks the active owner erroneous; the untouched prerequisite
stays 0. State 1 must never remain sticky after a catchable scheduler failure.
Trivial no-`<clinit>` classes with already-ready prerequisites may complete without
inventing an unnecessary frame, but state transitions must remain ordered.

At VM entry, initialize the selected root class **before creating or making eligible
the root Java method frame**. Keep root args externally until initialization succeeds,
then create/populate the root frame. Therefore failure of the root class, its
superclass, or required default interface cannot be caught by a handler in a method
whose invocation never began. Initialization triggered later by a root bytecode
instruction remains catchable at that active-use instruction.

### Abrupt transition rules

1. Search handlers in helpers and in the actual `<clinit>` frame first. If caught,
   initialization continues; no wrapping or failed state occurs merely because an
   initializer is active.
2. If an exception leaves a helper, use the helper frame's `callPC` when searching
   `<clinit>`. Thus a handler around that invocation can catch it.
3. Only when the actual `<clinit>` frame has no matching handler and exits abruptly
   does its owning continuation apply JVMS 5.5 step 10:
   - if the thrown dynamic class is `java/lang/Error` or a subtype, retain the same
     reference and kind;
   - otherwise allocate one canonical EIIE kind-3 reference, optionally record the
     original reference as its internal cause, and propagate the wrapper;
   - if EIIE allocation hits the exception-arena cap, propagate the reserved OOM
     kind-7 reference instead.
   Then mark that actual initializer's class state 3 and retain its failed reference
   in internal metadata if useful for later cause support.
4. If a superclass or required default-interface initialization completes abruptly,
   every dependent class whose initialization continuation is being abandoned is
   marked state 3 and the **same** pending Error reference is propagated. Do not wrap
   again at dependent classes. This covers an arbitrary chain, not only one parent.
5. If class A's `<clinit>` actively uses failing B, the B continuation first marks B
   failed, then delivers the exception at A's active-use opcode. A handler in A's
   `<clinit>` may catch it and let A initialize successfully. Without such a handler,
   A's own `<clinit>` exits; because EIIE/NCDFE/OOM/SOE are Errors, A is marked failed
   and that same reference escapes.
6. Any later `new`, `getstatic`, `putstatic`, or `invokestatic` whose actual active
   owner is state 3 raises fresh canonical NCDFE kind 12 at that instruction's
   `opPC`. It is catchable. Resolution/access/shape checks retain their existing
   precedence before this state check.
7. An EVM validation failure or EVM OOG aborts the invocation and cannot be caught;
   no observable retry state exists after that revert.

Kinds 2, 3, 7, 10, 11, and 12 are Errors according to the canonical graph. Use graph
assignability rather than a duplicated hardcoded “unwrapped kinds” list.

## 10. `athrow` and external uncaught ABI

Admit `0xbf` as a one-byte opcode in predecode.

Runtime operand contract:

- Empty stack: existing `BytecodeError(3,opPC)`.
- Non-reference or `KIND_UNINIT`: existing `BytecodeError(14,opPC)`.
- Invalid nonzero registry handle: existing `ReferenceError(1,opPC)`.
- Null initialized ref: raise a fresh NPE kind 6 at the `athrow` PC (or emergency
  OOM if the exception arena is exhausted).
- Nonnull ref with `exceptionKinds[handle] == 0`: `BytecodeError(14,opPC)` in this
  bounded stage. Do not infer/construct a Throwable from host/JRE state.
- Registry-known captured VM Throwable: set pending from that handle's existing
  kind and the `athrow` PC; do not allocate or clone it.

On a local match, the same reference is restored as the handler's sole stack item.
On no match it unwinds normally. This supports compiler-emitted catch/rethrow and
catch-all paths without claiming `throw new MyException()`.

Preserve the exact external `JavaException(uint256)` selector and 36-byte payload.
When pending reaches the top without a handler, revert only with its canonical kind:

```text
1 ArithmeticException            7 OutOfMemoryError
2 StackOverflowError              8 ClassCastException
3 ExceptionInInitializerError     9 ArrayStoreException
4 NegativeArraySizeException     10 IncompatibleClassChangeError
5 ArrayIndexOutOfBoundsException 11 AbstractMethodError
6 NullPointerException           12 NoClassDefFoundError (new)
```

No handle, message, or cause crosses the ABI. Host Go/CLI code adds only exact kind-12
decoding to `java.lang.NoClassDefFoundError`; malformed/unknown payloads remain EVM
failures. Existing kinds 1..11 and schema 1 remain byte-for-byte compatible.

## 11. Constructor/uninitialized-reference safety

A captured VM Throwable is always initialized `KIND_REF`, never `KIND_UNINIT`.
Existing constructor rules remain: caller aliases become initialized only after a
normal constructor return.

On abrupt exit of a child `<init>` invocation, before searching a handler in its
immediate caller, invalidate every caller-local alias of that child's uninitialized
`thisHandle` (and any retained stack alias defensively). A selected handler clears the
operand stack anyway. Do not call `_initializeAliases`, do not set
`isConstructorLinked`, and do not permit poisoned aliases to be reloaded/transported,
stored, returned, or used for another constructor call. A dedicated poison kind or
`initialized[local] = false` is acceptable if all aliases are covered deterministically.

This rule applies when a superclass/this constructor fails and its caller constructor
catches the exception. It does not poison uninitialized `this` merely because an
ordinary helper called before `super` throws and is caught within the same constructor.
A constructor that has not linked this/super still cannot return normally. These are
runtime safety checks around the supported constructor lifecycle, not a claim to
implement JVMS 4.10.1.9's complete uninitialized-value dataflow verifier.

## 12. Function-level migration map

Names may be factored, but ownership and responsibilities should remain recognizable:

| Current area/function | Required migration |
|---|---|
| `Selected`, `Frame` | add ordered handlers/cache; tag Java vs init continuation; retain call/request PCs and init phase |
| `interpret`, `interpretClasses` | append canonical bootstraps, reject 19 reserved user names, assert max-88/<256 graph |
| `_parseBundleClass` / method metadata | retain Code locations as now; preserve enough class/method identity for HandlerError |
| `_readCode`, `_readCallCode` | parse bounded exception entries and nested attributes; stop blanket rejection |
| `_loadRoot`, `_loadCallee`, `_loadInitializer`, special/virtual loaders | carry class/method identity and handler arrays; preserve existing descriptor/access errors |
| `_predecode`, `_instructionWidth` | admit `athrow`; retain start map; validate table boundaries and handler max stack |
| `_execute` | own pending state, process it before fetch, dispatch `athrow`, and make every Java-producing branch return to unwind |
| `_newFrame` and all six child-push/cap sites | preserve exact `callPC`; SOE becomes pending in current frame without child allocation |
| `_initializeClass` and init-continuation dispatch | four states, capacity-before-state, root-before-frame, dependency failure propagation, one boundary wrap |
| `_throwJava`, `_hasActiveInitializer` | remove; replace with allocation/raise and boundary-specific init logic |
| `_findInterfaceMethod`, `_selectInterfaceImplementation`, `_selectVirtual`, `_resolveInterfaceSpecial` | return Java kind 10/11 status plus normal result; retain uncatchable validation errors |
| heap initialization and each allocation site | centralize registry setup, reserve emergency OOM, enforce 2,305 max, keep ordinary counters unchanged |
| `_validatePackedRef`, `_requireHeapKind`, `_typeAssignable` paths | accept real canonical exception objects through existing object semantics; never accept fake handles |
| `_initializeAliases` / abrupt constructor unwind | normal-return-only initialization plus failed-ctor alias poisoning |
| Solidity `_bootstrap*` and `runtime/build.js` | embed/rebuild/check all 19 reproducible raw images and exact graph |
| `jvmevm.decodeJavaException` | add exact kind 12 only; no host matching/evaluation |

Avoid turning `_execute` parameters into more parallel arrays if a bounded `VMState`,
`HeapState`, `InitState`, and `PendingException` memory-struct decomposition reduces
Solidity stack pressure. This is an implementation tactic, not permission to move
execution semantics to Go or an EVM precompile.

## 13. Proposed implementation write sets after parent freeze

Only the parent may freeze/assign these. A safe disjoint plan is:

### Runtime worker (sole Solidity writer)

- `jvmevm/runtime/JVMSubsetInterpreter.sol`
- `jvmevm/runtime/JVMSubsetInterpreter.runtime.hex`
- `jvmevm/runtime/build.js`
- new 19 `jvmevm/runtime/bootstrap/*.java` and matching `*.class.hex`
- `jvmevm/jvmevm.go` only for kind-12 decode
- `jvmevm/jvmevm_test.go` only expected runtime hash/bootstrap-artifact assertions
- new `jvmevm/exceptions_test.go` with `runtimeM5da*` helpers
- narrowly identified obsolete handler/athrow rejection assertions in old runtime-owned
  tests; report each replacement rather than blanket weakening

### Fixture/oracle worker

- `jvmevm/testdata/differential/**` only, adding cumulative `m5da` trusted Java 8
  sources/manifest cases and extending OracleMain only as necessary to report actual
  known root-initialization Throwables
- no host-generated expected classes and no host exception evaluation on production path

### Verifier worker

- `tools/java_diff.py`, `tools/test_java_diff.py`, `tools/JAVA_DIFF.md`
- new `jvmevm/exceptions_validation_test.go` with `verifyM5da*` helpers
- only exact obsolete handler/athrow negative assertions owned by that worker

### Parent-owned

Plans/program/AGENTS/quickstart/Makefile/integration, final hash/profile updates,
combined regression, and independently authored raw-cell/classfile probes. No worker
pushes, changes global configuration, spawns peers, edits consensus core, or adds host
Java fallback.

## 14. Test and acceptance contract

Preserve all 2,091 M5c-d differential cases, all prior focused tests, four native
raw-bit bindings only, five existing bootstraps, and every existing limit unless this
proposal explicitly adds a bound.

### Trusted JVM/EVM fixtures

Cover at minimum:

- each existing kind 1..11 caught locally by exact class, a superclass at each useful
  branch (`RuntimeException`, `Exception`, `Throwable`, `VirtualMachineError`,
  `LinkageError`, `Error`), and catch-all; uncaught behavior remains exact;
- ordered overlapping handlers where the first match wins; inclusive start and
  exclusive end; handler target at an instruction boundary; handler stack contains
  one reference and no stale prefix while locals survive;
- every call mode with a fault in the callee and a handler covering precisely the
  caller invoke PC, plus multi-frame propagation and rethrow identity;
- `athrow` of a caught known ref, nested catch/rethrow, null-to-NPE, and unsupported
  ordinary/uninitialized refs;
- captured exception identity and compatibility through local/static/instance fields,
  Object/Throwable/reference arrays, calls/returns, casts, `instanceof`, and `if_acmp*`;
- caught SOE at the 128-frame call boundary without a new frame;
- caught logical OOM after each ordinary object/array/count/slot/element limit, proving
  both the catch and unchanged ordinary accounting;
- 256 fresh exception identities, arena exhaustion changing the next raise to the
  reserved OOM, catch/rethrow of that emergency ref, and per-invocation reset;
- a fault caught inside `<clinit>` (including from a helper) allowing successful init;
  an escaping non-Error wrapped exactly once; escaping Error unchanged;
- failed own initializer, failed superclass, failed required default interface,
  dependency chains, reentrant initialization, and later active uses producing
  catchable NCDFE for every class that became erroneous;
- a failing class used inside another `<clinit>` both caught there (outer succeeds)
  and uncaught there (outer becomes erroneous);
- root class/super/default-interface failure not catchable by the never-entered root
  method, while a later active-use failure from inside root is catchable;
- initialization scheduling at frame cap with no state-1 residue, and constructor/
  super-constructor failure handlers with no uninitialized-reference escape.

### Independent malformed/raw-class probes

Patch trusted emitted classfiles to isolate:

- all HandlerError codes, table count cap, truncated entries/attributes, CP tag/name,
  start/end/handler boundaries, end==code_length, overlap and table order;
- lazy catch policy: missing catch class outside an applicable range is untouched;
  the first range-applicable unresolved entry fails rather than being skipped;
- `max_stack == 0` with a handler, `athrow` width/truncation, stack underflow and kind;
- all former direct JavaException(2/10/11) paths now catch, and nearby malformed
  Call/Interface/Hierarchy paths remain uncatchable EVM errors;
- emergency OOM is a nonzero registered handle, cannot be forged from root ints, and
  registry writes never exceed 2,305;
- low gas yields EVM OOG rather than caught Java OOM.

Use finite measured gas/timeouts. Quota probes may retain the existing Go-only 250M
ceiling only where measured necessary; do not raise fixture budgets casually or force
host-JVM OOM. Differential JVM outcomes must come from independently running trusted
classfiles, not from mirroring EVM kind tables in the oracle.

Acceptance should run runtime reproducibility/bootstrap checks, focused Go tests,
CLI/Python tests, all 2,091 prior differential cases plus M5d-a additions, smoke/full
profiles, demos, AOT regression, and `go vet` as applicable. Report runtime size/hash,
bootstrap count/hashes, max gas, exact new case/probe totals, and retained limitations.

## 15. Risks and explicit trade-offs

1. **Initialization is the highest semantic risk.** Eager “initializer active” wrapping
   is easy but wrong. Tagged continuations and boundary-specific wrapping are required;
   dependency and active-use-in-`<clinit>` tests should land before optimization.
2. **Solidity stack/code growth.** Nineteen raw images, handler parsing, and unwind add
   size to an already 135,652-byte local runtime. State structs/shared helpers reduce
   duplication, but no EIP-170 claim is possible. Measure gas and artifact reproducibility.
3. **Linear scans.** Handler lookup is ordered and therefore linear by semantics;
   subtype checks can also traverse a bounded class graph. The 1,024 handler and
   88-class bounds make this finite. Do not reorder handlers for optimization.
4. **Arena-cap deviation.** With no GC, a 256-object exception arena eventually raises
   emergency OOM sooner than a normal JVM might. This is preferable to conflating
   ordinary object quota, forging a reference, or becoming raw OOG; document and test it.
5. **Lazy catch resolution timing.** It avoids penalizing irrelevant ranges but is not
   eager JVM verification. The exact first-applicable-entry failure policy above must
   be frozen so fixtures cannot depend on accidental scan behavior.
6. **Reserved names.** Rejecting user definitions of 19 `java/lang` classes is a small
   compatibility change but prevents forged canonical hierarchy/identity. Existing
   replaceable Object/marker/raw-FP behavior remains unchanged.
7. **Constructor poisoning is partial verification.** It closes the unsafe escape
   introduced by new catch edges without claiming full stack-map/dataflow verification.
8. **EVM OOG remains outside Java semantics.** Even emergency objects cannot guarantee a
   catch if the outer execution has insufficient gas. Tests need headroom and a separate
   low-gas negative.
9. **No giant Throwable API slice.** Guest code can inspect type/identity and transport a
   caught exception, but calls such as `getMessage`, `getCause`, `printStackTrace`, or
   fresh `new ArithmeticException` remain explicit unsupported failures.

## 16. Preflight evidence

Local inspection commands on c6b6584 established the path inventory above:

```sh
git rev-parse --show-toplevel
git status --short --branch
grep -n 'revert JavaException\|_throwJava' jvmevm/runtime/JVMSubsetInterpreter.sol
grep -n 'depth == MAX_FRAMES\|_initializeClass(' jvmevm/runtime/JVMSubsetInterpreter.sol
sha256sum jvmevm/runtime/JVMSubsetInterpreter.runtime.hex
```

The hex file's text hash is not the runtime hash; decoding it produced exactly 135,652
bytes and the accepted SHA-256 shown in section 2.

All five cited JVMS 8 links and all 19 linked Java 8 API class pages returned success
during preflight. Local `javap` (JDK 21.0.9, hierarchy stable with the Java 8 API
pages) confirmed every direct superclass in section 4. A separate `/tmp` bootstrap
prototype compiled the 19 minimal sources together with Object and Serializable using
`javac --release 8 -g:none -Xlint:-options`; it emitted all 19 classfiles (2,910 raw
bytes total), supporting the proposed reproducible raw-image strategy. Exact per-file
bytes and hashes remain for the implementation freeze/build change, not this proposal.

A bounded temporary Java semantic probe compiled with `javac --release 8` and ran
outside the repository. Its observed values were:

```text
ordered/local catch=11, cross-call catch=21, rethrow identity=31,
null athrow catch=41, caught StackOverflowError=51
caught initializer=61
first/later failed class=ExceptionInInitializerError/NoClassDefFoundError
failed superclass dependent and prerequisite later=EIIE/NCDFE/NCDFE
failed default-interface dependent and interface later=EIIE/NCDFE/NCDFE
root method with its own catch around its body: initialization failed before entry
```

`javap -c -v` showed ordered handlers `[0,6) -> 7 ArithmeticException`, then
`[0,6) -> 11 RuntimeException`; a callee fault was caught by a caller range `[0,3)`
covering its `invokestatic` at PC 0. Temporary probe files remained under `/tmp` and
were not added to this repository.
