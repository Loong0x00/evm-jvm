# MC-SC0 construction-state pre-freeze experiment

Status: **pre-freeze evidence and one recommendation only**, at `09f7b20` after
accepted MC-TL0. No SC0 freeze or production implementation is authorized. No
Minecraft/EULA/listener, VFS, peer/core/consensus, accepted artifact, setting, or
budget was changed.

## Basis and exact artifacts

Accepted TL0 remains 212,574 bytes, runtime SHA-256
`c1a9a48d598e7efb7eaf636222ee596e767a22e5859384acd33e99314acf2084`
and source SHA-256
`58315c6ecaa09888cc9c12b996e525137b8489c08950e516873895118cbe48b3`.
This experiment used a read-only copy of the earlier ignored String prototype, not
the TL0 artifact. Its Solidity source SHA-256 is
`18122c41526eec02658a807c775e389eb63a3ed90e244d9c7a44baa270b3adf1`;
the 207,145-byte runtime SHA-256 is
`01e2c9ce16f50bfba925e6d53acdef9777a52b316c17e7c2b01a53060cb82864`.
`cmp` confirmed copied source/runtime/String bytes equal the read-only originals.
The 984-byte String SHA-256 remains
`7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad`.
This oversized, minimally patched LC0-derived prototype is evidence only.

Two raw, EVM-supplied synthetic `java/lang/Object` images each declare static
`escaped:Object`, instance `inherited:int`, and genuine constructor Code:

* one-byte `return`: 168 bytes, SHA-256
  `3b6d6b9763dcac289325f4317f853a97036260ab7a34836739928560ac15ccfa`;
* `aload_0; putstatic escaped; iconst_1; iconst_0; idiv; pop; return`: 176
  bytes, SHA-256
  `ffc2cad26a31fd40b81fbd9a912ae8ac66a4e9d5bf7ef8f06dc5b11067f8c7db`.

The Java-8-target probe class is 1,129 bytes, SHA-256
`ed8f26be625afa64596a3e54398469f3c0918fc27e2bae84f8f1cc67e758fb16`;
its source SHA-256 is
`8555dd07a9ea1a29461cc33f57db2f6f8a61a64c756d922c698493deed9794c5`.
Only the holder class-name CP bytes were length-preservingly changed to
`java/lang/Object`; `javap` records the resulting exact references and Code.
These Object experiments are a **synthetic accepted-VM profile**, not a stock-JVM
oracle: no host JVM bootstrap Object was replaced or executed. Generator, EVM
runner, and inspector source SHA-256 are respectively `8a93b7ba1994bdc8f105bf1db3dfa5e3619367179fdcfa059709abbe003096f1`,
`700ade8d81f03aa207f962999057c908c1494a40809f3611356b2fa6b5bf3144`, and
`4901196531d87acbdf6ff878082b85f483e8552483e7a556eeac10eacf7831d7`.

## Concrete answer: reachable default String is possible

Yes. The accepted constructor rules enter root `Object.<init>` with `local0=REF`
even though the active String constructor immediately below still has
`local0=UNINIT`. Therefore Object Code can publish that REF to a static, then fail.
Unwind poisons caller UNINIT aliases, but correctly does not erase the already
published REF. The failed String remains reachable with inherited `INT:0`,
`value=REF:0`, and `hash=INT:0`.

Actual EVM results (one-call and linked q1 terminal machine roots agree):

| Object Code / root | one / q1 slices | result | machine root |
|---|---:|---:|---|
| return / defensive char copy | 1 / 87 | 97099 | `677f6953...c205fcaf` |
| return / `String(String)` | 1 / 32 | 110 | `d20109aa...9c59849e` |
| publish-fail / char constructor caught | 1 / 38 | 111 | `1805ebe0...2849448` |
| publish-fail / copy constructor caught | 1 / 41 | 1111 | `42d6fa73...294bd16` |

Results 111 and 1111 prove caught ArithmeticException, nonnull escaped identity,
dynamic String type, and (for 1111) distinction from the literal. Calling
`length()` on the escaped default object currently hard-reverted as
`BytecodeError(14,30)` (`62d5596d...000e...001e`), rather than producing an honest
Java outcome. That is direct evidence that option A needs native-service work, not
just a looser validator.

### q1 safepoints

With return-Object, defensive checkpoint 021 has String frame flags20/local
`UNINIT:3` and Object frame flags28/local `REF:3`. Checkpoint 022 is immediately
after genuine Object `return`: Object frame is gone, while the still-active String
frame is flags28/local `REF:3` and its fields remain default. Copy checkpoints
008/009 show the same transition for handle4. Thus REF means the superclass
constructor protocol completed; it does **not** mean the String constructor did.

With publish-fail, char checkpoint 017 has static `escaped=REF:2`, Object and String
constructors active, and String fields `[INT:0,REF:0,INT:0]`. Checkpoint 020 retains
that root with pending Arithmetic kind1/ref4. One internal unwind at checkpoint 021
removes both constructor frames and enters the caller handler, but static REF2 and
the default object remain. Terminal checkpoint 038 retains them. Copy checkpoints
014/017/041 repeat this for target handle4 while literal handle3 remains valid with
backing handle2. Selected checkpoint hashes and the full decoded chronology are in
`final-identities.log` and `checkpoint-construction-state.log`.

## Required state vocabulary and corrected graph rule

