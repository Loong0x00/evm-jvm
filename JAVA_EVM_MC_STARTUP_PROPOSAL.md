# Minecraft server startup compatibility preflight (proposal only)

Status: documentation-only inventory, **not a frozen stage contract and not an
acceptance claim**. This proposal was prepared from the accepted M5c-d profile and
the frozen-but-unaccepted M5d-a contract. No Minecraft server was executed, no
`eula.txt` was created or changed, no credentials were supplied, and no socket was
opened. The downloaded files under ignored `build/java-diff-mc-startup-preflight/`
were only subjected to bounded ZIP/classfile inspection.

## Recommendation

Use **Minecraft Java Edition server 1.12.2** as the candidate for the first
startup-complete workload, subject to an explicit target freeze and EULA/legal
review before any execution. Do not call it “latest”: the official manifest
retrieved for this preflight reported latest release `26.2`, while this proposal
intentionally chooses an older Java 8 target. Compare and retain **1.21.5** as a
pinned Java 21-era control target, not as the first target.

1.12.2 is the less infeasible first target because Mojang metadata selects Java
8, its server JAR directly names `net.minecraft.server.MinecraftServer` as the
main class, and all inspected classes have classfile major versions 49--52. The
1.21.5 distribution adds a bundler launch layer, 44 nested JARs, Java 21 / major
65 classes and a substantially larger class/library surface. This is a priority
recommendation, not evidence that 1.12.2 can currently run: the accepted runtime
cannot enter `main(String[])`, load this class graph, provide Java SE libraries,
or preserve a server across transactions.

Reasons not to select 1.12.2 silently are its age, legacy dependency/security
risk, and the fact that compatibility with it does not imply compatibility with
current Minecraft. Before freezing an implementation workload, the parent/user
should explicitly choose between:

* `MC-1.12.2-startup`: shortest credible Java 8 route recommended here; or
* a separately pinned modern route such as `MC-1.21.5-startup`: much larger but
  closer to current Java semantics.

## Official artifact pins and terms

Official metadata was retrieved on `2026-09-08T17:47:46Z` from Mojang's Piston
endpoints. SHA-1 is the digest published by Mojang; SHA-256 below is a local
additional digest.

| Item | 1.12.2 candidate | 1.21.5 Java 21 control |
|---|---|---|
| Release time in manifest | `2017-09-18T08:39:46+00:00` | `2025-03-25T12:14:58+00:00` |
| Version metadata URL | `https://piston-meta.mojang.com/v1/packages/832d95b9f40699d4961394dcf6cf549e65f15dc5/1.12.2.json` | `https://piston-meta.mojang.com/v1/packages/405e2a86530bad6992f832b66a0421fb6a65e5c8/1.21.5.json` |
| Metadata SHA-1 | `832d95b9f40699d4961394dcf6cf549e65f15dc5` | `405e2a86530bad6992f832b66a0421fb6a65e5c8` |
| Metadata SHA-256 (local) | `56dac2e1caa872d7e37a7b5523056cd812dca94f912ad2bd652817bee60edca4` | `513e5d07ac224321b9c6281f0362d9a0168a960c4e96eab8b8c1ee3ee57d2b9b` |
| Mojang Java selection | `jre-legacy`, major 8 | `java-runtime-delta`, major 21 |
| Official server URL | `https://piston-data.mojang.com/v1/objects/886945bfb2b978778c3a0288fd7fab09d315b25f/server.jar` | `https://piston-data.mojang.com/v1/objects/e6ec2f64e6080b9b5d9b471b291c33cc7f509733/server.jar` |
| Exact bytes | `30,222,121` | `57,269,758` |
| Official SHA-1 | `886945bfb2b978778c3a0288fd7fab09d315b25f` | `e6ec2f64e6080b9b5d9b471b291c33cc7f509733` |
| SHA-256 (local) | `fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e` | `ae7681dadce21b6b4017d28e7eb567d86b6c100a6969994f540b9e54f812dc29` |
| Server manifest main | `net.minecraft.server.MinecraftServer` | `net.minecraft.bundler.Main` |

The 1.21.5 outer JAR's `META-INF/versions.list` pins nested
`META-INF/versions/1.21.5/server-1.21.5.jar` at 18,585,350 bytes and SHA-256
`e6d853588b55572d05087026098cb630ae1bf1b980f30becfdf0c5906e960dae`;
the extracted bytes matched. Its `META-INF/libraries.list` enumerates 43 library
JARs in addition to that nested server JAR.

