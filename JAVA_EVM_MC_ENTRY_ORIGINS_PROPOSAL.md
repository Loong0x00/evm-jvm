# Entry origins and `main(String[])` — bounded design proposal

**Status: design only, based at `ea1fa2c8a9628e23c8024d6d835cba70a553f6b7`.** This proposes no code, artifact, ABI, quota, transport, profile, or acceptance change. It does not handle an official JAR or execute Java/Minecraft. The endpoint remains unchanged: genuine guest vanilla 1.12.2 startup to the pinned `Done` marker, superflat first, on a finite LOCAL artistic installation—not Java SE conformance or a standard deployment claim.

## Decision

**Rank 1 — B0: a separately specified direct `main` root, first exercised only on a small generated, single-origin package with an EVM-created empty `String[]`.** It is the smallest *origin* preflight because it needs no foreign launcher source at all: the selected root class comes from the one authenticated archive already supported by CB0. A future target class can therefore remain an entry in the untouched target artifact. B0 has a real new root descriptor/entry schema and must be a new, measured LOCAL profile; it is not an assertion that the current exact-int root can launch `main`.

**Rank 2 — A0: constructor-fixed multi-origin package, also generated-only.** This is legitimate and may later be useful for tools, adapters, or a deliberately supplied guest launcher, but it is a larger transport/identity/persistence change than B0. It must authenticate every resource's source archive; “two DI0s happen to have different roots” is insufficient. It is not a way to insert a class into, or re-identify, the official JAR.

**Rank 3 — no cheaper legitimate route is known.** Raw class injection, host catalogues, code installation, or a repacked JAR evade precisely the provenance question. They are ruled out below. No cost comparison is claimed: the concurrent cost-attribution work must measure the dense-package preparation/resume blocker before any capacity or caching conclusion.

The rank is narrowly about resolving the **launcher-origin** problem. It does not claim B0 is a shorter path to Minecraft: static facts still show the target's first classes, library/platform surfaces, class discovery and capacity exceed current CB0 boundaries. The accepted 4-resource/65536-byte package can be used only for the small generated B0 proof, not to conceal those deficits.

## Evidence status and facts

The source and document hashes used for this design snapshot are retained in `evidence/java-evm/entry-origins/design/SHA256SUMS`. References below are classified deliberately:

| statement | classification | basis |
|---|---|---|
| A generated `int Launcher.run(int)` created guest `String[]`, invoked another guest `void main(String[])`, and read post-call state | **measurement** | parent main-entry preflight: empty result 341; content control includes NUL/surrogates; ordinary direct/q1/q7 and durable reopens passed. |
| The current selected CB0 package has 1..4 resources, aggregate <=65536, and all resource bindings must share one FINAL ZI0 index/root | **source fact** | `CB0ClassCoordinator.sol` constructor, plus accepted CB0 review. |
| Current VFS0a root selection accepts only all-`I` arguments and `I` result | **source fact** | `_loadRoot` calls `_isExactIntRoot`; it rejects `([Ljava/lang/String;)V`. |
| Current CB0 transport exposes `Start(package, entryAt, entry, []int32, ...)` and `Resume`, stores one AS0/index route and one package/Java head in its manifest | **source fact** | `cb0/session.go`, `cb0/cb0.go`. |
| A direct root can be made small enough, preserve checkpoint identity, and remain ordinary gas | **unknown** | not measured. The earlier wrapper proof does not measure a new root descriptor, main-root allocation, or direct-main codec. |
| A two-origin package is affordable or preferable to B0 | **unknown** | no measurement. Do not infer it from byte count, aggregate gas, or the 8/256KiB prototype. |
| MinecraftServer's pinned main/artifact facts and direct early dependencies | **static fact**, not execution | existing STATICMC/startup documents; not re-inspected here and not authority for a future loader. |

The parent capacity baseline is the binding negative context: an experimental 8-resource/256KiB input change still refused a **generated** dense three-class 181969-byte package at ordinary gas with `LC0ControlError(7)`; direct/q7 failed and q1's surviving epoch-1 checkpoint could not resume at ordinary gas. Only separately authorized 1B boundary calls completed it. This proposal neither promotes that copy nor recommends an 8/256KiB profile. It makes no claim about the expensive operation, and does not duplicate the cost attribution work.

