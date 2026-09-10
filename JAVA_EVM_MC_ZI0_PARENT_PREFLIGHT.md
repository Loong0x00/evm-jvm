# MC-ZI0 parent preflight replay and remaining freeze gate

Status: **NOT FROZEN / NOT ACCEPTED**. Worker9012fe450 integrated as2e76ab392.
AS0 byte store64ea6b62f remains accepted; VFS0a72aa13f15 remains accepted JVM/VFS.
No ZIP inflation, Java resource/ClassLoader/main, Minecraft/EULA/listener/Done claim.

## Independent replay

Parent copied the ignored prototype to `build/java-diff-mc-zi0-parent/original/`,
rebuilt it with pinned solc0.8.30/optimizer200/viaIR/Cancun/metadataoff, and compared
its full JSON artifact byte-for-byte with the delivery. Source SHA
26575cac482b05946796aa60b6c712e53560c114b0eea1e9456a92498d485254 matched.
All25 original outcomes reproduced: watchdog0.213s/21590016B sampled group RSS,
exit0/no limit, `/tmp/mc-zi0-parent-replay.{log,json}`. This is a view-only toy
parser over genuinely EVM-created/sealed AS0; NOT persistent indexing evidence.

Parent separately rehashed the official JAR and reran the raw static inventory;
output exactly matched the worker inventory.20554 entries and2100796 CD bytes are
static sizing evidence, not an EVM-generated catalogue. No server JAR execution
or distribution occurred. The EVM fixtures are generated synthetic bytes only.

## Independently reproduced gaps

`build/java-diff-mc-zi0-parent/adversarial/` adds13 proposed-refusal probes and a
successful dense-signature control. Against the original runtime:

- Nine unsupported flag bits4,7,8,9,10,12,13,14,15 were accepted. The prototype's
  mask0x61 checked only three bits, rather than the proposed allowlist0x080e.
- Method0 accepted bits1 and2, which the proposed profile reserves for DEFLATE.
- The final unsigned descriptor could end INSIDE the central directory. A generated
 1311608-byte case makes CEN's first12 bytes match a missing descriptor: statedCRC
 0x02014b50,compressedSize0x00140314,plainSize0x00080808. No inflation is involved.
 The EVM accepted count1 and an index root at69092559gas. Data end was CD start,
 but record end was CD start+12. Earlier overlap checking covered only a NEXT LOC.
- A ZIP64-locator marker in the20-byte prelude to an otherwise empty classic ZIP
  was accepted. This needs an explicit preamble/structural-marker decision, not an
  unqualified promise to reject every ZIP64 record. Arbitrary preambles are already
  allowed by the positive page/tail controls. Searching arbitrary names/payloads for
  signatures would conflict with opaque-name/data semantics and is not a fix.

Failures retained in `/tmp/mc-zi0-parent-gaps-before.{log,json}` (exit1,0.320s,
26542080B sampled RSS). These are toy-prototype/profile gaps, NOT bypasses of
accepted AS0 or VFS. Raw compressed bytes/CRC claims remain unverified by design.

The original max-window69.11M sample was not a worst-case proof: an empty archive
with65532 comment bytes densely repeating EOCD signatures used **78012818gas**
and still succeeded under100M. Freeze must use adversarial discovery measurements,
not treat one fill pattern as an upper bound.

## Scoped parent correction / unresolved control

Parent changed only an ignored COPY of Solidity: exact allowed-flag mask, method0
option-bit refusal, and `recordEnd <= cdOffset` after descriptor parsing. New toy
runtime6594B/init6639B; no production or accepted EVM artifact changed.

All25 original cases still pass (0.214s/22933504B). Twelve definite parent refusal
probes now reject; the dense-signature control still succeeds. The ZIP64-prelude
case is explicitly recorded as an unchanged ACCEPTED OBSERVATION pending a policy
choice, NOT counted as a corrected refusal. The14-case corrected observation run
passes0.316s/27004928B. Logs `/tmp/mc-zi0-parent-corrected-{replay,gaps}.{log,json}`;
source/artifact/driver under `build/java-diff-mc-zi0-parent/{corrected,corrected-gaps}/`.

The worker error formatter printed Bad(n) for any36-byte error, including bubbled
AS0 errors. Its negative oracle also accepts any call error. This is not an exact
error/rollback gate. Production/persistent preflight must distinguish selectors and
unexpected OOG from semantic rejection, and inspect only committed successful state.
No reverted/OOG trace may become a published index or recovery source.

## Next authorized bounded persistence preflight

ONE Sol/high worker, no Fast/priority/spawn/push/settings/peer/core edits. Own only
`JAVA_EVM_MC_ZI0_PERSISTENCE_PREFLIGHT.md` (aim<=200lines) and ignored
`build/java-diff-mc-zi0-persistence-preflight/`. Parent is not concurrently writing
Solidity. This remains disposable measurement code, not a production freeze.

Start from the corrected parent copy; preserve originals/failure cases. Build a
small real EVM persistent scanner with constructor-only binding/owner, discover,
CAS-checked scan1..64, finish, and final-only entry/lookup. Use the proposed2-slot
record/hash index (specify ALL packed widths/offsets), full byte equality, and an
EVM-derived index root. Head may expose staged rolling diagnostics, but that is
not a published/final index: resolve the proposal's ambiguous 'only public after
finish' phrasing. Fixed runtime identity across owners/stores is preferred, no
setters/rebinding/upgrade/host index installer. Distinguish transport assertions
from EVM authority. Consumer calls must bind accepted AS0 code/address/sealed root.

Measure actual SSTORE/trie/per-mutation durable publication and real new-process
mid-index/sealed reopening. Commit/reload memory mutations too; raw-loop dirty-slot
pricing is not production transport pricing. No batching disk commits or host page/
metadata catalogue authority. Opaque Go ABI/trie transport only. AS0 remains ordinary
CREATE pages/controller; host SetCode/host-extracted entries are forbidden.

Required feasible measurements: generated20554-entry target-shaped archive and
full32768-entry capacity;64-entry batch with simultaneous256-byte names/1024-byte
valid extras/1024-byte comments; empty archive; q1 versusq64 roots for identical
binding/state setup; duplicates across batches; failed-batch rollback/retry; early
lookup/finish and wrong cursor/root/owner/binding refusal; full-byte lookup and
cross-page ranges. Cover original25 and parent12 definite refusals, dense EOCD
signatures, plus a clearly specified ZIP64 locator/preamble policy with normal raw
name/payload controls. Do not scan arbitrary entire payloads for signatures.

Generated inputs may use trusted host ZIP/flate builders only as fixtures, never
as parser authority. Do not upload/run the official JAR in this preflight. Its
static inventory only chooses finite bounds. No inflation/CRC/plain-class claims.
Keep32MiB AS0/8192 pages/4096 reads,32768 candidate entries/4MiB CD/64 scan units,
100M30s ordinary/1B120s boundary and20min4GiB unchanged. A failed cap is a blocker,
not permission to silently increase it. Report code/gas/trie/disk/RSS/time/binding
and restart evidence, and unresolved ABI/errors/publication limits before parent
independent replay and exact ZI0 freeze. Commit only the new note.
