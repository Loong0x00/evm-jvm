# MC Java-I/O exception/message prerequisite preflight

Status: **documentation/oracle-only proposal; not frozen or accepted**. Prepared at
`125272172a9aae556e2d0800aaf744962907230b` while MC-SC0 is frozen but under parent
review. Any successor is conditional on SC0 acceptance and its final accepted hash;
the current SC0 worker artifact is not silently treated as a base.

No production/runtime/peer/core/accepted file was changed. No Minecraft/JAR/server
code ran, no EULA file or acceptance was created, and no socket/listener was opened.
Only 30 trusted self-authored oracle cases ran on local Java 8/21. This proposes one
bounded prerequisite, **MC-IOE0**, not a VFS or all-platform stage.
## Recommendation and exact boundary

After SC0 acceptance, fork its accepted LOCAL continuation into a new versioned
runtime and add only constructor-backed message/cause state needed before a Java
`File` bridge:

* `Throwable.<init>:()V`, `Throwable.<init>:(String)V`, `getMessage:()String`, and
  `getCause:()Throwable`;
* `Exception.<init>:()V` and `(String)V`;
* `ExceptionInInitializerError.<init>:()V` and `(Throwable)V`, plus exact
  `getException/getCause:()Throwable`;
* reserved `IOException`, `FileNotFoundException`, and `EOFException`, each with
  genuine Java Code for public `()V` and `(String)V`; and
* Java-8-pinned message state for VM-created exact ArithmeticException and NPE, and
  exact VM-created EIIE cause identity, without running a host constructor.

Do **not** add `Throwable(Throwable)`, `(String,Throwable)`, the protected four-arg
constructor, localized/toString/printing, stack trace, fill callback, suppression,
`initCause`, StringBuilder/range/formatting, File/streams, VFS, main, scheduler,
logging or Java-SE claims. Existing TL0 fillInStackTrace-override rejection remains:
this narrow bootstrap still does not pretend to capture stacks.

`initCause` is **not needed for VFS0**. Each proposed I/O error can be freshly made
with zero/message Code; no bridge operation needs post-construction chaining. EIIE
has its dedicated exact `exception` relation. Adding `initCause` now would require
canonical IllegalStateException and IllegalArgumentException identities, their
message/cause constructors and observable failure messages, plus a policy for its
Java-8 synchronized method. Returning success, null, or canned failures would lie.
Calls therefore remain an exact missing-method/link/profile failure. A later
version may add it atomically; it may not reinterpret IOE0 checkpoints.

## Bootstrap choice

Use reserved bootstraps, not host classes. Replace only the new-version copies of
`Throwable`, `Exception`, and EIIE; add the three `java/io` classes. Keep all other
accepted SC0 images byte-identical, including its final accepted String image.
The resulting candidate has 30 images (23 unchanged old images, one SC0 String,
three changed Throwable-family images, three new I/O images).

The I/O classes must be reserved because the later bridge selects exact bootstrap
identity, user replacement must fail, and supplying the three-class hierarchy as
input would consume three of SC0's four class slots. User I/O subclasses remain
ordinary bounded input classes. IllegalStateException/IllegalArgumentException are
neither inputs nor bootstraps in IOE0; if `initCause` is later frozen, both must be
reserved canonical images rather than host-selected or user-supplied lookalikes.

Throwable also has one exact private static metadata-carrier method containing the
AE `CONSTANT_String`; EVM validates its shape and reads its CP bytes but never invokes
it as a native service or exposes it as public API. Measured Java8 skeletons are not
final pins: Throwable 584B `cfcb1fce8c15a8083e4c4c764e1cd451f701a0d9e0f2d000e38d4f4b29d1021f`,
Exception 203B `25cb2ac6e090fc75f4ca3faa8b00586b6373a53d0ace3024fe36be272a19b34e`,
EIIE 389B `21fe8c2605bbb61c248207ed1e9c1a42b194aba9661e6b930b2c605cde962609`,
IOException 203B `61b742b86e9be1d4c3bc8c5d90156befc8ce38afc5d4425bd5751b77224d4d17`,
FNFE 213B `d964d55dc660566a64eda14af9dacbfa51a93baa8d5b772e73a083d2d258f654`,
EOF 204B `6cb3a2c8d9baa1403f9e5a11e7e46872bcc0da45099cbe315ec248f841a6fd0`. A
freeze must reproduce/review exact source, bytes, hashes and access flags; never
copy OpenJDK stack/suppression/StringBuilder dependencies or add another helper.

## State, origin and genuine Code