## Why current CB0 cannot honestly combine launcher and target archives

### Exact constructor/package binding

The accepted coordinator takes one ordered array of DI0 decoders, raw names, asserted index roots, resource roots, and a package assertion. For every decoder it checks FINAL phase, name hash, index root, resource root, size, owner, and duplicate decoder/name. At the first binding it records `commonIndex/commonIndexRoot`; every later binding must equal both or it reverts `CB0Error(13)`. It then checks that one ZI0 is FINAL, has that root and owner, and calculates:

```text
R0 = H(P, coordinator, owner, engine, engineCode, DI0Code, ZI0Code, count)
Ri = H(R, R(i-1), i, decoder, H(rawName), indexRoot, resourceRoot, size)
Package = H(P, Rfinal, total, commonIndex, commonIndexRoot)
Instance = H(V, coordinator, Package, salt)
```

with ABI (not packed) encoding and current CB0 domains. `_loadAll` repeats the same one-index/root route validation on every Start and Resume, then reads each FINAL DI0 resource wholly inside EVM in <=4096-byte fragments. `start` derives the entry class only by stripping `.class` from the selected raw name and sends the assembled `bytes[]` to the unchanged VFS0a ABI. Its seed array is empty.

Thus a generated `Launcher.class` in a launcher ZIP and `TargetMain.class` in a target ZIP cannot both be bindings of this coordinator. A DI0 resource carries an EVM-derived `index`, `store`, `content`, `indexRoot`, raw-name hash and final root, but CB0 deliberately collapses the package to one `commonIndex`. Supplying a caller-computed root cannot override this: the constructor recomputes and compares it.

### Root, class assembly, and checkpoint binding

At present VFS0a computes `artifact = keccak256(abi.encode(DART, rawClasses))`, includes it in config/checkpoint/anchor state, reparses the supplied complete bundle on Resume, and `_prepare` assigns user classes before bootstraps. Its selected root must be an exact static int root: every argument descriptor is `I`, and return is `I`. `main:([Ljava/lang/String;)V` is a valid Java method descriptor but is not a current root.

CB0's public Start is correspondingly int-only. Its Java result must have one valid nested engine event and a nonempty EVM-issued checkpoint <=1MiB; its disk manifest binds the current state root, fixed routes/code hashes, package root and Java-head checkpoint hash. Reopen checks bounded metadata before opening LevelDB, then re-reads EVM heads/routes. `ReadCheckpoint` returns only the current published Java head. These are important constraints for either route: a root/argument change cannot create a parallel host checkpoint format or leave a caller-selected archive unbound on Resume.

### Public-session and ownership limits

`cb0.Session` is public transport over its own ordinary EVM world, but it contains one `as0Address`, one `indexAddress`, one ordered decoder route and one coordinator/package/instance field. `CreateDecoder` is contiguous, capped at four, and stops after coordinator creation. Its documented public path is AS0 append/seal -> one ZI0 discover/scan/finish -> DI0 -> `CreateCoordinator` -> Start/Resume. `Head` gets route/class identities from EVM; Go may perform bounded encoding checks but is not a ZIP/class catalogue authority. The accepted source permits `SetCode` only for the explicit pinned LOCAL engine installation in atomic initialization; it is not a class transport or an authorization for a second code path.

## Route B0 — direct `main` root from one authenticated origin (recommended)

### Minimal scope

B0 adds a separately named root kind rather than changing existing `start` behavior. Its sole positive workload is generated Java 8 in **one** opaque ZIP/index/AS0 origin containing a public static `main(String[])`; no wrapper class is present or needed. The EVM selects the entry's existing resource binding, creates a non-null zero-length guest `String[]`, invokes exactly `main:([Ljava/lang/String;)V`, and records ordinary void termination through the normal EVM checkpoint/event/publication path.

The first B0 call accepts **no textual host arguments**. That avoids falsely treating host strings as guest String objects. A later, separately approved argument stage would need an exact bounded byte encoding (including UTF-8/MUTF-8 policy, length/element caps and error precedence) whose EVM code allocates every guest `String` and the array. It must not be smuggled into B0 as `bytes[] rawClasses`, a Go-created object array, or a host callback.

