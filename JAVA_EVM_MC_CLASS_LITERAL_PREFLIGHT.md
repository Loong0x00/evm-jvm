# MC-first class-literal COPY preflight

**Candidate only; not an accepted JVM/profile/cap/ABI/artifact change.** This is a
new isolated derivative from base `3dc007e42` of the parent MC-ENTRY candidate
`224c23b23`, specifically to address the next measured original resume blocker:
LogManager `<clinit>` predecode's `ldc_w CONSTANT_Class` at PC6. It does not retry
or process an original JAR. Parent alone retains that probe.

## Exact scope and design

The candidate lives entirely under
`evidence/java-evm/minecraft-entry/class-literal-preflight/`; no accepted runtime,
core, Make, cap, quota, global manifest, or ABI has changed.

* Predecode now accepts structurally valid tag-7 `CONSTANT_Class` for `ldc`/`ldc_w`.
  It checks the UTF8/name form, but intentionally neither finds, parses for use,
  access-checks, nor initializes the target until the instruction executes.
  Tag-7 arrays/primitive forms remain an explicit `BytecodeError(13,pc)` refusal.
  Other unsupported ldc tags remain refused.
* Executing a literal resolves its ordinary reference class/interface in the EVM
  package and applies existing class access rules. A missing execution target is
  the actual EVM diagnostic `MCEntryMissingClass(0x100c, pc, name)`. There is no
  host loader, parser, evaluator, decoded-page input or catalogue.
* A pinned Java-8 owned `java/lang/Class` bootstrap is appended after the old
  Runnable bootstrap; prior bootstrap indexes stay fixed. It has no public
  constructor/setter and a normal Java bytecode `getName()` which reads its private
  `String name` field. Factory allocation produces a genuine ordinary Class heap
  object and real existing guest String, mapping slash to dot while preserving `$`.
* Mirrors are canonical by a validated EVM heap scan, rather than host cache/map.
  The checkpoint codec already serializes ordinary heap fields; restored Class
  objects are checked against actual package names and duplicate targets are
  rejected. The represented target is not initialized by literal construction.
  String miss allocation reserves the following mirror's handles/object slots first
  so an OOM cannot publish a partial mirror.

Deferred: arrays/primitive mirrors, `TYPE`, `Object.getClass`, `Class.forName`,
newInstance, reflection/enumeration, ClassLoader and Thread. In particular a
reference class named `I` is not a primitive mirror. The candidate retains the
parent's MR0 empty `String[]` root, lazy Selected/direct reads and Runnable
semantics, 16 images/262144 bytes, CP4096/Code65535/heap/VFS/frame/1MiB checkpoint
limits, ordinary 100M gas/25M reserve and <=320KiB LOCAL engine boundary. It does
not use a 1B call or promote a profile.

## Fresh pins and installation

Solc is `0.8.30+commit.73712a01.Emscripten.clang`, optimize 200/viaIR/Cancun,
metadata off. Engine runtime is 303045 bytes, SHA-256
`a35a22d28314bcfcad05df73046d9ef7af08cfb6a5b24e3925f4ce1b9fee09fe`, Keccak
`838a37b319d197fc82c8db86645726e12d38c4d55a40186f59248b2e48de928c`.
Coordinator runtime is 3547 bytes, Keccak
`62b80a209abdb7b809d34078a8003136cba3f0a1ceacd359eec9eb6de707242f`.
The engine is LOCAL initial-state-only at
`0x4d434c4153534c49544552414c00000000000001`; the coordinator and AS0/ZI0/DI0
controllers remain ordinary CREATE. New `MC-CLASS-LITERAL-PREFLIGHT` domains and
address make old checkpoint compatibility intentionally unclaimed.

## Generated opaque-transport evidence

`run-smokes.py` builds source and runs only generated Java-8 fixture ZIPs through
EVM AS0→ZI0→DI0→coordinator. Its source-build watchdog evidence records 23
independent whole process-group commands, 191.894866s aggregate elapsed and
882515968B maximum sampled group RSS, each bounded at 20 minutes/4GiB with
file-backed stdout and group kill. No original archive argument exists.

* Narrow class/interface/`$` fixture checks same literal reference, Class cast/use,
  exact `getName`, and that Target's static initializer remains untouched until
  `Target.touch`. Host Java-8 oracle passes; EVM direct/q1/q7 reaches VOID with
  40 Java/4 internal steps, epochs 1/37/6 and ordinary gas sums
  56,416,943 / 567,016,298 / 121,737,578.
* Wide fixture has actual `ldc_w #607` Class operand (not merely CP padding). Its
  oracle passes and EVM direct/q7 reaches VOID at 9 Java/2 internal, epochs 1/2.
* An untaken excluded missing literal reaches VOID (5 Java/2 internal), proving no
  eager target bind. Taking the excluded literal reverts before checkpoint with
  selector `0x555db429`, site 4108/`0x100c`, PC0, `MissingTarget2`, 4,027,501 gas
  and unchanged EVM root.

Receipts, source/artifact hashes, fixture builders/oracles, raw refusal and
watchdog samples are durable under the owned evidence directory. This is not an
original-JAR, Minecraft, EULA, listener, world, or Done claim. The practical OOM
boundary is not independently swept in this narrow candidate; its reservation
logic requires parent review.
