# M5d-a oracle/semantics preflight proposal

Status: **proposal only; the implementation contract is not frozen**. Baseline is
`c6b6584` (accepted M5c-d). Nothing in this document claims that the current EVM
runtime executes handlers or `athrow`.

## 1. Baseline finding

The current runtime has exactly the expected preflight gap:

- root `Code.exception_table_length != 0` is rejected as `MethodError(8)` at
  `jvmevm/runtime/JVMSubsetInterpreter.sol:4045-4046`; entered callees and
  initializers reject the same shape through `_readCallCode` at lines4073-4074;
- implicit Java faults call `_throwJava`, which immediately reverts
  `JavaException(kind)` and eagerly wraps any non-`Error` while *any* initializer
  is active (lines4807-4814), before an initializer-local handler can run;
- frame-cap SOE and dispatch ICCE/AME also use direct `JavaException` reverts;
  `athrow`0xbf is not dispatched.

Thus all existing JavaException sites must feed one in-EVM pending-exception and
handler/unwind path. `ClassError`, `MethodError`, `BytecodeError`, `CallError`,
`LinkError`, `FieldError`, `InitError`, `HierarchyError`, `ArrayError`,
`ReferenceError`, `ObjectError`, `TypeError`, `InterfaceError`, and EVM OOG remain
hard runtime/validation failures. They must not become catchable merely because a
Java class name resembles an exception.

Baseline artifact:135652 decoded bytes, SHA-256
`cf68495083ebcd2df93f6d676e16afad87192a3401bd743a0301d805d5a8cd15`;
Solidity source SHA-256
`120c55df483458ee9daa4445390eb59a2c2d7f4ac4060433e37c28caab75feb2`.

## 2. Normative Java 8 anchors

Use these direct JVMS SE8 rules, not host implementation accidents:

- JVMS §2.10, Exceptions:
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-2.html#jvms-2.10>
- JVMS §2.6.5, abrupt method completion and caller frame restoration:
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-2.html#jvms-2.6.5>
- JVMS §4.7.3, `Code` and exception-table structure:
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.3>
- JVMS §4.10.1.9, type checking instructions and uninitialized instances:
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.10.1.9>
- JVMS §5.4, permitted eager/lazy resolution and when resolution errors are
  observed:
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html#jvms-5.4>
- JVMS §5.5, class/interface initialization, erroneous state and wrapping:
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html#jvms-5.5>
- JVMS §6.5 `athrow`:
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html#jvms-6.5.athrow>
- Relevant implicit-fault instruction definitions: `idiv`, `ldiv`, array loads
  and stores, `arraylength`, `newarray`/`anewarray`/`multianewarray`, `checkcast`,
  and invoke instructions in
  <https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html>.

The key executable rules are: inspect table entries in classfile order; match when
`start_pc <= throw_pc < end_pc`; on a match clear the operand stack, push exactly
the thrown reference, preserve locals, and jump to `handler_pc`. If the current
method has no match, discard its frame and repeat in the invoker. A callee's abrupt
completion is observed at the caller's **invoke opcode PC**, not the already
advanced next PC.

## 3. Bounded oracle evidence

All sources were trusted local probes compiled by OpenJDK8 `javac 1.8.0_504`
with `-source 8 -target 8 -g`; every emitted class is major52. Runs used `timeout
20s`, `-Xmx64m`, `-Xss512k`, `-XX:-OmitStackTraceInFastThrow`, and either normal
verification or `-Xverify:all`. No host OOM or SOE was attempted. Probe `main`
methods use printing/reflection/string APIs only to label host-oracle results;
those launchers are not proposed EVM fixtures, and section7 calls for isolated
int-root guest methods.

JVMs:

- OpenJDK8 `1.8.0_504-b01`, VM build25.504-b01;
- Java21 `21.0.9+7-LTS-338`.

Local ignored evidence:

- source archive `build/java-diff-m5da-oracle-preflight/m5da-oracle-sources.tar.gz`,
  SHA-256 `b1ebda62c51c10794153d0785e8432ce8f5d4b70fe065ac053539a841b4e149d`;