`main` returning void is not a synthetic `int 0` return. The result schema must distinguish at least:

* running/yielded (with epoch/checkpoint);
* ordinary **void terminal** (no fabricated Java int result);
* terminal genuine Java exception (existing typed result conventions); and
* EVM/validation/publication failure (existing gas-only/revert distinctions).

No B0 API may turn the VM's checkpoint into a root-result message or accept a caller checkpoint different from the EVM anchor. The old exact-int root selector, ABI encoding, receipts and test expectations remain byte-for-byte separate.

### Proposed shape for a later freeze (not an API authorization)

A least-privilege schema is a tagged root descriptor held in the coordinator and carried into the engine, not an overloaded interpretation of `entry`:

```text
RootSpecV1 = {
  schema: 1,
  kind: MAIN_EMPTY_STRING_ARRAY,
  entryAt: uint8,
  method: exact ASCII "main",
  descriptor: exact ASCII "([Ljava/lang/String;)V",
  argsCommitment: H("MC-main-empty-args/v1")
}

StartMainV1(packageRoot, RootSpecV1, maxJvmSteps, maxInternalSteps)
ResumeMainV1(packageRoot, expectedEpoch, expectedCheckpointRoot,
             checkpoint, maxJvmSteps, maxInternalSteps)
```

The fixed package root and selected `entryAt` still select the EVM-derived raw-name/class binding; `entryClass` is derived inside EVM exactly as CB0 does today. `RootSpecV1` is validated before Java execution and included, together with root kind and `argsCommitment`, in a new domain-separated config/root commitment. The engine creates the array, not Solidity calldata/Go. The anchor/checkpoint prelude carries the descriptor/version and argument commitment so Resume rejects a root-kind, method, descriptor, package, or arguments substitution.

A real implementation may choose different selector names or place the descriptor in a new coordinator. It must retain the same semantic invariants: no ambiguity with int roots; exact public/static/non-abstract method selection; descriptor exactness; no reference/void root accepted accidentally; and normal EVM ownership, CAS, event and durable-publication behavior. Because the existing interpreter's root check is exact-int, this is a new engine/root ABI and profile decision, not a documentation-only adapter.

### Identity and persistence requirements

B0 retains the existing single-origin CB0 package formula for its first proof. The origin identity is therefore the EVM-validated ZI0 FINAL controller/root, whose constructor binds an accepted AS0 controller, sealed EVM content commitment and declared length; DI0 additionally binds its index/store/content/name/record and publishes a FINAL resource root. The host may upload opaque generated ZIP bytes and use EVM `Head` identities for assertions, but cannot provide extracted class bytes or a catalogue.

The new root configuration must be in both (1) the EVM engine anchor/checkpoint config and (2) the coordinator/transport head and durable manifest validation inputs. A durable resume in a fresh process must load the prior published trie root first, revalidate the exact coordinator/index/DI0/engine code and route identities from EVM, then submit the EVM-issued blob plus epoch/CAS. It must not use the manifest, a static fixture name, or an external classfile to reconstruct root arguments.

### B0 generated gates

All are proposed gates, not completed checks. Each EVM call is ordinary <=100M gas and 30s; the complete guarded run is <=20min/4GiB. B0 has no 1B call.

1. **Positive single-origin void root.** A generated class has `<clinit>` and a nontrivial `main(String[])` body that branches on `args == null` and `args.length`, mutates private static state, then checks that state before normal void return. The verifier asserts the known generated Java-step/internal-step outcome and terminal EVM root/checkpoint; it does not add a second int root or decode private checkpoint state to manufacture an observation. A Java 8 oracle is test-only. The guest code must establish that the received array is non-null and length zero.
2. **Direct/q1/q7 and disk.** Compare terminal machine/VFS/package/resource roots where grouping semantics permit, retain each EVM checkpoint SHA and EVM Keccak, check exact nested checkpoint event/root/epoch/counters, and reopen actual new processes with no installation/CREATE. Include a pending q1 root then Resume through the same B0 descriptor.
3. **Root negatives.** Reject wrong root kind/schema, wrong entry slot, wrong method name, `()V`, `(I)V`, `([Ljava/lang/String;)I`, non-public/non-static/abstract/native main, a null-array test-only mutation, malformed argument commitment, and int-root/B0 selector confusion. The positive empty-array result must not be reproducible by treating null as empty.
4. **Binding negatives.** Wrong package assertion, wrong DI0 final/index/name/resource binding, target class declaration mismatch, source/order mutation, and stale epoch/checkpoint all fail without a success checkpoint/root/logs. Reuse only known generated fixtures and public EVM APIs.
5. **Persistence/publication negatives.** Preserve a real pre-publication failure and a post-rename poison/reopen case; require gas-only versus revert behavior as current CB0 does. A changed root descriptor/args commitment or root config on resume refuses before Java execution. Verify current terminal void head is retrievable and a stale checkpoint is not.
6. **Boundary nonclaims.** Keep 1..4/65536 and existing 4096-byte DI0 paging. Explicitly show class five and aggregate 65537 remain their existing refusal source, rather than silently running an 8/256KiB copy.

