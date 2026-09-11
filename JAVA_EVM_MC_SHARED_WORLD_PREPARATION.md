# Shared-world class coordinator preflight preparation

Status: **PREPARATION, NOT PRODUCTION FROZEN/ACCEPTED**. Follow the parent class
bridge findings in JAVA_EVM_MC_CLASS_BRIDGE_PARENT_PREFLIGHT.md. The EVM byte path
works on generated Java8 fixtures, but the old experiment used a private DI0 StateDB
pointer and did not publish bridge/Java state. Parent fixed its separate prototype's
single-read4096-vs65536 mismatch; preserve the real earlier failure.

## One bounded implementation/measurement task

ONE Sol/high worker; no Fast/priority/spawning/peer/main/push/settings changes.
Own ONLY JAVA_EVM_MC_SHARED_WORLD_PREFLIGHT.md and
 evidence/java-evm/class-bridge/shared-world-preflight/** plus own ignored
 build/java-diff-mc-shared-world-preflight-*/. No production/accepted/core/Make/ABI/
quota/opcode/gas changes. No original server/JAR/class execution or handling; use
trusted GENERATED fixtures only. Key sources/fixtures/reports/hashes/reproducers
in tracked scope, not /tmp-only. Completion is not acceptance.

Build the smallest disposable coordinator and self-owned raw EVM driver, with no
reflection/unsafe/private fields from an existing Session. The driver owns its
StateDB/triedb/database normally and ABI-packs calls to EXACT accepted AS0/ZI0/DI0
runtimes. It does NOT parse ZIP/classes, inflate bytes, build Huffman tables, copy
class plaintext to a JVM call, or install decoded pages. It may install ONLY the
exact accepted LOCAL VFS0a engine once at its frozen address under an explicitly
recorded LOCAL initial-state operation; inspect its accepted nonce/account/context
setup. This is not EIP170 deployment. All resource/coordinator/pages ordinary CREATE.

Suggested coordinator contract to measure (not an invitation for extra APIs):

- Nonzero fixed constructor owner; immutable-by-interface STORAGE registry of1..4
  FINAL DI0 resources sharing one accepted final index. Constructor takes decoder
  references, exact raw names and root assertions; validates exact code/name/index/F/
  phase, rejects duplicates, empty classes and aggregate size>65536. No setters,
  owner transfer, decoded-byte import, callback, upgrade, dynamic rebind or hidden
  comparator. Constructor-bound ordered package avoids driver-only resume binding.
- Package root computed IN EVM over owner/controller/engine and dependency identities,
  ordered class name/resource references/roots/sizes and total size, with distinct
  preflight domains. Requested root is an assertion, not a package import. Define
  class order explicitly; do not claim equivalent roots for reordered packages.
- One JVM instance per coordinator (bind its ID explicitly). Start chooses an entry
  from the registered classes and an existing supported method/args; no raw classes
  enter start/resume. Derive JVM internal name exactly from rawName sans .class;
  opaque matching, no general Unicode/path/ClassLoader normalization claim.
- Each start/resume checks fixed package and code bindings, performs<=4096B DI0
  FINAL read fragments (max19 across four images totaling65536), assembles actual
  EVM-produced classes, calls exact unchanged VFS0a ABI. The JVM independently checks
  declared names/link/code. Do not use source-counted pretend reads or host copying.
- Fixed package/instance/owner and existing VFS0a epoch/checkpoint CAS. Transport
  checkpoints are the previous successful EVM-issued bytes. No result/trace bytes
  from a failed call; no forged checkpoint, no treating gas-aware units as exact.
- Existing engine/bootstrap/image4/65536/checkpoint1MiB/heap/VFS/seeds/argument and
  instruction budgets stay unchanged. Seed inputs may be empty in the minimal proof;
  future VFS scope must be explicit. No logging/platform emulation shortcuts.

## Measurements required before a production freeze

1. Genuine shared world with accepted controllers/engine and no private-session
   attachment. Record installation and CREATE identities and exact fixed hashes.
2. Real cross-class Java call/link/init on two generated classes in ONE ZIP and one
   index; actual result differs with inputs. Independent Java8 oracle is test-only.
   Engine head owner must be the coordinator, not host EOA or resource owner.
3. Same fixed package with direct/q1/q7 grouping: actual Java counters/result and
   terminal machine/VFS roots; frame/epoch checkpoint roots may legitimately differ.
4. Wrong package/ref/name/F/owner/CAS/non-FINAL/class-name mismatch refuse through
   real contracts without accepting caller bytes. Keep positives strict and errors
   exact; a low-gas EVM failure is not a semantic rejection/pass.
5. Aggregate1..4 image count and exact65536/+1 boundary using parent ignored-attribute
   fixtures as needed. Preserve DI0 max262144 separately. Paging proof must include
   >4096 and cross-page sizes, not only tiny classes. Validate every returned length.
6. Per-successful-mutation commit/reload to memory and real disk (trie+code sync and
   atomic manifest publication). Include LOCAL engine installation as an explicit
   initial-state phase, not gas-charged EVM CREATE or hidden data-page SetCode.
7. Actual new-process continuation after Java start with EVM checkpoint and live
   coordinator/engine anchors, then at least one further resume and FINAL reopen;
   no re-CREATE/reinstall/host reparse. Distinguish package/resource/VM/trie roots.
8. At least one direct EVM failure after state writes and old-root retry, plus an
   actual post-sync publication failure/old-root restoration. Do not mask the EVM
   rollback claim by manually restoring first; diagnostics never become authority.
9. Pinned wrapper compiler0.8.30 opt200 viaIR Cancun metadataoff; ordinary100Mgas/30s,
   explicitly labeled1B/120 boundary only; whole20min4GiB watchdog. Controller<=24576,
   complete init<=49152 INCLUDING maximum constructor args. Engine remains accepted
   oversized LOCAL code, not counted against small controller deployment as a trick.
10. Record actual code/gas/call counts/real syncs/wall/RSS/disk and exact reproducible
    hashes. No universal performance/Java conformance/full-loader claim from fixtures.

If shared-world installation, existing ABI/ownership/caps, output framing or final
publication pose a blocker, preserve it and propose a bounded explicit refinement;
never change accepted profiles quietly. Parent independently replays then defines
production ABI/root/schema/transport and separate implementation ownership.