- 22-file `source-sha256.txt`, manifest SHA-256
  `5dba69a29cdcd1a8a1408ef15ba64eb676f6f59808126df35f8b8d97f3bc679f`;
- complete classes/logs/javap evidence archive
  `build/java-diff-m5da-oracle-preflight/m5da-oracle-evidence.tar.gz`, SHA-256
  `7ecf6e00d5b70b4c481dfeed402286b1fef27e284b47d4ee681fdd358a8a634a`;
- consolidated stdout `outcomes.txt`, SHA-256
  `a4136536882993229af6b00319a2fa6f939fdd9d5b93af3d6d9cf431f0c19f4d`;
  Java8 `javap -c -v -p` listings are under the archive's `logs/`.

### 3.1 Handler/throw matrix

| Probe | Java8 | Java21 | Bytecode corroboration / contract consequence |
|---|---:|---:|---|
| catch Arithmetic/NPE/AIOOBE/ASE/CCE/NASE | six named catches | same | Each valid implicit fault entered its typed handler. |
| ordered subtype, then RuntimeException, then Throwable | `11,22` | same | `ordered` has overlapping entries in that exact table order. First matching entry wins. |
| source multi-catch Arithmetic\|NPE | `41,42` | same | Two adjacent entries share handler15; no set/sort normalization. |
| AIOOBE caught as IndexOutOfBoundsException | `51` | same | Matching uses subtype ancestry, not exact kind equality. |
| callee throws through invoke-only try | `61` | same | `invokeOnlyRange`: invoke at0, next PC3, protected range `[0,3)`. Searching with next PC would incorrectly miss it. |
| stack prefix discarded; I/J/F/D locals retained | `149` | same | Handler stack map has only ArithmeticException; locals are `int,long,float,double`. The pre-invoke int prefix does not survive. |
| caught ref rethrown by `athrow` | `71` identity equal | same | `athrowIdentity` catches the exact same reference at `[10,12)`. |
| rethrow through another frame | `72` identity equal | same | Caller catches at invoke PC and receives the original reference. |
| `athrow null` | `73` NPE caught | same | `throwNull` has `athrow` at3 and NPE handler range `[2,4)`. |
| first two same-BCI implicit arithmetic faults | `74` distinct | same | Only two throws, FastThrow disabled; evidence rejects a global leaf-type singleton as the normal path, but makes no claim after resource exhaustion. |
| Java8 `finally` | `75` | same | javap emits catch_type0 (`any`) range `[4,11)`, cleanup, then `athrow`; no `jsr`/`ret`. |
| explicit catch(Throwable)+instanceof | `76` | same | Minimal hierarchy and `instanceof` suffice; Throwable APIs are not involved. |
| rethrow from inner handler | `77` | same | Inner `[0,6)` excludes handler7; outer `[7,10)` catches `athrow` at9. This demonstrates start-inclusive/end-exclusive behavior. |
| binary-evolution ICCE caught before escape | `111` | `111` | `catch(IncompatibleClassChangeError)` precedes `catch(Error)`. |
| binary-evolution AME caught before escape | `121` | `121` | `catch(AbstractMethodError)` precedes `catch(Error)`; AME is an ICCE subtype. |

The simple source outcomes were identical on Java8 and21. The probes establish
semantics; they do **not** establish present EVM support.

### 3.2 Initialization matrix

