# MC link-frontier preflight

Status: **generated Java-8 measurement only; no production implementation or acceptance.**
This work is based on accepted CB0 `0fdb9dcf7` and the generated-main evidence at
`a70ca4acf`.  It changes neither CB0, VFS0a, AS0/ZI0/DI0, engine/root ABI, artifact,
profile nor any quota.  No original class/JAR was supplied to Java execution, and
there is no Minecraft/EULA/listener/world/Done claim.

## Question and bounded method

Does the current constructor-fixed CB0 package bind every constant-pool class at
setup, or does a class reference become binding only at hierarchy preparation or at
the instruction that consumes it?  The decisive inputs are generated Java 8 public
classes only:

* closed graph: `LinkLauncher`, `LinkMain extends LinkBase implements LinkMarker`,
  `LinkBase`, `LinkMarker` (exactly four images). `LinkLauncher.run(int)` creates a
  guest `String[]` containing `"\u03bb"` and `"\u2603"`, calls the public static
  **void** `LinkMain.main(String[])`, and returns its observable static state;
* `DemandEntry` has a constant-pool `MissingTarget` class reference and unused field
  descriptor. Mode 0 does not consume it; modes 1/2/3 respectively consume it via
  `invokestatic`, `new`, and `checkcast`. `MissingTarget.class` is deliberately not
  selected in those worlds;
* `SuperEntry extends MissingSuper` and `InterfaceEntry implements MissingInterface`
  are selected without the named direct dependency.

The fixture compiler/oracle is pinned Java 8u504. The host oracle is only for this
trusted generated source; it never runs against EVM execution input.  Its expected
outputs are `10724,41,10731,41`. The Unicode assertion consumes the **UTF-16 code
units**, not merely lengths: U+03BB is 955 and U+2603 is 9731, giving 10724 for mode
0 and 10731 for mode 7. `final3-fixture.json` records source-derived class/ZIP and
`javap` hashes; the generated verbose output proves all three demand opcodes refer
to `MissingTarget`.

The driver is copied to a new ignored `build/java-diff-mc-link-frontier-*` directory
before build. It uploads one opaque generated ZIP through only public `cb0.Session`
APIs: AS0 append/seal, ZI0 indexing, DI0 FINAL decode/publication, CB0 coordinator,
then `Start`/`Resume`/`Head`/`ReadCheckpoint`. Known fixture names are merely
assertions. The CB0 package is recomputed from actual EVM `Head` values using the
frozen CB0 domains and rechecked by EVM. The driver neither parses ZIP/class data
nor inflates it on the execution path; it has no reflection, private Session,
StateDB/SetCode, raw-class execution input or failed-trace recovery.

## Captured result

`evidence/java-evm/link-frontier/preflight/final3-report.json` is the strict
machine-readable result; raw per-call/refusal records are in `final3-results/`.
The replay completed under the 20-minute/4-GiB sampled group watchdog in **7.199 s**
with **331,214,848 B** peak group RSS (`final3-watchdog.json`).

| world | actual outcome |
|---|---|
| four-image closed graph, direct mode 0 | terminal result 10724, 44 JVM / 6 internal steps |
| same graph, direct mode 7 | terminal result 10731, 44 / 6 |
| same graph, mode 7 q1 | 44 distinct fresh Start/Resume processes; terminal result 10731, 44 / 6; machine, VFS, AS0, ZI0, DI0 FINAL, and frozen-domain package roots equal direct |
| one-image `DemandEntry`, mode 0 | terminal 41: the non-consumed `MissingTarget` CP reference does not bind merely from parsing the entry image |
| omitted `MissingSuper` | `HierarchyError(1,0)`, selector `0xa52e829f`, before/after root, epoch and checkpoint unchanged |
| omitted `MissingInterface` | current `LinkError(4,0)`, selector `0x427cfac5`, unchanged state |
| omitted `MissingTarget`, modes 1/2/3 | current `LinkError(4,12)`, `(4,21)`, `(4,38)` respectively for `invokestatic`, `new`, `checkcast`; selector `0x427cfac5`; unchanged state |

These are EVM reverts, not fabricated Java exceptions or OOG. Every actual
Start/Resume/refusal EVM call is asserted `0 < gasUsed <= 100000000`; no 1B call was
made. The q1 `invokestatic` case committed epochs 1--5, then the sixth fresh-process
`resume` reverted `LinkError(4,12)` using 3,287,171 gas. Its exact prior checkpoint,
root and epoch 5 remained readable from another fresh process. Thus a previously
published EVM-issued continuation survives the refusal, but cannot pass the still
missing dependency; this is not a successful lazy load.

A generated five-name selection is also captured. After four genuine decoders the
fifth `CreateDecoder` is rejected by the public CB0 bounded-slot guard with measured
zero EVM gas and unchanged root (`decoderCount:4`). It is intentionally distinguished
from an EVM call/refusal: CB0 cannot construct a five-resource coordinator, so this
is a real current fixed-package frontier rather than a silently bundled fifth image.

`verify.py` asserts every row above (including gas, selectors/code/detail, roots,
q1 PIDs, Unicode output and fixture hashes). `reproduce.sh` refuses an existing output
path and sets `TMPDIR` beneath that task-owned ignored build directory. `SHA256SUMS`
covers the durable sources and final3 capture.

## Limits and next dependency proposal

The focused VFS0a source keeps `MAX_RAW_CLASSES=4`, `MAX_RAW_BYTES=65536`,
`MAX_CONSTANT_POOL=4096`, and `MAX_CODE=65535`
(`jvmevm/runtime/local/vfs0a/VFS0aInterpreter.sol`, constants and parser checks).
CB0 preserves the same 1--4 selected-image / aggregate-65536 package boundary and
binds a checkpoint to that fixed artifact. This preflight therefore shows **demand
resolution is the immediate semantic blocker** once a reference is reached, while
**eager package capacity is independently already a hard frontier**. It does not show
that a four-image package is lazy loading.

The smallest honest next preflight is not a broad Java SE rewrite or a naked cap
increase. It is a separately frozen, generated-only EVM experiment for one bounded
pending symbolic reference: bind the sealed resource identity/name/root in the
checkpoint, EVM-read/decode exactly that resource, validate its declared identity,
append it to a bounded active class registry, and resume the consuming opcode with
atomic rejection/persistence tests. It must measure both a missing-reference retry
and the 4-to-5 frontier, with no host catalogue/class parser and no claim that it
loads arbitrary transitive graphs. A separate capacity design is required before
that can be an MC path: static-only `JAVA_EVM_MC_AS0_PREPARATION.md` records that
MinecraftServer/bn/tr/um plus LogManager is five classes, even though 46,841 bytes,
and `JAVA_EVM_MC_DI0_PARENT_PREFLIGHT.md` records the already EVM-decoded
`AbstractLogger.class` at 90,309 bytes. Those are not execution or reachability
evidence, but they rule out pretending the current
four-class/64-KiB fixed package is a lazy MC loader. Required bootstrap/platform APIs,
other bytecode families, threading, configuration/resources and the actual startup
path remain unmeasured.
