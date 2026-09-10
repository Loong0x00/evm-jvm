# VFS0a implementation preflight after IOE0 acceptance

Status: **bounded preparation, not a VFS implementation freeze or acceptance**.
Accepted dependency is IOE0 `8f29f8c`, runtime233286B SHA256
`507ed54d56d4cbe5e559013fbf5a3e598d75a28c0ffe33735573f646eac659a0`.
The earlier VFS0a proposal (`012b277`) is useful but does not yet pin its eight
bootstrap images or demonstrate whole-runtime size/native-bind/codec costs.

The intended next capability remains genuine EVM-owned File/FIS/FOS operations,
not host file execution, a generic Java-SE migration or Minecraft startup. No MC,
JAR execution, EULA files, listener or real Done is authorized by this preflight.
Keep at most two Sol/high agents, no Fast/priority; parent integrates/verifies.

## Parent oracle findings requiring precision before freeze

Trusted `ParentFileOracle.java` in ignored `build/java-diff-mc-vfs0a-parent/` was
run in separate owned temporary working directories on Java8 and21. Both showed:

1. `new File("missing//child/")` stores path `missing/child`; FNFE uses this normalized
   lexical path. VFS0a must not append a suffix to the unnormalized input String.
   Ordinary Java constructor Code should implement the narrow slash-collapse/
   trailing-slash rule. Dot/parent canonical resolution belongs to the EVM filesystem
   operation and is distinct from File's lexical normalization.
2. With writer A at offset3, writer B truncates the same file, then A writes68:
   file bytes become `0,0,0,68`. No seek API is needed to produce this zero-filled
   gap. A cursor may exceed current inode length after another descriptor truncates
   it. Reads then return EOF without resetting that cursor. The proposed "no hole"
   simplification cannot reject these ordinary sequential multi-descriptor cases.
3. Native FNFE suffixes depend on host locale. Default environment produced Chinese
   ENOENT text; explicit LC_ALL=C/LANG=C produced `No such file or directory` on
   both JVMs. A deterministic virtual English/C-locale message profile must be
   explicit, not accidentally taken from the host locale. Java wrapper Code, not
   Go/native canned exception objects, must construct its selected guest messages.

Logs: `/tmp/mc-vfs0a-parent-java{8,21}.log` and `-c.log`. These are host-JVM TEST
oracles only; no contents became production VFS bytes.

Further precision: read-only files may be opened for INPUT; only OUTPUT is denied.
Treat the proposed64KiB aggregate as ALL logical regular-file bytes including seeds
and read-only contents, unless the parent explicitly freezes another bounded rule.

## Construction-state question

File/FIS/FOS are new capabilities and pinned constructors may acquire native state
before storing their handle/path field. Retain genuine pending-bind gaps; do not
pre-store fields or rerun open/truncate on resume. A custom Object constructor can
publish partially constructed receivers under the accepted VM profile. Before a
freeze, choose either honest support for such default/escaped File/stream states or
an explicit no-callback Object profile for NEW File/stream-family allocation. Do not
silently skip callbacks or alter unrelated IOE0 objects/Throwable constructors.
After a successful stream super-constructor, a failing user subclass may leave a
bound descriptor and unreachable object; no-GC/no implicit-finalizer rules must be
explicit. Source and active-frame validation cannot mistake generic integer locals
or a foreign constructor for a pending descriptor's owner/bind phase.

## Authorized disjoint preparation

1. **Wrapper worker** owns ONLY `JAVA_EVM_MC_VFS0A_WRAPPERS_PREFLIGHT.md` (aim<=220
   lines) plus ignored `build/java-diff-mc-vfs0a-wrappers/`. Produce candidate eight
   source/class images, exact public/private-native ABI/fields and getter/error/path
   Code rules with hashes and trusted Java8/21 oracle evidence. No production edits.
2. **Kernel worker** owns ONLY `JAVA_EVM_MC_VFS0A_KERNEL_PREFLIGHT.md` (aim<=220lines)
   plus ignored `build/java-diff-mc-vfs0a-kernel/`. Measure a genuinely executed
   EVM filesystem/codec prototype: seeds, paths, inodes, independent cursors,
   create/truncate/append/zero-fill/read/close, readonly and quota rules. Include
   pending-bind/owner/canonical framing recommendations and real gas/byte sizes.
   Standalone kernel size or an ABI probe is NOT an integrated Java/filesystem proof.
3. Parent owns this note, final scope/schema/bootstrap pins, independent probes,
   Make/guide, later integration and acceptance. Do not add a third verifier agent.

Neither worker may spawn/push/change settings/core/accepted artifacts or peer files.
No production Java or filesystem logic is delegated to host code. Finite100M/30s
ordinary,1B/120s boundary EVM calls; whole preflight20min/4GiBRSS watchdog. Preserve
all old budgets and opcode semantics. Report runtime233286B's remaining28858-byte
headroom honestly: additive size estimates do not prove a <=256KiB integrated
artifact. A real size/gas blocker requires reviewed scope/module design, not a
silent ceiling increase. The1MiB checkpoint and64KiB VFS-byte proposal are tiny LOCAL
limits, not a world-capacity/startup-cost guarantee.