| Probe | Java8 | Java21 | Required behavior |
|---|---|---|---|
| arithmetic caught inside `<clinit>` | `inside=81` | same | Search the initializer's own handlers first; successful catch prevents EIIE and class failure. |
| non-Error escapes own initializer, then reused | `EIIE / NCDFE` | same | First escape wraps; later active use sees erroneous state and throws NCDFE. |
| failing superclass prerequisite, then subclass reused | `EIIE / NCDFE` | same | The dependent subclass is erroneous too, not left initializing or retried. |
| failing default-method interface prerequisite, then implementing class reused | `EIIE / NCDFE` | same | The dependent ordinary class is erroneous too. |
| reentrant active use while class initializes | `before=0,later=9` | same | Same-thread reentry succeeds and sees prepared default fields, without restart. |
| selected root class initialization fails before root method | outer EIIE, then outer NCDFE | same | The root method's own EIIE/Throwable handlers never run because its invocation has not begun. |
| ICCE escapes `<clinit>`, then class reused | ICCE / NCDFE | AME / NCDFE in this evolved sequence | Both first outcomes are `Error` and remain unwrapped; second use is NCDFE. Do not infer a cross-version exact linkage-error precedence from this multiply-evolved graph. |
| AME escapes `<clinit>`, then class reused | AME / NCDFE | same | `Error` is unwrapped and failed-class state persists. |

The Java21 ICCE-sequence variation is useful caution, not a target change: Java8
is the stated compatibility oracle, and binary-evolution graphs can expose
resolution/selection differences. Freeze isolated Java8 expected outcomes and do
not encode accidental Java21 error ordering.

### 3.3 Missing catch type / verifier timing

A fresh major52 `LazyCatch` was compiled with a valid
`catch(missing.MissingProblem)`, then only `MissingProblem.class` was removed.
On both JVM8 and21, with both default verification and `-Xverify:all`:

- `Class.forName(name, false, loader)` succeeded;
- initialization (`Class.forName(..., true, ...)`) failed with NCDFE caused by
  ClassNotFoundException;
- invoking either a no-throw body or an arithmetic body failed the same way before
  returning from the body.

This does not prove one universal lazy-resolution point. JVMS §5.4 permits
implementation choice while constraining observable error timing, and HotSpot
verification may inspect more than the selected path. The EVM subset must keep
three concepts separate:

1. malformed/truncated exception-table or wrong CP tag: deterministic EVM
   validation failure;
2. structurally valid but unsupported/user-defined catch type: explicit supported-
   profile validation failure in M5d-a;
3. Java NCDFE kind12: only subsequent active use of a class/interface already
   marked erroneous by initialization in this slice.

Do not relabel (1) or (2) as a Java catchable error, and do not claim whole-class
JVMS verifier conformance. Continue the existing selected/entered-method Code
validation model; an invalid unused method may remain unseen by this subset.

## 4. Recommended frozen M5d-a vertical slice

### 4.1 Supported thrown types and external kinds

Retain external JavaException kinds1..11 and add exactly:

- **kind12 = `java.lang.NoClassDefFoundError`**, only for active use after failed
  initialization in this stage.

Internally, a pending exception is a typed, non-null reference, not just a kind.
`JavaException(kind)` remains only the exact uncaught-root ABI outcome. Preserve
exact selector+one canonical uint256 decoding and rejection of unknown,
noncanonical, short, or trailing payloads.

Use this closed synthetic ancestry (names are JVM internal names):

```text
java/lang/Object
  java/lang/Throwable
    java/lang/Exception
      java/lang/RuntimeException
        java/lang/ArithmeticException
        java/lang/NullPointerException
        java/lang/IndexOutOfBoundsException
          java/lang/ArrayIndexOutOfBoundsException
        java/lang/NegativeArraySizeException
        java/lang/ClassCastException
        java/lang/ArrayStoreException
    java/lang/Error
      java/lang/VirtualMachineError
        java/lang/StackOverflowError
        java/lang/OutOfMemoryError
      java/lang/LinkageError
        java/lang/ExceptionInInitializerError
        java/lang/NoClassDefFoundError
        java/lang/IncompatibleClassChangeError
          java/lang/AbstractMethodError
```

This table is enough for typed catches, catch-all, rethrow, reference identity,
`checkcast`, and `instanceof`. It does not need classfiles, fields, constructors,
messages, causes, stack traces, `getClass`, `toString`, reflection, or any new
native binding. Fresh user `Throwable` subclasses/construction and Throwable APIs
remain M5d-b+. Do not accept a supplied fake `java/lang/Throwable` class as a way
to override the synthetic hierarchy.

### 4.2 Throwable identities and bounded arena

