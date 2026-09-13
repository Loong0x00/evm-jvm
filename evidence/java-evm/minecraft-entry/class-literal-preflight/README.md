# MC class-literal COPY preflight

Unaccepted, generated-fixture-only derivative of the parent `224c23b23` MC-ENTRY
COPY, based at integration `3dc007e42`. It implements only ordinary reference
class/interface `CONSTANT_Class` literals (`ldc`, `ldc_w`) and the actual next
`Class.getName()` path. It does not take an original archive path and did not
handle or execute Minecraft.

## Pin and installation boundary

* Engine source SHA-256 `975eb5c6d81d339cd4cea0bb5da19108a9e7af7d115294ee979a8309436160c5`;
  runtime 303045 bytes, SHA-256
  `a35a22d28314bcfcad05df73046d9ef7af08cfb6a5b24e3925f4ce1b9fee09fe`, Keccak
  `838a37b319d197fc82c8db86645726e12d38c4d55a40186f59248b2e48de928c`.
* Coordinator source SHA-256 `59d93f1d80fc7090657757012d0f4f1c2dbb19c84bffa5ae4043a77862fe7027`;
  runtime 3547 bytes, Keccak
  `62b80a209abdb7b809d34078a8003136cba3f0a1ceacd359eec9eb6de707242f`.
* Solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, viaIR, Cancun,
  CBOR metadata off. ABI remains the copied 32-engine/12-coordinator entry ABI;
  there is no new public mirror API.
* New domains are `MC-CLASS-LITERAL-PREFLIGHT/.../v1`. The LOCAL initial-state
  engine address is `0x4d434c4153534c49544552414c00000000000001`; the coordinator
  is ordinary CREATE. This is intentionally incompatible with parent checkpoints;
  it makes no cross-code restore claim. AS0/ZI0/DI0 remain ordinary CREATE.

The engine stays beneath the 320 KiB LOCAL cap. It retains 16 images/262144 bytes,
CP4096, Code65535, existing heap/VFS/frame and 1 MiB checkpoint caps, 100M gas
ordinary calls and the 25M commit reserve. Nothing changes accepted runtime/core,
ABI, quota, or standard CREATE deployment.

## Narrow semantics

Predecode accepts only CP tag 7 for `ldc`/`ldc_w`, validates its UTF8/internal
reference form, and does not bind it. Execution resolves the target through the
EVM package, checks ordinary class accessibility, and returns
`MCEntryMissingClass(site=0x100c, context=PC, name)` if absent. Arrays, primitives,
`Object.getClass`, wrapper `TYPE`, `forName`, constructors/newInstance,
ClassLoader/Thread and enumeration are still unsupported. `I` means a reference
class named `I`, never `int.class`.

`java/lang/Class` is a new final owned bootstrap append after historical Runnable
(index 39 after the old 0..38) with a private `String name`, private constructor,
and ordinary bytecode `getName()`. Its pinned Java 8 image SHA-256 is
`30bfb644d8bd3bb03ee1059b40842bfe72313bbb927c14d5d69a3a1b46fb778b`.
Users cannot override it. The factory creates an ordinary heap object and fills
that private field with an ordinary interned guest String; it never initializes
the represented target. Heap scan (not a host cache) discovers canonical mirrors,
and checkpoint restoration validates each Class object has exactly one real
represented name and no duplicate target. Slash changes to dot; `$` remains `$`.
Class allocation reserves post-String object/handle/field capacity before a String
miss, so OOM leaves no partial mirror. No arbitrary forged Class object is silently
accepted.

## Reproduction and actual generated smoke

`run-smokes.py OUT` refuses an existing output, builds its copied Go transport,
generates only Java 8 fixtures, and runs opaque ZIP→AS0→ZI0→DI0→coordinator→engine.
It has no original archive argument. Every command has a fresh 20-minute/4GiB
whole-process-group watchdog, sampled `/proc` RSS, group kill on either limit and
file-backed stdout (no unconsumed pipe); reports are retained under
`actual-receipts/source-watchdog-cast/` (the earlier buildless watchdog run is retained alongside it).

The generated JVM oracle proves narrow, wide, and untaken branches before EVM.
Actual EVM results are retained in `actual-receipts/source-watchdog-cast/summary.json` and per-world
receipts: narrow literal direct/q1/q7 terminates at 40 JVM/4 internal steps with
1/37/6 epochs; wide `ldc_w #607` direct/q7 terminates at 9/2 with 1/2 epochs;
untaken missing target terminates 5/2. The omitted missing target reverts before a
checkpoint, selector `0x555db429`, decoded site `4108` (`0x100c`), PC 0 and name
`MissingTarget2`; its EVM root is unchanged. These are generated-class results,
not original-JAR/Minecraft/Done evidence or acceptance.
