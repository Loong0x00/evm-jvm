# ZI0 integrated candidate — parent findings before acceptance

Status: **UNACCEPTED**. Runtime549e0e809/119935802 integrated ab1a0b88e/d10d9700d;
Go transportacd40faa3/8d076105f integrated f0f4ea441/14c565614. Runtime9177B,
complete init9937B, runtimeSHA74ea23889368b3381843e39bb2caf53a66de8dbfdb3dc58dc4a066c97a33d7a3.
No Minecraft/inflate/ClassLoader or accepted-profile changes.

The Go delivery had ONLY stub-based compilation/vet and no behavioral tests.
This does NOT satisfy the frozen harness work or acceptance. Parent tested against
actual embedded production artifacts and retained failures IN REPO under
`evidence/java-evm/zi0/production-14c565614/`.

## Reproduced integration failures

1. Fresh disk Open never calls createAS0. It writes marker/manifest with empty root
   and AS0 address0, returns success and zero Creation fields. Memory NewMemory DOES
   CREATE and works. Parent FreshOrdinaryCreate/disk fails; the real two-entry ZIP
   disk pipeline fails on append's missing event after calling address0. This is a
   live normal-path defect, not just a malformed metadata probe. No disk success
   claim can be made from the stub compile.
2. validateABI accepts an extra event, despite frozen ABI having zero events. Parent
   ExactABINoEvent fails. Exact20 entries must mean constructor+error+18functions,
   not just the function map count.
3. Parent TEST-only copied-state probes also reproduce the missing AS0 Head guards:
   pageCount2^32 truncates to0, cursor1/pageCount0 before EOF is accepted, and a changed
   owner is returned despite session binding. These are malformed copied-state
   validation gaps, NOT demonstrated live EVM owner bypasses. head-before.{log,json}
   and parent tests retain all three failures.

Parent real artifact two-entry upload/seal/CREATE/discover/scan/finish/lookup works
in MEMORY only so far. Failing parent tests are committed in
`jvmevm/artifactstore/zi0/parent_test.go`; do not change their expectations to pass.

## Mandatory repair/review scope

Before acceptance, use the REAL runtime dependency, not synthetic stubs or source
fallback. Implement all frozen transport tests and close the missing behavior:

- Fix fresh disk initialization with real AS0 CREATE and publication before return;
  Creation fields/codes/nonce/root must agree with memory and new-process reopen.
- Validate actual combined-artifact schema/compiler/settings/source/code hashes,
  accepted AS0 dependency pin, limits and absence of immutable/link substitutions.
  Check complete init len including64-byte args. No runtime-text fallback aliases or
  self-asserted manifest pin authority. Add negative asset/ABI-shape tests.
- Head decoders currently mostly type-convert, without canonical AS0/index phase,
  range/cap/root/binding checks. AS0 pageCount uint64->uint32 can truncate in altered
  state. Require canonical bounded metadata and errors (no successful empty decoding
  on nil decode error or unchecked type assertion panic). Keep actual ZIP decisions
  EVM-only: no host parsing/file catalogues or payload offsets.
- Test publication from actual AS0/ZI0 state after commits, old-root recovery,
  CreateIndex address reset versus postrename poison, reload errors and gas-only
  publication failure. Do not expose the page/root/address/logs of failed publish.
- Tests must cover all frozen16 groups proportionately, including full20554 durable
  every-call chain,32768/exact4MiB CD, q1/q64 roots, high-offset32MiB, multi-phase
  process reopen, full-byte guards/geometry/CAS/owner/EOF, metadata-beforeDB, links,
  no adoption/wipe/redeploy, positive success or exact expected semantic error.
  Self-report or a previously accepted AS0 driver is not actual ZI0 session evidence.

Parent independently rebuilt the real production Solidity artifact byte-identically,
ran its runtime tests and full runtime replay: exit0,19.107s/300404736B sampled RSS.
All7 runs/54 controls/12 probes matched worker EVM outputs. This is evidence for
runtime behavior using its standalone replay driver, NOT successful operation of
this new Go Session's broken disk path. runtime-{repro,tests,full-replay,report} files
are archived alongside the parent failures. Runtime source17317B SHA78329d1610c0ba180c7e267989bf36190a9d9eb536020acce42234066a94a2ae;
init9873B (+64args=9937), runtime9177B pins remain unchanged.

No production Sol changes are currently required by these findings. Parent made the
runtime testdata wrapper require an explicit workspace instead of a default /tmp
location; the original artifacts and emitted EVM bytes are unchanged.

## Authorized follow-up worker

ONE Sol/high worker owns only `jvmevm/artifactstore/zi0/**` excluding runtime/** and
parent_test.go; it repairs Go and supplies real-artifact tests/README. Parent owns
independent tests/docs/Make/gitignore/runtime review/integration. No concurrent peer
writes, no Fast/priority/spawn/push/settings/core/accepted-profile changes. Key
results must be retained in the owned package (or described in its README), never
only in /tmp; disposable build workspace may be ignored. Max100M30s ordinary,
1B120s explicit boundary,20min4GiB gate unchanged. Do not stop at stub compilation
again: report actual real-artifact suite results and any remaining blockers honestly.