A static ABI/source audit can check selector separation and descriptor routing before EVM execution, but it is not a B0 positive gate. A host Java oracle only compares generated behavior and never supplies executable bytes or outcomes.

## Route A0 — fixed multi-origin package (legitimate but second)

### What it must mean

A0 is not “allow several indexes.” It defines a finite ordered list of **origins** and makes every resource binding name its origin. The minimal generated proof uses two independently EVM-indexed archives: `launcher.zip` with `Launcher.class`, and `target.zip` with `TargetMain.class`; the guest launcher stays unchanged and calls real void main as already demonstrated. This verifies a cross-origin class package while retaining the old exact-int root semantics. Neither archive is repacked; each retains its own AS0/ZI0/DI0 EVM identities.

A future official-target use would put the target class/resource bindings only under a target-origin commitment whose AS0 content commitment/length and ZI0 FINAL root identify the untouched target archive. A generated launcher must remain under a distinct generated-origin commitment. The final package is a composite; it must **not** be described as the target JAR's hash, size, contents, or identity.

### Proposed identity model

For a new A0 coordinator, constructor-fixed origin records should include at minimum:

```text
OriginV1 = (originOrdinal, zi0Address, zi0CodeHash, owner,
            as0Address, as0CodeHash, as0ContentCommitment, as0Length,
            zi0FinalRoot)
ResourceV1 = (resourceOrdinal, originOrdinal, di0Address, rawName,
              di0IndexRoot, di0ResourceRoot, plainSize)
OriginRoot = H("MC-origin/v1", coordinator, OriginV1)
PackageRoot = H("MC-multi-package/v1", ordered OriginRoot[], ordered ResourceV1[], total)
InstanceId = H("MC-multi-vm/v1", coordinator, PackageRoot, salt)
```

All fields are ABI encoded and recomputed in EVM. The precise domains/schema must be frozen with the artifact; the names above only identify required separation from `MC-CB0/*`. For every origin, EVM validates code hashes, owner, ZI0 FINAL root/phase, and ZI0's AS0 store/content/length binding; for every resource it validates DI0 FINAL phase, owner, index address/root, store/content against its origin, name hash, final root and size. Duplicate origin index/store-content pair, duplicate DI0 address, duplicate raw class name across **all** origins, out-of-range origin ordinal, zero roots and excess totals reject. `_loadAll` repeats those checks before every Start/Resume and reads only the pinned decoder in <=4096-byte chunks.

This adds a useful missing explicitness to current CB0's common-index assertion: the source identity is not a host `archiveName`, local SHA file, or a caller root. It is the EVM-linked AS0 sealed content plus ZI0 final index and DI0 binding. If a future full-artifact official SHA-1/SHA-256 claim is wanted, it needs a separately specified EVM-verifiable whole-artifact commitment procedure; AS0's content root alone is not represented as a whole-file official SHA proof.

### A0 public/persistent contract requirements

A0 needs a new session/manifest namespace rather than overloading CB0's single AS0/index fields. Its public setup API must create/load each origin through ordinary EVM AS0/ZI0/DI0 operations and expose only bounded EVM Head data. Its constructor is fixed once: no post-start origin append, rebinding, owner transfer, lookup fallback or ambient “current archive.” The manifest carries only bounded routes and pins; EVM revalidation remains authority before/after reopen. Checkpoint artifact/config binding must use the composite package root, ordered source identities and root descriptor so source swap/reorder rejects on Resume.