Minecraft server software is copyrighted software, not a project source fixture.
The official download page states that downloading software from that page means
agreement to the Minecraft EULA and Privacy Policy. The current EULA also restricts
distribution and commercial use. Relevant official pages are:

* `https://www.minecraft.net/en-us/download/server`
* `https://www.minecraft.net/en-us/eula`
* `https://www.minecraft.net/en-us/privacy`

Local static snapshots of the first two pages have SHA-256
`996978437830a9530af703a75c5d56685e22ee72e285585b4c51c81f0f86e773`
and `eaf387c3bea4ee1667915344d0ef45c056bcb3f0f7bf166947ec890a2b0af58b`
respectively. These hashes record retrieved evidence, not permanent terms; the
live terms control and may change. Do not commit or redistribute the JARs, and
review bundled third-party notices/licenses separately.

Both inspected servers contain the `eula.txt` gate and the text `You need to
agree to the EULA in order to run the server. Go to eula.txt for more info.`
This preflight did **not** write `eula=true` or otherwise perform that runtime
acceptance. Reaching the proposed marker later requires a separately authorized,
explicitly pinned virtual `eula.txt`; bypassing, patching, or auto-accepting the
gate is forbidden.

## Genuine startup-complete marker

For 1.12.2, the exact classfile literal is:

```text
Done ({})! For help, type "help" or "?"
```

It occurs in obfuscated class `nz`, method `protected boolean j() throws
java.io.IOException`, at bytecode PC 989 and is passed with the formatted duration
to `org/apache/logging/log4j/Logger.info` at PC 994. In that same method the guest
logs `Preparing level "{}"` at PCs 920--930, calls the level/world preparation
method at PCs 935--950, and only after that call returns computes elapsed time and
emits `Done`. With deterministic English/default decimal formatting, the accepted
rendered line must match exactly:

```text
Done (<one-or-more decimal digits>.<exactly three decimal digits>s)! For help, type "help" or "?"
```

The logger's normal timestamp/thread/level prefix may be transported separately;
the message body above is the marker. An early
`Starting minecraft server version 1.12.2` or `Preparing spawn area`/`Preparing
level` line is a **startup banner/progress message, not completed startup**.

For comparison, 1.21.5 contains `Done ({})! For help, type "help"` in `aqr`,
method `public boolean e() throws java.io.IOException`, and invokes SLF4J
`Logger.info` at bytecode PC 566 after its level-preparation call returns at PC
521. This confirms that a modern target needs a separately pinned marker; the
1.12.2 question-mark suffix must not be assumed for modern releases.

### What marker acceptance would prove

A future acceptance record must show all of the following in one version-pinned
run:

1. The unchanged raw artifact matches the official SHA-1 and recorded SHA-256,
   and the EVM itself is bound to a commitment to those raw bytes.
2. Standard, unmodified EVM bytecode parses/loads and executes the actual server
   path. No host JVM, AOT specialization, translated classes, patched branch,
   hardcoded string, skipped world initialization, or host server logic is used.
3. The guest returns from the level/world preparation call preceding the marker
   and reaches the real logger invocation in `nz.j`, with class/method/PC
   provenance or an equivalent EVM trace commitment.
4. The rendered marker bytes come from the guest String/formatting/logging path;
   an external adapter only transports already-produced bytes.
5. Inputs and virtual-platform state (artifact/config/VFS root, clock policy,
   scheduler/network policy, gas and continuation count) are recorded, and every
   transaction has finite gas.

That would prove genuine startup completion for **1.12.2 under the specified
virtual platform**. It would not prove a listening OS socket, client connectivity,
login, gameplay, later tick-loop correctness, crash-free persistence, arbitrary
Java, Java SE conformance, modern Minecraft support, or standard deployment of
the present monolith. Connectivity remains optional later work.

## Static compatibility inventory

The probe recursively inspected ZIP entries and classfile structure, constant
pools, method flags and Code bytecode. It did not perform reachability analysis,
load classes, initialize classes, invoke methods, or run Java. Thus whole-JAR
counts are a conservative surface inventory, not a claim that every bundled
client/optional/library class lies on headless startup.

| Static measure | 1.12.2 | 1.21.5 distribution |
|---|---:|---:|
| ZIP entries recursively seen | 20,554 | 39,544 |
| Classfiles | 19,007 | 31,047 |
| Class bytes | 64,620,541 | 120,285,305 |
| Classfile majors | 49:34, 50:2,986, 51:11,811, 52:4,176 | 46:117, 49:57, 50:1,993, 51:1,456, 52:20,241, 53:24, 61:589, 65:6,570 |
| Methods | 215,302 | 352,074 |
| Native methods in supplied classes | 308 | 278 |
| Synchronized methods | 205 | 321 |
| Largest Code body | 9,625 bytes | 58,769 bytes |
| Largest constant pool | 2,805 entries | 9,943 entries |

