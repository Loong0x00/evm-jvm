# MC-DI0 decoder ordinary-budget performance preflight

Status: **PREFLIGHT PASS, NOT FROZEN / NOT ACCEPTED** at base `36ad7d298`.
This is a new Sol/high optimization measurement of the disposable DI0 decoder, not
completion/retry of the provider-blocked Terra task. Accepted ZI0/AS0/VFS profiles,
all gas/size quotas, production code, core EVM, and settings are unchanged. No
official JAR was inflated; no ClassLoader, Java/Minecraft execution, EULA, listener,
world, or Done marker exists.

## Change measured

Starting source was persistence-preflight `DI0OutputPages.sol` SHA256
`d117856b...ab54be5b`, runtime 12,885B SHA256 `64342a79...a9b3a`, artifact
`3344a2ab...f4a9`. The new disposable source keeps all byte/range/tree/lookup/CRC/
output-page decisions in EVM and changes only decoder work reuse:

- one bounded AS0 reader per step call, refilled by EVM in <=4096-byte reads, and one
  persisted input-cursor save per call rather than per action;
- fixed literal/distance codes decode directly from RFC1951 canonical ranges;
- the code-length canonical table is built once in memory per dynamic header;
- dynamic literal/distance canonical counts and ordered symbols are built once per
  header and persisted for later calls/fresh-process resumes, instead of allocating
  and sorting fresh arrays for every token.

Every dynamic header rewrites all count entries. Empty-distance headers clear all
distance counts; stale ordered entries are unreachable. Stored and fixed modes do
not consult dynamic tables. A dynamic->fixed->differently-ordered-dynamic fixture and
a separate dynamic-header fresh-process chain passed. No gas-aware early yield or
work-unit contract revision was needed: requested units remain exactly 1..128.

## Artifact and resource bounds

Pinned solc0.8.30 optimizer200/viaIR/Cancun/metadata-off produced:

- source 17,687B, SHA256 `f42a3f2d...589197`;
- runtime 14,278B, SHA256 `8bfe1a72...d25165`, Keccak
  `9b58338c...bb8abf` (below 24,576B);
- init 16,487B, SHA256 `3177fc22...8531a`; complete init with a 256-byte name
  16,871B (below 49,152B);
- artifact JSON SHA256 `ac27469d...7d085b`; unchanged 33-function ABI hash
  `54e3019b...43b00`; ordinary DI0 CREATE range 72,156..3,157,564 gas.

The combined strict gate used explicit `timeout 1200` and virtual-memory
`ulimit -v 4194304`, finished in 40.747s, and sampled 194,138,112B peak process-group
RSS. The main 37-case run was 10.833s/74,520KiB process rusage. The existing 90,309B
persistence database was 1,412,581B; added dynamic-cache persistence was 195,799B.
No 1B call was needed. All calls used the unchanged ordinary 100M cap.

Maximum observed DI0 step call across all strict runs was 80,681,628 gas for the
32-empty-dynamic-block q128 fixture. The largest original-37 call was 38,434,025 gas
(history wrap). Maximum step-gas sum was 1,748,466,926 across 10,197 separate q1
calls for the 262,144B same-binding case; its q128 sum was 1,337,295,970 across 80
decode calls (112 calls including 32 page publications). Aggregate sums are not
single-call caps. Maximum page CREATE call remained 7,492,356 gas.

The 262,144B same-binding q1/q128 pair had 10,165 work actions, 32 pages, output SHA
`97a2fc55...bc00c9`, rolling root `6b79e0f4...f725cc`, final root
`b563b20f...022c85`, and final state root `b0d076ba...09d17f` in both runs. Full
staging stayed bounded at 8192 words; output remained 8192B/page, <=32 pages,
32KiB lookback, 32-byte match copies, and final reads <=4096B.

## Strict semantic and budget gates

All original 37 generated persistence/output cases passed with their old expected
successes/failures, exact CRC/length/range checks, page verification and roots.
Fixed and dynamic same-binding q1/q128 output/work/input/page/state equality passed.
The direct post-output-write call now OOGs at an explicit 200,000 gas, commits no
work/output/root, and retries in 74,900 gas. The late 7.4M page CREATE failure leaks
no child/page/root and retries to the same child. CRC guard, owner/work/publication
CAS, phase, unit and page-bound controls retain exact `DI0Error(uint256)` selector
`0xb8c7a310` and exact codes. Public mutation/view selectors remain step
`0xe1723741`, publish `0x1e00cc39`, read `0xbd0c067e`, page `0x8e75ab08`.

The parent 22-case set now passes its strict gate. The three former Java8-valid OOGs
are real successes at 100M: deep full tree q128 max 6,374,704 gas; empty32 q64
80,681,454; empty32 q128 80,681,628. They are not malformed-input outcomes. Seven
additional cases cover alternate deepest-symbol order, dynamic/fixed/dynamic cache
replacement, fixed reserved literals 286/287 (exact code15), and fixed reserved
distances30/31 (exact code16), for 29 total. All256 fixed literals and Java8-accepted
length284+extra31=258 remain successful. Java8u504 Inflater/ZipFile/ZipInputStream
agreed on all 18 positives and rejected all 11 malformed fixtures; terminal unused
bits/full trailing-byte DI policy from prior evidence is unchanged.

Same-artifact, same-binding q1/q128 output, CRC storage, input cursor, work, page
tuples, final root and state root matched for deep tree, empty32, changed 32KiB
history, and exact256KiB output. Exhaustive q1..q128 sweeps also matched for deep,
empty32 and mixed dynamic/fixed/dynamic. Their maxima were respectively 6,374,704,
80,673,890 and 5,754,215 gas/call. No valid OOG was accepted as a semantic result.

The original durable sequence still has 60 independently synced publications and
four distinct process stages: 20->48 VERIFIED, ->49 one page, ->60 FINAL, ->60 read,
with 90,309 exact bytes/12 checked pages. A second real four-process chain resumed a
persisted dynamic table after its header: 20->24 VERIFIED, ->25 one page, ->26 FINAL,
->26 read; output/work/pages and code/root pins passed. Every mutation commit/reload,
trie+code sync, manifest file fsync/rename and directory fsync remains enabled.

## Boundary and remaining blockers

This passes the requested benign generated-fixture **performance preflight only**.
It does not freeze DI0 ABI/errors/root domains/storage layout/transport or accept the
unaccepted DI0-only 256KiB proposal. Production still needs parent-independent replay,
final ABI/diagnostic selection, namespace/manifest/nested-link checks, concurrency,
rename-poison recovery and full publication-failure hardening. Accepted AS0 32MiB/
8192-page/4096-read, ZI0, VFS, 100M/1B, 1MiB checkpoint and all older quotas remain
unchanged. Evidence, sources, commands, hashes and strict verifier are tracked under
`evidence/java-evm/di0/budget-preflight/`; historical failed reports remain intact.