A0 must bound **both** origins and resources separately. A two-origin/2-resource generated test does not authorize a large origin count, arbitrary class discovery, or a target-JAR catalogue. The exact maxima, constructor ABI size and runtime bytes are unknown until measurement and must not inherit the disposable 8/256KiB values. A conservative first experiment can retain total resources <=4 and aggregate <=65536, permitting a two-class generated cross-origin proof without a capacity claim.

### A0 generated gates

1. Positive two-origin `Launcher.run(int)` -> target `void main(String[])` with guest-created array; no host raw classes. Assert launcher and target have distinct EVM AS0 content/ZI0 roots and the composite package differs from each single origin.
2. Same direct/q1/q7/memory/disk/new-process checkpoint and publication controls as B0, using the current exact-int root. Verify all origin/resource identities on each slice and exact prior-root chaining.
3. Refuse cross-origin source swaps, same resource root under wrong origin ordinal, decoder from target paired with launcher index, wrong AS0 content/length, changed index final root, reordered origins/resources, duplicate raw class name across origins, duplicate decoder, owner mismatch, non-FINAL source, absent origin, and stale composite package assertion. Failed calls produce no usable slice/blob/root.
4. Retain current class/resource caps and prove their unchanged +1 refusals. Do not turn a target-origin class list into a trusted host catalogue or test only an archive label.
5. Fault/reopen probes cover a source route or composite-package manifest mutation before DB open, normal old-root recovery, and postrename poison/reopen. A reopened process performs no engine reinstall, controller re-CREATE or source rebind.

## Disallowed “cheap” routes

| route | why it is not legitimate |
|---|---|
| Repack the official JAR with `Launcher.class`, or claim an augmented ZIP retains the official JAR hash/size | byte identity changes. A composite package can be honestly named composite, never the exact target JAR. |
| Pass `bytes[] rawClasses`, a Go class array, reflection/private Session state, a StateDB pointer, decoded DI0 output, or a bootstrap injection to Start | it bypasses EVM AS0/ZI0/DI0/class assembly and makes host code a class authority. |
| `SetCode`/CREATE a class page or wrapper to make it appear resource-derived | CB0's one LOCAL engine installation is not resource installation. DI0's EVM-created FINAL pages are the only present resource route. |
| Host ZIP extraction, name->offset map, class hash catalogue, host ClassLoader/JVM execution, or a static official inventory as a runtime lookup authority | static facts and test oracles are not EVM authentication or Java execution. EVM must establish index/name/range/decoded bytes. |
| Add launcher bytecode as a new fixed bootstrap or hardcode a result/banner | it hides executable guest code and does not invoke the target's unchanged `main`. It cannot establish genuine Done. |
| Treat B0's empty args as permission to pass host strings later | array and all elements must be constructed/decoded in EVM with a separately frozen codec and checkpoints. |

## Dependency order and stopping rule

1. **Choose B0 or A0 explicitly; do not combine them.** Recommended next preflight: B0 generated single-origin direct-main/empty-array. Freeze no artifact until a fresh parent replay confirms its root/result/checkpoint/persistence schema.
2. If a supplied wrapper is truly required later, run A0 independently with two small generated origins. It does not substitute for B0 and does not unlock a target JAR.
3. In parallel but not folded into either route, complete cost attribution for the dense ordinary-gas refusal. Do not infer a cache, demand loader, cap increase or 1B operating budget beforehand.
4. Only after an origin/root design and an independently measured capacity/loading design exist may a separate proposal consider untouched target-artifact entry selection. It still needs real class discovery/loading, transitive link/init, and workload-needed platform surfaces.
5. Only a separately authorized unchanged-artifact guest execution can approach the pinned superflat startup marker. It requires the genuine level-preparation return and guest-generated logger bytes, not an A0/B0 return value.

## Explicit nonclaims

This design made no EVM calls and ran no generated Java. It did not upload, inspect, extract, decode, execute, or otherwise handle an official JAR/class. It does not accept an EULA, create configuration/world files, open a listener, generate a world, run Minecraft, or produce `Done`. It does not approve an ABI/profile/quota/artifact change, direct main implementation, multi-origin implementation, demand loading, capacity promotion, host fallback, or 1B normal call.