Recommended exact resource contract for freezing:

- reserve a per-invocation `MAX_THROWABLES=1024` arena, disjoint from the existing
  1024-object and array quotas but in the same unforgeable reference namespace;
- each ordinary implicit fault, SOE, logical OOME, ICCE, AME, EIIE wrapper, NCDFE,
  and `athrow null` allocates a fresh record while arena capacity remains;
- reserve one emergency OOME reference outside that count. If allocating any
  throwable record/wrapper fails at the logical arena boundary, replace the
  pending exception with that OOME. Repeated emergency use may expose the same
  identity; no freshness guarantee applies after exhaustion;
- records contain only synthetic class identity for now. They are immutable and
  survive locals/stack comparisons and rethrow. A new VM invocation resets them.

This prevents object/array logical OOM and frame-cap SOE from depending on host
allocation success and prevents a global singleton from breaking ordinary
identity. The exact cap should be changed before freeze only if measured EVM gas
requires it; never infer a cap by exhausting a host JVM.

### 4.3 Handler parsing and validation

Add a bounded per-selected-method table (recommended
`MAX_EXCEPTION_HANDLERS=256`). In classfile order, retain
`start_pc,end_pc,handler_pc,catch_type` and validate:

- complete 8-byte entries and count within cap;
- `start_pc < end_pc <= code_length`;
- start and handler are decoded instruction starts; end is an instruction start or
  exactly `code_length`;
- `handler_pc < code_length`;
- catch_type0 means catch-all; otherwise it is a valid CONSTANT_Class -> Utf8 name
  in the closed Throwable table and is Throwable-compatible;
- a reachable handler needs at least one stack word (`max_stack >= 1`).

Suggested hard error is `HandlerError(code, location)`:

1. truncated/count/cap; 2. bad range or non-boundary PC; 3. bad CP/tag/name;
4. unsupported/non-Throwable catch class; 5. unsupported pre-super constructor
handler. These are supported-profile validation failures, never catchable Java
objects. Root's current MethodError8 and callee CallError4 rejection become
obsolete only for valid tables.

### 4.4 One pending/unwind algorithm

Represent pending state at minimum as `(throwableRef, throwPC, targetDepth)` and
route every existing Java kind site plus `athrow` through it. A central loop must:

1. search the current executing frame's entries in declaration order using
   `start <= throwPC && throwPC < end` and synthetic subtype matching;
2. on match, set `sp=0`, push exactly the same throwable reference, retain every
   local and initialization bit (including I/F/D/J category layout), set
   `pc=handler_pc`, and clear pending;
3. with no match, perform abrupt-frame cleanup, pop that frame, and continue;
4. when crossing into a caller, use the popped child's recorded **callPC**, the
   invoke opcode PC. Never use caller `f.pc`, which already points after invoke;
5. when an active-use initialization continuation is involved, preserve its
   triggering opcode PC for eventual search in the requesting frame;
6. only if no Java frame remains, map the synthetic leaf class to exact
   `JavaException(kind)` ABI data.

Fault generation must be side-effect precise. Operands are evaluated normally,
but the faulting instruction performs no post-fault store/allocation/PC action.
Malformed operand kinds, wrong runtime heap domain, forged refs, bad descriptors,
and unsupported opcodes remain existing hard validation errors rather than
catchable exceptions.

For frame-cap SOE, the attempted invoke itself is the faulting instruction and no
child frame is pushed. Its caller can therefore catch SOE at that invoke PC. For
logical allocation OOME, no failed allocation/quota increment occurs before the
handler runs. EVM OOG remains an uncatchable execution abort.

### 4.5 `athrow`

Add opcode0xbf width1. It consumes one supported Throwable reference:

- non-null: pending uses that exact reference; rethrow preserves `==` identity;
- null: create a fresh NPE (or emergency OOME if throwable allocation itself is
  exhausted), with throw PC equal to the `athrow` PC;
- non-reference, uninitialized token, forged handle, or ordinary non-Throwable
  reference is a hard bytecode/reference validation failure in this subset.

