# MC next-entry frontier — static note only

Status: **small static planning note; no implementation freeze or acceptance**.
VFS0a remains **NOT accepted** while the parent finishes final acceptance of the
state-corrected 292968-byte candidate. IOE0 remains the last accepted profile.
This work did not execute Minecraft, a server main, or any guest logic; create an
EULA file; open a listener; or change production/core/settings. It only read the
pinned JAR as ZIP bytes and used `javap` for trusted static disassembly.

## Evidence boundary

Artifact:
`/home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar`.
It is exactly 30222121 bytes and SHA-256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`.
Its 75-byte manifest names `net.minecraft.server.MinecraftServer` as `Main-Class`.
These facts match `JAVA_EVM_PROGRAM.md` and `JAVA_EVM_MC_STARTUP_PROPOSAL.md`.
All byte counts below are uncompressed class-entry lengths unless labeled otherwise.
They are static direct-reference sets, **not a dynamic trace or transitive closure**.

The entry class is 33457 bytes, classfile major52, with highest constant-pool index
1455. Its `main` Code is 441 bytes (`max_stack=8`, `max_locals=13`) and its
`<clinit>` Code is 20 bytes (`max_stack=3`, `max_locals=0`). Thus each body and the
class itself fit the current per-Code/CP and 64KiB aggregate byte ceilings in
isolation. The immediate blockers are entry shape, class count/data discovery and
libraries, not this one method's Code size.

## Exact earliest static frontier

Invoking the static `main` first initializes `MinecraftServer`. Its declared JAR
hierarchy is:

| JAR class | bytes | why present before/at entry |
|---|---:|---|
| `net/minecraft/server/MinecraftServer` |33457|declares `main`/`<clinit>`|
| `bn` |1093|direct interface; declares seven default methods|
| `tr` |300|direct interface|
| `um` |127|direct interface|

Those four entries total34977 bytes (16677 compressed). `java/lang/Object` and the
fourth direct interface `java/lang/Runnable` are platform classes; current VFS0a has
Object but no Runnable bootstrap. Under Java8 initialization rules `bn` is also an
initialization prerequisite because it declares defaults; its class has no
`<clinit>`. Merely fitting these four JAR entries does not make entry executable.

`MinecraftServer.<clinit>` performs exactly this Code sequence:

1. PC0 `LogManager.getLogger()`; PC3 stores static logger `k`.
2. PC6 allocates `java/io/File`; PC10 loads literal `usercache.json`;
   PC13 calls `File(String)`; PC16 stores static file `a`; PC19 returns.

VFS0a's current File/String subset covers that File constructor/literal shape, but
logging comes first. Adding the 11864-byte bundled `LogManager` makes five direct
JAR entries/46841 bytes: under64KiB but already over the current four-raw-class cap.

The direct JAR owners named by `LogManager.<clinit>` are `StatusLogger`,
`LogManager`, `PropertiesUtil`, `LoggerContextFactory`, `LoaderUtil`, `Logger`,
`ProviderUtil`, `Provider`, and `SimpleLoggerContextFactory`: 9 entries/69253 bytes.
Union with the four entry-hierarchy entries is 13 entries/104230 bytes, exceeding
both current raw-input caps before any transitive library closure. This set includes
conditional branches and is not a claim that a JVM eagerly loads all thirteen.

The same LogManager Code directly references missing platform surfaces including
`Class.getName/newInstance`, `TreeMap`, `Iterable`/`Iterator`, `SortedMap`, `Set`,
`Map.Entry`, `URL`, `StringBuilder`, exceptions, properties and loader utilities.
PC0 calls StatusLogger and PC15 calls PropertiesUtil unconditionally; the configured
factory/provider branches depend on pinned System properties and resource results.
The JAR actually contains deflated `META-INF/log4j-provider.properties` (904 bytes),
which names `org.apache.logging.log4j.core.impl.Log4jContextFactory` (10701-byte
class), and deflated `log4j2.xml` (1124 bytes). ProviderUtil names that resource and
LoaderUtil calls `ClassLoader.getResources`. No Class/ClassLoader/resource semantics
exist today. Therefore replacing this with a fake logger or assuming the SimpleLogger
branch would not be unchanged startup.

Only after entry initialization does `main` execute PC0 `invokestatic ni.c`. Active
use initializes `ni` first; `ni.<clinit>` reads `System.out` and calls
`LogManager.getLogger`. `ni.c` then checks its once flag and at PC11 calls `ni.d`,
followed by direct static calls to `qe`, `aow`, `aqq`, `uz`, `alk`, `ain`, `akg`,
`akh`, `vi`, `anh`, later `aku` and `qs`; `ns`/`bfn` occur on its debug branch.
The 16 direct JAR owners in `ni.c` (including `ni` and Logger) total210429 bytes.
No transitive registry/class-initializer closure was measured.

The argument loop does not begin until main PC26, after `ni.c` returns. Later direct
main references include String.equals/Integer.parseInt, UUID/Proxy/authlib, `ph`,
`nz`, `rz`, Runtime/Thread/AWT and Logger. Its eight bundled instruction-owner
classes total89775 bytes, but branch outcomes and descriptor-only types make this
only a prioritization inventory. At PCs291/294 main also needs `File.getName()` and
`File(String,String)`, both absent from VFS0a; they are real later gaps, not the first
pre-main blocker.

## Current-cap contrast

VFS0a currently accepts an eager `bytes[]` bundle of at most4 raw classes/65536 total
bytes, reparses the supplied bundle on resume, and has38 fixed bootstraps. Entry is
an exact-int static root with `int32[]`; `_loadRoot` rejects void/reference roots, so
`main([Ljava/lang/String;)V` cannot be selected or receive a guest String array.
There is no ClassLoader or JAR/resource lookup. Mutable VFS regular-file data is
65536 bytes aggregate, checkpoints are1MiB, and the heap cap is1024 ordinary objects.
The official 30222121-byte JAR cannot honestly be put in that VFS/checkpoint, while
the first direct logging set already exceeds raw class count/bytes. Do not raise or
reinterpret any accepted cap to hide this mismatch.

## Recommended dependency-ordered bounded stages

1. **MC-CD0 — artifact-backed class/resource transport.** Add a separately scoped
   LOCAL immutable paged artifact store and lazy EVM class table, first proven on
   small trusted ZIP fixtures. EVM must authenticate the full pinned raw artifact,
   parse ZIP names/metadata, inflate requested deflated entries, parse classfiles,
   and persist loaded-class/link/init identity across checkpoints. Host supplies only
   opaque committed byte pages/ranges requested by EVM. Measure new finite page,
   class and metadata ceilings; do not consume/raise VFS0a's64KiB mutable-file or
   1MiB checkpoint limits and do not migrate stock modules merely for this art path.

2. **MC-LAUNCH0 — reference/void entry plus earliest platform kernel.** Add genuine
   `main(String[])V` launch with guest-created String[] and pinned arguments, then
   workload-needed Runnable, System/PrintStream, Class/ClassLoader, properties,
   resource streams, URL, minimal collections/reflection construction and
   StringBuilder behavior evidenced above. Freeze each sub-surface with generated
   Java8 fixtures and exact failures; no blanket native/no-op services. This stage is
   not “basic StringBuilder first”: it is ordered by the real LogManager frontier.

3. **MC-ENTRY0 — first unchanged server prefix, only after separate authorization.**
   With bounded artifact/class/heap/gas/continuation limits, attempt the pinned raw
   JAR and require an EVM-issued checkpoint after genuine `MinecraftServer.<clinit>`
   completion with root `main` poised at PC0. Record class/method/PC, loaded-entry
   commitments, resources, System properties and roots. Do not claim `ni.c` return,
   EULA progress, listener, world preparation or Done. Use the first real EVM stop to
   freeze the next `ni`/registry closure instead of extending from static guesses.

## Parent decision required before MC-CD0 freeze

Preferred boundary: upload/authenticate raw JAR pages, let EVM parse the central
directory, and later provide only authenticated compressed ranges that EVM inflates.
A whole-JAR EVM store is simpler semantically but much larger; on-demand pages need
an EVM-established page root plus full-artifact SHA-256 verification. Host extraction
of named classes/resources is acceptable only if EVM independently proves each result
against the raw JAR's ZIP record/compressed bytes. A host-built class catalogue,
offset list, extracted-class hash list or host ZIP/ClassLoader fallback cannot be
production authority. Parent must choose and bound one option; this note freezes none.

## Unknowns/nonclaims

Static references do not establish actual load order inside conditional branches,
default properties/provider choice, transitive Log4j/registry closure, unsupported
opcode reachability, or whether1024 objects/1MiB checkpoint/finite gas suffice.
No JDK class bytes were inventoried here, and no actual main trace, VFS acceptance,
Minecraft execution, EULA acceptance, network bind or readiness evidence exists.
The target remains the LOCAL artistic VM-in-VM path, not full Java SE conformance or
standard-deployment/module migration.

Reproduction outputs are ignored under
`build/java-diff-mc-next-entry-frontier/`. Commands used: `sha256sum`; `unzip -p/-l`
and Python `zipfile` reads; and per-class `timeout 30s javap -classpath <JAR>
-p -c -s -verbose ...`. The whole static preflight stayed within20 minutes/4GiB.