`Throwable` owns exactly `detailMessage:String` and `cause:Throwable` in this
profile. Its Java constructors call Object, set `cause=this` (the uninitialized-
cause sentinel), and the message constructor stores the exact caller String ref.
`getMessage` returns that field; `getCause` returns null iff the field is self.
Null and empty messages remain distinct, and no String copy/allocation occurs.
Exception and all three I/O constructors are ordinary forwarding Java bytecode.
Virtual overrides continue through normal EVM dispatch.

Explicit objects use ordinary object/field quotas and execute every constructor
frame. Their no-GC failed residues stay charged. Validation must admit checkpoints
between Object return, `cause=this`, message assignment and constructor return;
only normal return promotes UNINIT aliases. It must reject impossible usable
partially initialized state without globally rejecting legal TL0 REF/UNINIT aliases.

Every arena exception now has the two inherited fields. VM allocation, which still
does not execute constructor Code, must set `cause` to its own exact ref. Exact
Java-8 implicit integer divide/remainder ArithmeticException additionally receives
the guest String `/ by zero`; implicit NPE receives null. Thus explicit no-arg AE
has null message while implicit AE does not, and both causes read null. The fixed AE
text must come from an EVM-parsed pinned bootstrap `CONSTANT_String` and a genuine
SC0 String object/backing, never host text or an ABI/native canned response.

Each VM-created AE reserves its own non-interned message String and char backing:
the oracle found its message unequal to the interned literal and distinct across
two one-shot faults on both JDKs. Allow at most 256 such String/backing pairs, tied
one-to-one to arena AE records, in the single handle namespace but separate finite
VM-message counters so faults remain available after ordinary quota exhaustion.
Validate normal SC0 String structure; never expose backing or consume an intern
slot. Recompute the shared-handle ceiling and exact/plus-one behavior. Lazy ordinary
allocation that turns required AE into OOM is unacceptable. Other VM-created kinds
whose Java-8 messages are not pinned here must hard-fail `getMessage` with a new
`ThrowableAPIProfileError(kind,pc)`, rather than silently return null. Their existing
throw/catch behavior remains unchanged.

EIIE owns exactly `exception:Throwable`. Ordinary `(Throwable)` Code stores the
exact argument (including null); no-arg stores null. A VM-created EIIE stores the
exact prior non-Error pending ref in the same field. Both `getException` and the
EIIE override of `getCause` execute Java Code and return that field. Replace TL0's
wrapper-cause side table in the new schema: two authorities that can disagree are
forbidden. Explicit EIIE is never relabeled VM-origin; wrapper OOM creates emergency
OOM with no fictitious EIIE/cause. Message remains null. EIIE's inherited sentinel
is not exposed because of its override; `initCause` remains absent.

The emergency OOM also gets a self cause. Re-derive field offsets by exact owner/
name/descriptor, never constants. Reprove ordinary 65,536-field, per-object 1,024-
field, arena 262,144-field and shared-handle boundaries after +2 fields per
Throwable and +1 per EIIE. A field/string/checkpoint limit failure must retain the
existing Java-vs-hard-error distinction and old anchored head.

## Versioning, codec and API effects

Create a separate provisional `IOException0Interpreter`/`ioe0` package, artifact,
address, store marker, bootstrap/config/machine domains and machine magic. Start
fresh only: no SC0/TL0/LC0 import, migration, relabel or blob/store acceptance.
Keep SC0 start/resume/head/result signatures, opaque `javaClass`, owner/epoch CAS,
commit order, rollback and durable reopen unchanged. No message/cause is added to
the host ABI; guest bytecode observes refs/content. Uncaught I/O classes remain
TL0 kind0 with exact EVM-derived internal-name bytes, not new kinds 13--15.

The new canonical codec stores ordinary/arena field values and VM-message origin,
removes the wrapper table, and validates: message null or initialized exact String;
self sentinel/constructor transients; EIIE field type and VM-wrapper non-Error rule;
String backing/intern invariants; arena origin/kind/dynamic class; and canonical
re-encode equality. Validation never runs constructors, repairs fields or asks Go
for class/String/message data. Exact live-head binding remains required for resume.

Keep SC0 limits: <=256KiB runtime, <=1MiB checkpoint, 1..4096 JVM/internal units,
100M gas/30s ordinary calls, 1B/120s dedicated boundaries, 25M reserve and <=256
slices. IOE0-specific quota tests may use SC0's <=65,536 dispatch-unit allowance;
no accepted SC0/TL0/LC0/stock budget changes. Whole gate: external 20m/4GiB RSS.

## Proposed acceptance fixtures

Freeze 24 trusted Java-8 roots, each static `(I...)I`, <=4 input classes/64KiB:

1. eight message roots: Throwable/Exception/IOException/FNFE/EOF zero and selected
   literal/constructed/null messages, identity, UTF-16 content and virtual override;
