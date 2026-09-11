# DI0 parent replay and explicit bounded-yield decision

Status: **implementation freeze ready, NOT DI0 accepted**. Budget workere738ad221
integratedeaf473946. No accepted runtime/core/AS0/ZI0/VFS change. No official-JAR
inflation, Java/ClassLoader/MC/EULA/listener/Done. All new inputs are generated.

## Independent optimization replay

Parent independently reconstructed the compiler/driver/fixtures from tracked sources.
Artifact SHAac27469d5aaf531c9bebc49e78899bc4507f42eabee281d8609a0e4c3b7d085b matched.
37-case replay,29 tree/Java8 cases,4 same-binding pairs and3 exhaustive1..128 sweeps
passed the strict verifier against FRESH reports, not the worker's archived reports.
Combined parent watchdog42.597s/183877632B sampled groupRSS, exit0/no20min4GiB limit.
The per-call reader/refill and per-block canonical table reuse are genuine EVM work;
fixed codes remain in EVM and dynamic tables survive actual process restart.

Evidence is under `evidence/java-evm/di0/parent-e738ad221/`.

## Further valid-stream counterexample

The repeated-header fixture had32 empty dynamic blocks, only64 actions total. Parent
extended it to64 bit-contiguous empty dynamic blocks, which consumes128 actions.
Java8 and Go both accept it. With the optimized BUT unmodified worker runtime:
q1 succeeds (max2701544gas), q8 succeeds, q64 succeeds(max80637388), but **q128 still
OOGs at100000000gas**, with no work/output/final publication. The new strict gate
exits1; `headers64/` preserves the actual failure and Java8 result. Sweeping all
quantums on a64-action stream was not proof of an entire128-action batch bound.

## Explicit work-semantics refinement (not a gas-cap increase)

Parent added a four-line rule to an otherwise unchanged DISPOSABLE optimized copy:

```
for each requested action while DECODING:
    if at least one action has completed AND gasleft() < 25000000: stop this call
    execute the next bounded action
    increment work
save the actual bit/byte cursor when still DECODING
```

`units` now explicitly means an UPPER BOUND1..128, not a promise to consume all
requested actions. Actual progress comes from the EVM work/cursor/output getters.
There is no host retry from speculative state, no gas increase and no hidden reduction
of the accepted input domain. The first action is still attempted: an underfunded
call can genuinely OOG/revert, but no successful zero-work response is manufactured.
The25M reserve bounds whether to START another action; it is not fake paid gas or a
change to geth opcodes. Per-action work remains finite: bounded header/tables, one
symbol+extras, or up to32 copied/stored bytes. No arbitrary whole block action.

The source remains a preflight copy, using preflight roots. Production gets separate
v1 domains and exact ABI/transport/schema from JAVA_EVM_MC_DI0_PLAN.md. No optional
caller knob may disable this guard in the production profile.

## Parent checks after refinement

All37 original cases,29 tree/Java8 cases, four previous same-binding pairs and prior
three sweeps passed again. The64-block input now succeeds with q64 and q128 using
3 positive-progress calls,128 total actions, max75586130gas. q1 still uses128 calls;
all are actual successful runs with identical final decoded result semantics.

Parent further tested6 same-binding q1/q128 pairs and FIVE exhaustiveq1..q128 sweeps:
deep tree,32/64/129 empty dynamic blocks, and changed dynamic/fixed/dynamic cache.
All output/input/work/CRC/page/final/trie-state comparisons passed on the SAME new
artifact. The129-block input crosses multiple AS0 reads/pages and finishes258 actions;
no maximum-quantum batch OOG occurs. Largest observed call75586130gas. The extended
pair/sweep gate ran136.174s/190369792B sampledRSS, exit0/no limits.

New first-action OOG proof uses70,000gas: an opcode diagnostic confirms a CHANGED
SSTORE completed before a subsequent real OOG; actual state roots compared on copies
match BEFORE any host restoration, and valid retry succeeds at74957gas. No trace
bytes/state are used as output or recovery. An earlier60,000gas trial rolled back
but did not establish a completed changed write; it was NOT counted and its failed
proof gate remains in `yield/initial-lowgas*`. Late page-CREATE failure/retry and all
original durable and dynamic-cache process chains still pass.

These are bounded engineering gates, not universal performance or DEFLATE conformance
claims. Tests must retain valid positive expectations, exact malformed/error selectors,
first-action low-gas OOG and budget-yield progress. Production must rerun final artifacts
against all original and newly enlarged streams; no old report substitutes for that.

A final NEW-workspace reconstruction from the tracked parent reproduction script
rebuilt the exact refined artifact, four binaries and Java8 oracle, regenerated all
inputs and strictly checked fresh37/29/4 cases,6pairs/5sweeps and durability/rollback.
It passed in145.440s/334434304B sampled groupRSS (including builds),20min4GiB/no
limit hit. This combined fresh gate does not consult archived passing reports.
Refined runtime14314B SHA60ec1d6c207f10e14eb561e3efc40ee31ce78ebfbf23e95f2106b6835797380a;
artifacta0ab70279c9f69e0487549e81e6b6d36c2133e7bf4da52baf82d6cfa26fa12cf.

## Frozen direction

Select full bounded plaintext staging (max8192words/256KiB) rather than an unnecessary
separate ring; lookback remains<=32768. Immutable verified output uses at most32 EVM
CREATE pages of8192B. Phase1 DECODING,2 VERIFIED,3 PUBLISHING,4 FINAL; empty verified
output auto-finalizes with zero pages/nonzero root. Final read/page never read staging.
CRC+length/exact compressed range gate verification, ignored terminal unused bits and
Java8-compatibleHLIT<=286/HDIST<=30 retain earlier measured policies.

New DI0 transport namespace owns one AS0 upload, one ZI0 index and one DI0 decoder
for a proof session, each ordinary CREATE and each mutation independently published.
A standalone DI0 runtime instance can bind any accepted FINAL ZI0; session routing
is not a requirement to reload an archive for each future guest resource. Future
Java loader/factory integration is separate, and no host parser/canonical table/
output-page installer or adopted older manifest is authorized.

Parent now freezes production writes in the dedicated plan. Up to2 disjoint Sol/high
workers: sole Solidity/runtime writer and separate Go transport/test writer. Prior
stub-only compile failure must not recur: real final artifacts and behavior tests,
publication failure handling, namespace/pins/head shape, full-byte readers, process
resume and16 independent parent groups are mandatory before DI0 acceptance.
