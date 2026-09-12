# Selected-table allocation: next COPY-only optimization preflight

Status: **bounded experiment authorized, NOT a production change/acceptance**.
Evidence: JAVA_EVM_MC_PREPARATION_COST_PARENT_PREFLIGHT.md. Exact runtime debug-entry,
IR and free-pointer observations identify736B Selected allocations for every slot
of `new Selected[](methods.length)`. A5111-allocation dense boundary call spends
57200064 gas in that emitted allocator region; its broader VFS memory expansion is
68261157 gas. This is a concrete target, not attribution of every ambiguous source
span or proof that optimization already works.

## Scope

Start from the verified capacity-baseline8/262144 COPY, not accepted CB0/VFS source.
Only transient selected-method table representation/allocation/access/restore may
change. Keep method/class indexing and lookup, bytecode/predecode/verification,
initialization/constructor/default/interface/exception semantics, reference/field
caches, bootstrap38, all guest heap/fields/frames/args/VFS/checkpoint limits and
COMMIT_RESERVE unchanged. No parsed-class cache, demand loading, new ABI/root kind,
new host data authority, or source-specific method/fixture optimization.

Prefer typed lazy indirection: allocate a cheap per-method slot, then instantiate
one real Selected only when that slot loads. An immutable shared empty sentinel or
memory-safe assembly table is a possible experiment only with explicit layout and
alias proof. Do NOT let modifying one loaded method mutate another unloaded/loaded
slot; handler-class caches and all mutable Selected fields must stay isolated.
Audit all root/initializer/static/special/virtual/interface/constructor creation,
access and `_restoreSelection` paths, not just the large static fixture.

Copies only under fresh ignored builds, narrow archived source patch/recipe/hash.
New exact engine/coordinator code pins/isolated namespace and LOCAL initial route,
no accepted identity/CREATE/standard-chain claim for the oversized engine. All
resource/controller/data/output pages ordinary CREATE; Java input remains opaque
ZIP -> EVM AS0/ZI0/DI0 FINAL -> <=4096 EVM reads. No host class parser/inflater/
catalogue/evaluator, raw-class execution input, private Session/StateDB access,
reflection, class-page installation or failed-trace recovery. Compiler0.8.30,
opt200,viaIR,Cancun,metadataoff, runtime<=320KiB.

## Required checks

- Cold and same-process/disk/reopened execution for the exact padded256KiB,
  BigEntry90874 and BigPair181969 fixtures, input sensitivity, actual gas and
  allocation count/bytes/peak EVM memory. Old ordinary failures remain retained.
- Ordinary100M30s first; any preauthorized1B120s OLD reference run is labeled
  BOUNDARY ONLY, never an ordinary rescue. Demonstrate whether dense direct/q1/q7
  now progresses; report failure instead of weakening budgets/reserve.
- Different code/pins change config/package/instance/machine roots. Do not disable
  binding for a false equal-root claim. Compare actual Java result/exception/
  counters/VFS, and where the unchanged envelope schema permits, exact opaque
  serialized machine payload bytes against successful same-quantum old reference.
  This byte comparison is transport evidence, not host interpretation of Java.
  Within each variant, direct/q1/q7 roots/epochs/current checkpoints must obey the
  normal profile; no raw equality across grouping of code-bound envelope/trie roots.
- Loaded/unloaded slot alias negatives and at least multiple distinct called methods,
  <clinit>, constructor, virtual/interface/default path and caught/uncaught handler
  cases. Cold/warm/reopen behavior must agree. Invalid method/descriptor/refusal
  precedence and checkpoint tamper/old-root recovery stay intact.
- Exact class/input/page/checkpoint boundaries remain; no hidden slot capacity or
  integer overflow shortcut. Actual controller read traces still match selected
  FINAL resource bytes. Event/outcome/receipt/hash/publication checks are unchanged.
- Fresh build/debug byte checks, independent Java8 TEST oracles, strict verifiers,
  actual processes,20min4GiB sampled group gate, scoped TMPDIR. Archive all failures
  and logs before cleanup; essential source/evidence not /tmp-only. Parent must
  independently rebuild/replay before any promotion or merge into another copy.

One semantic Solidity writer at a time. MR0 harness work may proceed read-only on
its compiled candidate separately; do not alter MR0 concurrently. No original
Minecraft Java/JAR handling, startup/EULA/listener/world/Done or push in this task.
