# Parent cost attribution: selected-method scratch allocation

Status: **verified read-only COPY experiment; NO optimization/profile promotion**.
Worker59cbf4c2c integrated0ffca56ab. Parent independently compiled the same sources
with pinned debug products, replayed seven cases, checked exact gas/roots and added
read-only memory/free-pointer observations. Accepted code/quotas remain unchanged.

## Corrections to evidence strength

The worker's three direct-call numbers reproduce, but its run had no completed
sampled process-group RSS watchdog. Its scripts computed a reconciliation residual
without asserting it, and comparison.json was a retained assertion record rather
than an executable comparison procedure. Parent now checks all fields and every
reconciliation. The worker's timeout note is a narrative, not a full captured
failure transcript; preserve it as such.

A zero named-source-map bucket does NOT exclude a semantic phase:68.31% of the dense
ordinary trace used whole-contract/ambiguous spans. In particular, no returned
checkpoint does not prove the commit guard was never entered. Parent only reports
unambiguous source buckets and actual compiler debug-entry hits. Other-source IDs
are checked rather than accidentally interpreted against the Solidity AST.

## Exact replay and gas accounting

Normal and debug compilation produce identical runtime bytes: VFS292968B/SHA256
4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f;
coordinator3792B/SHA2561fc9cc6be252cc9256e280fb2a5669fbdd6a92a03955639d83ddc5173f365363.
Compiler0.8.30,opt200,viaIR,Cancun,metadataoff. Debug output adds source maps, AST,
functionDebugData and optimized IR only; no Solidity source, EVM semantics or input
is changed. All Java bytes still come from EVM AS0/ZI0/DI0 FINAL reads.

Seven traced receipts match the parent untraced capacity receipts exactly for gas,
result/exception/revert, before/after/published roots, head, slice/counters, logs,
checkpoint length/hash, budget and quantum. Wall time is deliberately excluded.
PC decoding skips PUSH immediate bytes. Each known PC's opcode matches its pinned
runtime. All child calls have zero value; forwarded gas is subtracted from caller
opcode costs, never added twice with child work. Sum(exclusive PCs)=root receipt;
per-address PC costs also equal inclusive frame costs minus direct children. The
sum of forwarded gas equals all child entry-gas observations. All seven reconcile
with zero residual. No independent StateDB refund allocation is inferred.

Dense ordinary:74874471 gas, excluded forwarded gas7051035439; its exact rejection
is LC0ControlError7, NOT OOG. Boundary direct124505990 and boundary resume127622437
remain explicitly1B-only observations. q1 first succeeds50952310, subsequent ordinary
resume refuses77090888. No failed trace becomes a checkpoint or Java outcome.

## Memory and allocation measurement

The observer reads current EVM memory length/stack operands before each opcode;
for memory accesses/copies/KECCAK/RETURN/REVERT it computes the charged expansion
using the unchanged formula C(w)=3w+floor(w*w/512). All recorded growth reconciles
EXACTLY to C(peak words) for the VFS frame in every case. This is EVM scratch
memory, NOT JVM guest heap quota or host process RSS. Free-pointer writes are
observed at MSTORE(0x40), not assumed from class byte size.

Compiler functionDebugData gives:
- `allocate_and_zero_memory_struct_struct_Selected` entry146431;
- next emitted helper `allocate_and_zero_memory_array_array_struct_Selected_dyn`
  entry146622. The recorded allocator region[146431,146622) is bounded by actual
  JUMPDEST/return-JUMP instructions and its optimized IR is retained.
- Selected has23 fields; the emitted helper increases free pointer by736B.
  Actual entry counts, observed736B allocation histogram and allocator-region
  free-pointer increments reconcile exactly. This identifies a real generated
  allocator, not a speculative assignment of the ambiguous source-map bucket.

| case | receipt gas | peak VFS memory B | expansion gas | Selected allocations | allocator-region PC gas |
|---|---:|---:|---:|---:|---:|
| padded262144 |7879725|863648|1503635|6|14970|
| BigEntry90874+caller |48451006|3137568|19070722|2557|15515685|
| dense181969 ordinary refusal |74874471|3735616|26966934|2556|20582167|
| dense1B direct |124505990|5957824|68261157|5111|57200064|
| dense q1 first |50952310|1612352|5109652|3|13899|
| dense q1 ordinary resume refusal |77090888|3865120|28856527|2557|21551842|
| dense1B resume |127622437|6086784|71235880|5112|59135003|

At the1B direct completion,5111 allocations consume3761696B just for these Selected
structures. The source creates `new Selected[](methods.length)` lazily per class,
but Solidity eagerly constructs each array element—even methods not executed.
Repeated parser reads also cost gas; this result does not assign every ambiguous
PC to Selected or claim that removing this allocation saves all expansion gas.
Memory expansion is cumulative/quadratic, so an optimization must be measured.

## Next narrow experiment

Prioritize a COPY-only sparse/lazy Selected-table representation over a broad parsed
class cache/demand-loader rewrite. Preserve exact method indexing, loaded flags,
initializers, virtual/interface/static/constructor paths, reference/field caches,
exception handlers, restores and all guest-visible state. No cap/gas/COMMIT_RESERVE
change. Prove unloaded/loaded slot alias safety, ideally using a type-safe indirection;
any shared empty sentinel or assembly allocator needs explicit immutable-sentinel
and layout proof. No source-specific shortcut for BigEntry or method names.

Different engine code changes code/config/package roots; do NOT disable their
binding merely to claim equal roots. Compare actual guest results/counters/VFS and,
where schema permits, opaque serialized machine payload bytes independently of the
code-bound envelope. Within each variant, direct/q1/q7 and relocated-process roots
must agree appropriately. Retain original ordinary refusals and label1B reference
runs. No expected output can be inferred from a failed trace.

## Parent gates and provenance

Fresh full source/debug reconstruction plus seven observed calls:
**419.030s/936648704B/exit0**,20min/4GiB sampled watchdog.
Independent fresh-world replay using that exact rebuilt/hashed executable, strict
analysis/vet/protected-code checks: **58.513s/522731520B/exit0**, separate watchdog.
These are TWO explicit gates, not one invented combined capture. An earlier second-
replay attempt failed before EVM because copyfile omitted executable mode; retained
final-replay.log/watchdog record it. copy2 fixed only that harness issue, fresh path.

Evidence: evidence/java-evm/preparation-cost/parent-59cbf4c2c/. Source/byte pins, raw
aggregate receipts, compiler debug products/IR, strict analyzer, log failures and
reproducers retained. No millions-of-op rows. No accepted runtime change, original
Minecraft Java/startup/EULA/listener/world/Done or push.