M5d-a need only create Throwable references from implicit faults and wrappers.
No `new ArithmeticException`, constructors, message/cause APIs, or arbitrary user
`Throwable` objects are required.

## 5. Initialization/unwind contract

Initialization needs states `uninitialized`, `initializing`, `initialized`, and
`erroneous`, plus enough continuation metadata to identify the dependent class
and triggering active-use PC.

1. Search handlers inside `<clinit>` and helpers normally. A caught fault resumes
   initialization; do not wrap it and do not mark any class erroneous.
2. Only when a pending exception escapes the initializing class's `<clinit>`:
   mark that class erroneous. If its synthetic type is not an `Error`, replace it
   with a fresh EIIE wrapper; if it is an `Error`, preserve the exact reference.
3. If superclass or required default-interface initialization fails, mark every
   dependent ordinary class whose initialization cannot complete erroneous while
   unwinding its continuation. Do not rerun any initializer.
4. A later active use of an erroneous class/interface creates pending NCDFE kind12.
   This NCDFE is an Error and is catchable as NCDFE, LinkageError, Error,
   Throwable, or catch_type0.
5. Same-thread reentrant requests for an `initializing` class succeed immediately
   and expose prepared defaults/current writes.
6. Root initialization occurs before the selected root method invocation. Keep
   the root frame dormant/non-searchable until initialization succeeds; a root
   initialization failure cannot be caught by a handler in that root method.
7. EIIE/NCDFE cause/message APIs are deferred, but wrapper/reference type and
   identity must still be real internal records.

An `Error` caught inside `<clinit>` also prevents class failure if the initializer
then completes normally. Conversely, merely having some unrelated initializer
active must never wrap an exception caught by its own frame; this is why the
current global `_hasActiveInitializer` shortcut cannot remain.

## 6. Constructors and `finally`

Required now:

- a constructor fault can unwind to a handler around `new C()`/`invokespecial` in
  its caller; the caller handler's cleared stack makes the uninitialized allocation
  inaccessible;
- handlers in a constructor after its successful this/super chaining call may run;
- normal constructor alias promotion remains only on normal constructor return;
  abrupt return must not initialize aliases.

Recommended explicit M5d-a limitation: reject with HandlerError5 an exception
range in `<init>` that protects execution while local0 is still uninitialized,
including the mandatory chaining `invokespecial`. JVMS verifier treatment of
uninitialized-this and handlers is stateful (§4.10.1.9), while this runtime does
not implement a full verifier. Do not silently enter such a handler with a normal
object reference. Broader valid hand-authored constructor-handler forms can be a
later verifier stage.

Java8 `finally` needs no `jsr`/`ret`: accept the ordinary javac8 pattern of a
catch_type0 handler, duplicated cleanup, and `athrow`. Keep `jsr`, `jsr_w`, and
`ret` unsupported.

## 7. Required fixture and independent-test matrix after freeze

### JVM/EVM trusted Java8 fixtures

Use small `(int...)int` methods, separate classes where initialization freshness is
needed, and actual Java8 oracle outcomes. Include:

- each implicit leaf: int and long divide/remainder zero; null array load/store/
  length, null field and invoke; negative/positive bounds; NASE for all existing
  allocation forms; CCE; ASE; binary-evolution ICCE and AME;
- exact/subtype/supertype/Error/Throwable/catch_type0, overlapping ordered entries,
  javac multi-catch shared target, and nonmatching fallthrough;
- first instruction at `start_pc`, instruction at `end_pc` not caught, nested and
  overlapping tables, handler throwing/rethrowing, and catch inside a handler;
- invoke-only `[invokePC,nextPC)` cross-frame cases for static/special/virtual/
  interface calls and initializer-triggering active uses;
- nonempty caller operand prefix cleared; locals I/F/D/J and initialized-null refs
  preserved; handler receives exactly one ref; same-ref compare/rethrow and null
  `athrow` -> NPE;
- two bounded same-BCI implicit faults compare distinct with FastThrow disabled;
  do not loop until host/JIT exception reuse;
