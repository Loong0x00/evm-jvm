# MC-AS0 preparation: immutable EVM artifact bytes before JAR/class loading

Status: **parent direction plus bounded measurement authorization, not an AS0
implementation freeze or acceptance**. VFS0a accepted72aa13f15 remains unchanged.
Entry-frontier note b4dbb2408->bf4b8e15f/8cf53f25b is static, not a main trace.

## Parent verification and next dependency

Parent independently rechecked the official1.12.2 JAR30222121B/SHA256
fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e.
MinecraftServer/bn/tr/um=34977B; adding LogManager makes5classes/46841B. Both Log4j
provider metadata904B and log4j2.xml1124B use ZIP method8. Java8 javap reconfirmed
MinecraftServer.<clinit> PC0 calls LogManager before File(usercache.json) PC6..16.
This was STATIC inspection only. No JAR execution, EULA, listener or real Done.

Do not replace logging or guess the SimpleLogger branch to bypass that work.
The current4-class/64KiB eager input cannot supply this dependency graph, and a
30MB JAR cannot fit the accepted64KiB mutable VFS or1MiB continuation blob.
Implementing one more isolated library is not sufficient to cross this frontier.

Split the proposed CD0 into dependency-sized pieces:
1. **AS0:** immutable, opaque, EVM-owned artifact byte storage/read commitments.
2. Bounded EVM ZIP directory/resource lookup and DEFLATE stages on trusted fixtures.
3. EVM lazy class identity/load/link/init continuation, then reference/void launch
   and the actual workload-needed platform/library subset.
These are separate stages; AS0 alone is neither a JAR reader nor JVM class loading.
No accepted budget/checkpoint format is expanded or reinterpreted for this work.

## Initial AS0 design to measure

Prefer one immutable artifact per store instance/controller, with sequential upload,
owner/cursor checks, fixed declared length, explicit sealing, and bounded reads only
from the sealed artifact. No public overwrite/upgrade, host page installation,
host class catalogue, class-name/offset hints, or host ZIP extraction authority.
Controller and byte pages execute/use ordinary unchanged EVM behavior and accounting.

Candidate limits to measure, not yet freeze:32MiB total (fits the pinned30.2MB JAR),
8192B pages (at most4096), <=4096B reads crossing page boundaries, finite100M/30s
ordinary and1B/120s boundary calls,20min/4GiB external measurement watchdog.
This immutable store is separate from VFS0a's64KiB mutable files and1MiB checkpoint.
A later JVM profile must bind the store's code identity and sealed content root.

Prefer EVM-created immutable data-code pages with STOP prefix, if measurements support
it; compare storage-byte costs. Each8KiB page fits ordinary EIP170/initcode bounds.
Do not install child data pages from Go or modify CREATE/EXTCODECOPY/gas/precompiles.
An oversized LOCAL controller install, if necessary, remains an explicit profile,
not proof of whole-JVM standard deployment. No need to modularize old JVM instructions.

EVM must compute ordered page/content commitments including lengths and indexes,
bind read bytes to its immutable issued pages, reject wrong owner/cursor/length,
and roll back page creation/root/position/events on a failed call. Seal only at the
exact declared length. Host transports raw bytes and persists EVM code/trie/head
state, never provides execution decisions or recovers publication from OOG traces.
Measure real new-process persistence feasibility; do not call a Go byte map a store.

## Hash/proof distinction — do not silently overclaim

For the FIRST AS0 byte-store stage, select EVM-computed opaque page/content commitments
as authority over the bytes it received. An owner chooses the input artifact, just as
owners choose raw class bytes in existing profiles. A supplied hash/catalogue is not
accepted in place of computing the content commitment from actual EVM-received bytes.

The host may SHA256-check an opaque input file against the published Minecraft pin
as transport/test integrity, but that is NOT EVM verification of the official whole-
JAR SHA256 and must never be labeled as such. AS0 must not expose an unverified
caller-supplied SHA256 field as authenticated evidence. Measure whole-input SHA256
precompile costs versus streaming alternatives and report the separate unresolved
proof choice; do not raise gas limits or hand SHA compression to a host evaluator.
A future stage may implement streaming EVM SHA256 if required. This deliberately
narrows the frontier worker's combined SHA256/ZIP/inflate/lazy-loader recommendation
instead of pretending those features are already present in an opaque byte store.

All future named class/resource results must be derived/proved by EVM against the
committed raw ZIP/compressed bytes. Host-extracted classes are not production
ClassLoader authority. Neither page commitments nor off-chain input pin checks imply
that EVM parsed ZIP, inflated DEFLATE, loaded a class, entered main or started a world.

## Disjoint measurement assignment

One Sol/high worker, no Fast/priority/spawning/push/settings/core/accepted-profile
writes, owns ONLY JAVA_EVM_MC_AS0_PREFLIGHT.md (aim<=200lines) and ignored
build/java-diff-mc-as0-preflight/. Implement a real standalone EVM page-store
prototype there, measure runtime/page sizes, upload/read/seal gas, code-page/cursor/
content-root behavior, exact limits and rollback, and export/reopen evidence where
bounded. Use trusted generated byte/ZIP fixtures only; never execute Minecraft or
upload copyrighted JAR bytes to GitHub/network/chain. Full-size generated binary
controls may be used to measure capacity without distributing the server.

Report actual hashes/commands/limits and the scope of each proof. Parent independently
replays measurements and freezes AS0's exact API/root/state/durability contract only
then. Any infeasible limit is a measured blocker, not permission for a silent increase.