* **Fully initialized String**: its exact supported String constructor has returned;
  own `value` is a valid rank-1 char array and `hash` is zero or the content hash.
  A REF tag or successful Object return alone is insufficient.
* **Active-constructor String**: its String frame exists, including while Object is
  above it. It may be default, partially copied, or have `value` installed; the
  exact constructor PC/locals/stack delimit legal temporary states.
* **Reachable partial String**: reachable from statics, non-constructor frames,
  objects, reference arrays, intern roots, or pending state before successful String
  completion, or after its constructor failed. The synthetic static escape proves
  this category is nonempty in the unrestricted accepted VM profile.
* **Unreachable failed residue**: allocated/no-GC-accounted but absent from every
  such root/path after unwind. Only this category may safely use the proposal's
  default-residue exception under option B.
* **Default/null-backed** describes fields, not reachability or initialization.

Therefore the prior statement “only unreachable failed residues may default” is
false for unrestricted custom Object Code. It becomes valid only with the option-B
construction restriction below. Validation must not infer completion from REF.

The defensive constructor's source array and fresh backing are distinct (handles2
and4); while active, backing4 is a constructor-local temporary and is installed at
`putfield` before return. `String(String)` allocates no array: the source/literal and
target genuinely share backing2 after target `putfield`; that backing also appears
temporarily on the operand stack. These exact constructor-local aliases and the
intentional two-String backing alias are legal. No ordinary source array may become
an initialized String backing. No host String logic or handle creation occurred.

## Bounded options

**A — support every reachable partial state.** Add durable per-String lifecycle
(`allocated/active/completed/failed`) independent of REF tags and frames, validate
all graph roots/cycles against it, and preserve failed reachable objects. Every
native String service must implement honest behavior for each partial shape; for
example null backing dereference must raise Java NPE6 rather than hard
BytecodeError. Intern insertion/comparison, hash mutation, equals, and resumed
pending faults need corresponding atomicity tests. This is general but materially
larger and not justified for the first two trusted constructors.

**B — SC0-only no-callback Object profile.** Restrict only exact bootstrap String
allocation; leave all TL0 other-object/Throwable behavior unchanged. This keeps the
fixed String constructors as the sole code that can see post-super String REF and
makes failed null/OOM Strings unreachable after outer UNINIT poisoning.

**Recommendation: choose B for SC0.** At `new` of the separately versioned exact
SC0 `java/lang/String`, after normal class/hierarchy/String-layout resolution but
before class-init/allocation/quota mutation, EVM must resolve and parse the actual
direct `java/lang/Object.<init>:()V`. Normal malformed/missing/access/static/native/
Code errors keep their existing parser/link/call errors. A valid method is SC0-legal
only with `max_stack=0`, `max_locals=1`, empty exception table, and exact one-byte
Code `return`; ordinary non-Code/debug attributes remain governed by existing
classfile rules. Arbitrary otherwise-legal Object static and instance fields,
including inherited-layout boundary shapes, remain legal and charged base-first;
Object `<clinit>` and all non-String allocation semantics remain ordinary.

A valid but noncanonical Object constructor hard-fails as new reserved
`StringProfileError(4,newPC)` before String allocation. Because `new` executes first,
this intentionally precedes any later malformed/unsupported constructor descriptor;
with a legal Object profile, malformed String descriptors retain
`CallError(4,invokespecialPC)` and valid unsupported descriptors retain
`StringProfileError(1,invokespecialPC)`. Do not skip or native-bind Object Code:
`invokespecial` still pushes its frame and its real `return` dispatches. Both
`String(char[])` and `String(String)` then genuinely execute all Java bytecodes,
including defensive copy or backing/hash field operations. Literals do not execute
`new` and remain unchanged. This narrow exact shape is preferable to unsound
behavioral analysis or rejecting every Object field/class replacement.

## Commands, bounds, and limitations

Commands were `javac --release 8 -g:none`, `javap -v/-c`, then
`(ulimit -v 4194304; timeout 1200s go run
./build/java-diff-mc-sc0-construction-state-preflight/run_construction_state.go)`
and the read-only Python checkpoint inspector. Calls used 100,000,000 gas; no 1B
boundary call was needed. Max measured call was 6,480,217 gas; all calls completed
in under 1 s. The process had a 20-minute/4-GiB virtual-memory cap; peak RSS was not
measured. `evm-construction-state.log` SHA-256 is
`6ea92d02575bbc15bbb583eda4b0f814a7944003b580e5fa9c8b68894fae8354`;
inspection log SHA-256 is
`276f88cf73fb2c92eb08708d26f0be1f44e7ac1697d96cffcc2e7037a2066075`.

Unmodified ordinary fixtures were rerun on Java 8u504 and Java 21.0.9; both retained
97099/111/111/12/64076 and exact range exception classes. Their rerun log SHA-256 is
`7aa3d0785db29bf1701b142732b86f0eaa99a7138f3caa657f671b8f2e577d98`.
No production validator, profile-error precedence, malformed mutation, quota edge,
OOG rollback, durable reopen, old gate, or maximum-copy test was run here.

All accepted 27 TL0 image bodies and artifacts must remain byte-identical. A future
SC0 must use a separate runtime, bootstrap/config domain, schema, and versioned
String image; it must neither reinterpret TL0 checkpoints nor rewrite the accepted
String image. No SC0 freeze is authorized until the parent reviews this choice.