- caught arithmetic inside `<clinit>`, helper fault caught by `<clinit>`, caught
  Error inside `<clinit>`, escaping non-Error -> EIIE, Error unwrapped, later
  NCDFE, failed super/default interface -> dependent NCDFE, reentrant defaults,
  and root failure outside root handler;
- caller catches constructor failure; post-super constructor-local catch; javac8
  finally/catchall/rethrow without `jsr`/`ret`.

Do not add direct host-OOM or host-SOE oracle cases. Existing logical array/object
OOM and the interpreter's frame cap are deterministic EVM semantics and can be
caught in EVM tests; ICCE/AME provide bounded real-JVM `Error` oracle paths.

### Exact independent Go negatives/resources

Use fresh trusted classfiles and one controlled mutation per case:

- HandlerError1: count257, truncated 8-byte entry;
- HandlerError2: start==end, end>code_length, start/handler in middle of an invoke,
  handler==code_length, end neither boundary nor code_length;
- HandlerError3: catch index0 is separately valid catch-all; otherwise index OOB,
  Utf8 instead of Class, Class name index bad, malformed internal name;
- HandlerError4: `java/lang/Object`, a supplied ordinary class, unknown/missing
  class, or unsupported user Throwable subclass as catch type;
- HandlerError5: protected pre-super constructor chaining call;
- athrow wrong int/uninitialized/ordinary-object/forged ref; stack underflow;
- handler `max_stack=0`; branch/handler interactions and duplicate ordered entries;
- prove Bytecode/Call/Link/etc. validation reverts and gas OOG bypass all handlers;
- prove Java kinds1..12 are catchable at exact/super/catchall levels, while an
  uncaught leaf preserves its existing external kind; exact kind12 decode, unknown
  kind13 and noncanonical/trailing ABI rejection;
- at throwable records1,2,1024: ordinary identities differ; record1025 yields the
  reserved catchable OOME without host pressure; EIIE/NCDFE wrapper allocation at
  the boundary also yields OOME; fresh invocation resets the arena;
- object/array quota OOME and frame128 SOE are catchable; failed allocation/call has
  no side effect; low-gas execution remains EVM OOG, never Java OOME/SOE.

Keep simple handler probes at the existing focused ceiling `<=20M` gas where
measured. Allow `<=80M` for bounded cross-frame/initialization cases and the
already established `<=250M` ceiling only for Go-only quota/arena boundaries.
Any case exceeding those ceilings is a freeze/review issue, not permission to
raise budgets or weaken outcomes.

### Gates

Preserve all2091 M5c-d cases,192 raw-cell probes, four raw-bit bindings, exact root
ABI and all current malformed-input outcomes not explicitly superseded. Rebuild
and review the pinned artifact only after runtime implementation. Run focused Go,
CLI/decoder,36 Python, full Java differential, smoke, demos, AOT, vet, and
bootstrap checks. This proposal itself intentionally runs no EVM conformance
claim.

## 8. Freeze issues for the parent

1. **Solidity control flow:** internal helper reverts cannot be caught by guest
   handlers. ICCE/AME resolution helpers and every `_throwJava`/frame-cap site must
   return/set pending state or be reorganized under a central dispatcher; do not
   decode/catch Solidity revert data inside the guest VM.
2. **Cap confirmation:** freeze the proposed 1024-record + emergency-OOME arena
   and 256 handlers/method only after artifact/gas measurement.
3. **Constructor limitation:** explicitly retain HandlerError5 rather than imply
   full Java8 verifier coverage.
4. **Catch types:** freeze the closed synthetic hierarchy only. User-defined
   Throwable subclasses, construction, fields/APIs and missing-catch-class Java
   timing remain later work.
5. **Java8 target:** use Java8 for exact binary-evolution outcomes; Java21 is a
   secondary differential signal, as the observed ICCE/AME initializer variation
   demonstrates.
6. **No overclaim:** M5d-a would be an implicit-exception-first catch/unwind slice,
   not complete exceptions, complete verification, Java SE conformance, arbitrary
   Java, or deployable-mainnet support.