Both distributions use, somewhere in their supplied classes, `invokedynamic`,
`monitorenter`, `monitorexit`, `athrow`, all primitive numeric families,
`invokevirtual`/`invokeinterface`/`invokespecial`, object and primitive arrays,
`multianewarray`, switches and `wide`. The inventory also finds broad references
to Java platform APIs. For 1.12.2 these include 542 distinct unresolved `java/`
class names, 143 `javax/` names and 12 `sun/` names. Examples include:

* `java/lang/String`, boxed primitives, `Class`, `ClassLoader`, method handles,
  reflection, exceptions and system properties;
* `Thread`, `ThreadLocal`, executors, futures, atomics, locks and monitors;
* `System.nanoTime/currentTimeMillis`, locale, random/UUID and security services;
* `java/io`, `java/nio`, ZIP/DEFLATE, charsets and filesystem paths;
* `java/net`, NIO channels/selectors and the bundled Netty stack;
* Log4j/SLF4J formatting, configuration, resource loading and output;
* auth/crypto/DNS/HTTP capabilities, even where a no-client startup may not
  exercise every path; and
* world/data registries, data fixes, resource packs, NBT/region persistence and
  initial spawn/world generation.

The accepted M5c-d runtime is far below this profile: maximum 64 supplied user
classes, a static int-only root ABI, 128 frames, bounded 1,024-object and
1,024-array heaps, no general Strings/class library/main launcher, no dynamic
class loading/JAR/resource path, no threads/monitors, no reflection or
`invokedynamic`, no filesystem/network/time/logging platform, and invocation-local
state reset. M5d-a adds only the frozen implicit-exception/handler foundation and
is still unaccepted; even after acceptance its intentionally deferred Throwable
APIs are required by these libraries.

### Required semantic and platform work

A startup route must cover the *reachable* subset without pretending unreachable
whole-JAR features are complete:

1. **Launcher/classfiles:** `public static void main(String[])V`, String and Class
   objects, Java 8 verification/linking details, scalable class namespaces,
   JAR/manifest/resource lookup, ZIP and DEFLATE. Raw artifact parsing and class
   resolution remain EVM work; an offline inventory cannot become a production
   host parser.
2. **JVM semantics:** remaining constant kinds, general descriptors, full object
   layouts, exception construction/APIs, `invokedynamic`/method handles used by
   libraries, monitors/synchronized methods and the reachable reflection profile.
   No JNI/native method may silently fall back to the host.
3. **Libraries:** a pinned, testable Java 8 class-library profile including
   Strings/builders/formatting, collections, concurrent utilities, I/O/NIO,
   charsets, ZIP, logging and resource/service loading. Pure-Java library code may
   execute as guest bytecode; VM/platform primitives must be explicit ordinary-EVM
   implementations.
4. **Scheduling/time:** deterministic cooperative guest threads/fibers, task
   queues, monitor/wait/notify and atomics sufficient for main, console, networking
   and world workers. `Thread.start` cannot simply be ignored. Wall and monotonic
   clock rules must be defined from standard EVM context and/or committed inputs;
   the host must not make scheduling decisions based on Minecraft logic.
5. **Filesystem:** a path/permission/locking model and persistent virtual files for
   `eula.txt`, `server.properties`, logs, JAR resources, datapacks and world files.
   Reads/writes and ZIP parsing happen under EVM control. World generation before
   `Done` is a major gas/storage workload and may not be skipped or replaced by a
   host-generated “ready” world unless a separately declared pre-existing-world
   milestone is deliberately chosen.
6. **Network:** Java/Netty bind/channel/event-loop behavior. The no-client goal
   removes packet traffic, not the bind and worker initialization that the real
   startup path performs. Auth/telemetry/outbound behavior must be explicitly
   denied or modeled without credentials, never opportunistically performed by
   the host.
7. **Logging/output:** guest formatting and Log4j calls produce a deterministic
   byte/event stream. A host UI may decode and print that stream but cannot search
   the JAR, fabricate `Done`, or decide that an earlier banner means success.

## Minimum honest headless boundary

The smallest defensible first boundary is a deterministic **virtual machine
namespace**, implemented in ordinary EVM contracts/state:

* a persistent VFS and immutable raw-artifact store;
* a cooperative scheduler and explicit virtual clocks;
* a virtual TCP namespace where bind reserves `(address,port)` and creates queues,
  but no OS listener or client is attached;
* empty/nonblocking console input, a guest-produced log sink, and explicitly
  disabled credential/outbound-network sources; and
* committed configuration, locale and entropy policy.

A successful virtual bind is not an OS bind and must be labeled as such, but it is
more honest than returning success from a no-op: ownership, collision, close and
queue state are represented and enforced. A later external adapter may map opaque
socket bytes to transactions and display logs. It must not parse classes, execute
Java, advance world generation, choose task outcomes, or synthesize responses.
No listener or adapter is required for the first marker milestone.

Standard configuration choices are not classfile patches, but they still change
the workload and therefore must be pinned (including `nogui`, world seed/type,
port/address, online mode, difficulty and view distance). No credentials are part
of the first target. The eventual EULA input must be an explicit user-authorized
VFS item, not embedded in code or silently generated.

## Stock-EVM resource and deployment design

The accepted interpreter artifact at commit `c6b6584951aa426212deb085e3d3ee359bf1fc46`
is 135,652 bytes, SHA-256
`cf68495083ebcd2df93f6d676e16afad87192a3401bd743a0301d805d5a8cd15`.
It exceeds EIP-170's 24,576-byte deployed-code limit. The inspected preflight base
`8ff8eecc126305861714096fb82077534a0c1325` contains an integrated M5d-a candidate
artifact of 152,506 bytes, SHA-256
`3ae672871debc1d6528749abea3c3783b7d7f11987cc28fe619e283cc833ba03`;
that does not make M5d-a accepted.

`jvmevm.run` calls upstream `core/vm/runtime.Execute`. That helper creates a
temporary account and directly calls `State.SetCode(address, code)` before EVM
execution. It does not pass through CREATE/CREATE2 and therefore bypasses proof of
EIP-170/EIP-3860-compliant deployment. Gas measurements also exclude deployment,
transaction intrinsic/calldata costs and persistent-state continuation.

A compliant route must use only existing EVM instructions and protocol limits:

* split the generic interpreter into independently deployed modules, each below
  EIP-170, with explicit CALL/DELEGATECALL interfaces and no class-specific code
  generation;
* store immutable artifact/class/resource bytes in many size-compliant code pages
  or storage/calldata/blob-backed chunks, and have EVM code validate commitments,
  parse ZIP/classfiles and request chunks. Host chunk transport is opaque data
  availability, not parsing or evaluation;
* use size-compliant factories/initializers under EIP-3860 and account for every
  deployment and call cost;
* turn the VM into a deterministic resumable state machine. At each finite-gas
  boundary, serialize frames, heap, statics, class-init state, scheduler queues,
  VFS/world state and pending I/O into contract storage or commitment-checked
  pages, then resume in a later transaction; and
* make continuation boundaries semantically invisible: no lost exceptions,
  duplicated side effects, reordered threads, reset statics, fake clock jumps or
  marker emission before committed world/VFS updates.

This is architecturally possible with stock EVM primitives but economically and
operationally unproven. Contract call depth, per-transaction/block gas, memory
expansion, storage costs, state growth and artifact deployment may be harder
limits than opcode coverage. No opcode, precompile, gas rule, consensus code,
EIP-170/EIP-3860 limit, host-Java service or privileged state insertion may be
relaxed to obtain the marker.

## Pinned-upstream audit

Against geth v1.16.9 commit
`95665d5703e1023995a0ff93e4ce9eb77e8a59bd`, the preflight-base diff contains no
changed path under `core/vm`, `core/state`, `core/types`, `consensus`, or `params`.
The SHA-256 of `core/vm/runtime/runtime.go` is the same at pinned upstream and the
preflight base: `822478c26ca1eb4313ab83da97576cbc4d93397f8f1cfddebbffcb6afd7d9c26`.
The fork adds the interpreter, runners, fixtures, tools, Make targets and docs
outside those consensus/EVM paths. This supports “no geth EVM/consensus source
change” for that exact diff; it does not prove deployment, another client's EVM,
a live-chain transaction, or Minecraft execution.

“Original, unmodified EVM” acceptance therefore requires both this source audit
(or equivalent multi-client bytecode execution) **and** an ordinary deployment
and invocation path obeying active fork rules. Present `runtime.Execute` evidence
alone is insufficient.

## Dependency order after atomic M5d-a

Do not reorder or split M5d-a to chase Minecraft: first accept its complete frozen
fault/handler/unwind/init contract and all historical gates. Then proceed in
bounded, dependency-ordered slices:

1. **Standard-deployment prototype:** size-compliant generic modules plus a small
   persistent continuation workload, establishing the stock-EVM architecture
   before the interpreter grows further.
2. **Java launch/data core:** void/String-array main, scalable class table, general
   descriptors, Strings/builders/boxing and expanded heap/state persistence.
3. **Raw JAR/resource core:** EVM-side ZIP directory parsing, DEFLATE, manifests,
   resource streams and commitment-checked paging; prove on small trusted JARs.
4. **Throwable and library core:** M5d-b Throwable construction/APIs, common Java 8
   exceptions, collections, I/O abstractions and exact guest error behavior.
5. **Dynamic Java core:** method handles/`invokedynamic`, reachable reflection,
   class loading/service discovery and remaining verifier/linkage behavior.
6. **Concurrency core:** monitors, synchronized methods, atomics, cooperative
   fibers/executors and deterministic continuation-safe scheduling.
7. **Virtual platform:** VFS/locking, clocks/entropy/locale, logging and virtual
   network bind, each first accepted with pure-Java micro-workloads.
8. **Pinned dependency ladder:** run unchanged small upstream libraries needed by
   1.12.2, then bounded server entry/EULA-stop/progress checkpoints. Static
   reachability findings may prioritize work but may not remove runtime paths.
9. **Startup-complete acceptance:** only after explicit EULA/config authorization,
   execute the unchanged pinned server through the exact `Done` logger call and
   retain artifact/state/trace/gas/continuation evidence.
10. **Optional connectivity:** external byte adapter, protocol/login and tick-loop
    milestones are separate and cannot retroactively be claimed by `Done`.

Each slice needs finite per-transaction gas, total continuation/storage ceilings,
negative tests proving unsupported paths fail rather than fall back, and preserved
historical JVM/EVM differential gates. No slice count is a full-JVM or Minecraft
claim.

## Bounded local evidence

All probe outputs are ignored and are not part of the commit:

* `build/java-diff-mc-startup-preflight/metadata/version_manifest_v2.json`
  (275,339 bytes; SHA-256
  `f8cc72846df1c5a41733d044c74eaae5a0f547fd91e26056f915b89a07097194`;
  the mutable aggregate manifest digest is evidence of this retrieval, not a
  Mojang version pin used above).
* `build/java-diff-mc-startup-preflight/metadata/1.12.2.json` and
  `build/java-diff-mc-startup-preflight/metadata/1.21.5.json`: exact official
  records and hashes above.
* `build/java-diff-mc-startup-preflight/metadata/server-download.html` and
  `build/java-diff-mc-startup-preflight/metadata/eula.html`: static terms-page
  snapshots with the hashes recorded above.
* `build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar`
  and `build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.21.5.jar`:
  exact ignored artifacts and hashes above; each download was capped at 128 MiB.
* `build/java-diff-mc-startup-preflight/inspection/minecraft_server.1.12.2.inventory.json`
  (SHA-256 `143dbae233d5938c5579145bab080e7b40f98c0f66c8727a7d222963a4952478`)
  and `build/java-diff-mc-startup-preflight/inspection/minecraft_server.1.21.5.inventory.json`
  (SHA-256 `bf9b301fb46d2d5dfd4ebefcaff29f225d06268e5c69e112123e2be72247ac73`).
* `build/java-diff-mc-startup-preflight/inspection/1.12.2-nz.javap.txt`
  (SHA-256 `1d3e203a142c13cec17a51a955efea972cc315ec74fa1fff724ac6085933c936`)
  and `build/java-diff-mc-startup-preflight/inspection/1.21.5-aqr.javap.txt`
  (SHA-256 `8b5dcbcca0d091fdf9d77b6aca0f8bd695528daadbe93b3f85d67d79a8137239`).
* `build/java-diff-mc-startup-preflight/inspection/upstream-evm-audit.txt`
  (SHA-256 `49088a656b42f9faa565d6cf61b4bd57c60c4673b41b2e6637a4025352d53eaf`).
* `build/java-diff-mc-startup-preflight/static_probe.py`: bounded to 128 MiB per
  JAR, 64 MiB per ZIP entry, 100,000 classes and 512 MiB aggregate class bytes.
  It only reads ZIP/class structures and Code bytes.

The current static inventory is a broad over-approximation and obfuscated method
names limit source-level interpretation. A future bounded call-graph/resource
preflight can refine reachable priorities, but only actual in-EVM execution can
establish the startup marker. Nothing in this proposal proves server success.