2. eight origin roots: explicit/implicit AE and NPE, catch/rethrow, cause-null,
   `/ by zero`, and EIIE wrapping explicit/implicit causes; and
3. eight cause roots: EIIE null/cause constructors, VM wrapper, shared cause across
   two wrappers, Error propagation, wrapper OOM, failed init then NCDFE, and an I/O
   subclass caught as IOException/Exception with preserved message identity.

Run 24 one-call controls and q1+q7 actual chains for ten boundary-sensitive roots
(20 chains), stopping around allocation, sentinel/message writes, constructor
return, implicit fault, EIIE replacement and handler entry. Outcomes, refs,
contents, counters and final machine roots match within IOE0. Java 8 is primary;
Java 21 is comparison only. No oracle output enters EVM execution.

Add 32 independent groups: eight image/link/access/unsupported-API precedence; eight
ordinary/arena/string/field/handle/exact-checkpoint quota boundaries; ten mutated
codec states (self, partial constructor, message type, EIIE field, origin, intern,
counts/order/root); and six CAS/OOG/rollback/retry/disk/new-process cases. Include a
full ordinary heap that still raises implicit AE with its message, no speculative
output/log, and explicit EIIE versus VM EIIE field equality. Preserve all accepted
SC0 (if accepted), TL0/LC0/LB0/2231/stock/artifact gates separately.

## Oracle evidence and differences

Cases 01--30 cover zero/message constructors, explicit versus isolated implicit AE/
NPE, ordinary and VM-created EIIE, getException/getCause identity, fresh initCause,
explicit-null lockout, failed self-cause then valid cause, and EIIE disabled chaining.
Each case ran in a fresh VM, so evidence assumes neither HotSpot repeated fast-throw
reuse nor general stack-trace behavior. Java 8u504 and Java 21.0.9 agreed on all
class/cause identities, constructor message identities, `/ by zero`, distinct
non-interned AE message refs, EIIE null message, exact wrapper cause and initCause
rules.

Only cases 18, 19 and 26 differed: Java 8 implicit invoke/athrow NPE messages and its
wrapped NPE message were null; Java 21 supplied helpful, bytecode/local-dependent
text. IOE0 pins Java 8 null. This does not generalize to other NPE opcodes or VM
vendors. Constructor strings are oracle expectations, not guest logs or permission
to synthesize launcher output.

Evidence is ignored under `build/java-diff-mc-io-exception-preflight/`. Oracle source
SHA256 `c345820bb2ccd7dd46e92a9c4da03f2e42321bcfad3e049faee041861880abec`;
Java8 output `1c6c2b9f1796c3dfc5d026e843ffd98bce7dc0f3fd2c352a9b0caa09db53b34a`;
Java21 output `3c3b90e8b6af1c7b88215e3d80066870dc20b1b6348a9ae0771239e0ef687762`;
diff `2d38590b382831beba1ec1c602a6af4bd2c54ea43f9acc456cff9a4b3c55fb5e`;
candidate class hash list `f3ae14e21d7c481abb087b12196d308d8c6e9e14f8ae154f90e7fdcc15d73089`.
Java8 was OpenJDK `1.8.0_504-b01`; secondary was Oracle `21.0.9+7-LTS-338`.
Local Java8 `rt.jar` was 65,731,803B, SHA256
`85fb70f0b55ac1c84f2a5b2bc70d128db81749cc8ae0b5cc99cf7ea2df2c6097`
(inspection/runtime oracle only).

Reproduction from repo root:

```sh
timeout --signal=KILL 1200s build/java-diff-mc-io-exception-preflight/run_oracles.sh
```

The script compiles with Java8 `-source 8 -target 8 -g:none`, gives every JVM a 30s
kill timeout and an external 4GiB address-space cap (therefore RSS cannot exceed
4GiB), and records versions/class/output hashes. It ran successfully with 30 lines
per runtime. These small oracles do not prove IOE0, SC0 acceptance, Java SE, VFS,
Minecraft/EULA/listener behavior, stack traces, or the genuine `Done` marker.

## Unknowns before freeze

SC0's final acceptance/hash is unknown. Runtime/checkpoint/gas cost of two arena
fields, EIIE field migration and up to 256 reserved AE Strings is unmeasured. The exact
method-flag policy for Java8's synchronized `getCause` must be explicit: IOE0 may pin
an unsynchronized single-stack image and claim value semantics only, but must not
claim monitor/thread equivalence or silently no-op a lock. Messages for the other
VM fault kinds remain deliberately profile-rejected pending workload evidence and
small Java8 oracles. VFS bridge-selected FNFE/IOException text, close errors and
operation precedence are also not fixed here; a later bridge must pass a genuine
guest String into these constructors and must schedule/resume constructor Code,
never directly mint a message-filled ordinary object.
