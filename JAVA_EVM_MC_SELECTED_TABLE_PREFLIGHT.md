# Selected-table lazy allocation COPY preflight

Status: **DISPOSABLE implementation draft; not accepted or a profile change.**

This is the sole Solidity semantic change for the bounded experiment described by
`JAVA_EVM_MC_SELECTED_TABLE_PREPARATION.md`.  It starts from parent capacity COPY
reconstruction at base `b24d5ff4058aa387056e6cb01f2c0df57b582415`, itself pinned to
accepted source `7b46769c5`.  It does not edit accepted sources, artifacts, ABI,
quotas, Makefiles, or any MR0 files.  All edited Solidity exists only in a fresh
ignored `build/java-diff-mc-owncapacity-selected-*` copy.

## Representation and alias argument

`Program.selected` changes from `Selected[][]` to `Selected[][][]`:

* the outer class array and each class's method array are allocated as before in
  shape, but each method element is now only a dynamic-array pointer;
* `_putSelection` allocates `new Selected[](1)` only once a method has been
  resolved/predecoded, and stores that single independently allocated object in
  the method slot;
* `_selectionLoaded` requires a one-element slot and the original `Selected.loaded`
  flag; `_selectedAt` is used for every read; all resolution paths use
  `_putSelection`.

Thus an unloaded slot is a zero-length `Selected[]`; it has no mutable fields. A
loaded slot owns a distinct `new Selected[](1)`.  No sentinel is shared, no assembly
is used, and no loaded metadata is aliased.  In particular
`handlerClassesPlusOne` remains inside the independently allocated `Selected` that
is passed to `_resolveCatchClass`; its writes cannot reach another method's slot.
The patch covers root creation, restored frames, athrow handler inspection,
initializer loading, virtual/interface/default dispatch, special/constructor/VFS
native dispatch, and static/native dispatch. Reference and field caches retain their
original per-class allocation and indexing.

The source patch is
`evidence/java-evm/selected-table/preflight/selected-table.patch`
(SHA-256 `d42bc1290402080c1383af3a16a7dddf13f82a8b2e2c6e21e82073cd68100461`).
The recipe reconstructs pinned accepted inputs, applies the old capacity-only COPY
patches, gives all generated Go packages a distinct namespace, and then applies
only this source patch.  It installs each copied lockfile locally (the repository
has no checked-in `node_modules`), retaining the initial missing-local-solc failure
in the evidence directory rather than treating a global compiler as a pin.

## Fresh EVM gate

The fresh `run-20260912T110538Z` archive records a complete reconstruction,
re-pin and public-transport gate: **407.515 s**, sampled process-group peak
**878391296 B**, 1991 samples, exit 0, under its 1200 s/4 GiB limits. It compiled
with solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, viaIR, Cancun
and metadata off. The engine is 292605 B, SHA-256
`b8013a6592938b8ba58129fbb4d3db6d6ee87a15856515e4f3aafa0e5cab6ed7`, below the
320 KiB LOCAL cap. Its Keccak is
`fdd73425c5c82ac344b72130aa3ac6db98ba5c6341df0982a9c039ea24844c0f`;
the separately re-pinned coordinator artifact is
`44a1d0685a7b6e9907d98f689ffaf025ae90f0d4826a9cb444356d6448dd6687`.
The coordinator package/resource/VM domain is `MC-SELECTED-TABLE-PREFLIGHT`.
This intentionally differs from the capacity reference engine/config/package/
instance/machine roots; no cross-engine literal-root or payload-byte equality is
claimed.

The verifier checked 24 worlds/94 distinct process receipts, 52 published
checkpoint files and 566 actual DI0 fragments. It exercised cold, memory warm,
disk/new-process reopen, q7, publication failure/old-root retry and size/count
refusals, using only opaque ZIP -> AS0 -> ZI0 -> DI0 FINAL -> coordinator reads
of at most 4096 bytes. It retained CP4096/Code65535, 8/262144 input limits,
1 MiB checkpoints, 38 bootstraps and the original ordinary budgets/reserve.

For the three-image 181969 B `BigPair` input (result 23), ordinary 100M direct
now finishes at **63660316 gas**; q7 finishes in 3 slices and q1 in 20. Every
dense call has 47 actual <=4096-byte DI0 reads and direct/q1/q7 agree on final
same-engine machine/VFS roots, counters and result. The old parent capacity
reference had an ordinary `LC0ControlError7` at 74874471 gas and required its
explicit 1B-only 124505990-gas direct run. This is a measured comparison of
separately pinned engines, not a false equal-root claim. The one-class BigEntry
run is 31474005 gas (parent reference 48451006); padded262144 is 7911658
(parent reference 7879725), so the improvement is method-density-specific, not
claimed as a universal reduction. No 1B optimized rescue was used.

## Remaining mandatory work

This worker did not add a dedicated loaded/unloaded alias fixture spanning every
requested clinit/constructor/virtual/interface/default/caught-and-uncaught case,
nor a new peak-EVM-memory/free-pointer observer that can report optimized
allocation counts/bytes. It therefore does **not** claim the exact number of
`new Selected[](1)` allocations, an exact memory-expansion reduction, opaque
checkpoint payload byte equality across changed envelope bindings, or production
acceptance. The existing matrix gives regression coverage but is not a substitute
for those dedicated negatives. Ordinary 100M remains first; 1B/120s stays
reference/boundary-only and never a rescue.

## Reproduction

From the repository root, with a nonexistent fresh output directory:

```sh
python3 evidence/java-evm/selected-table/preflight/prepare_selected_copy.py \
  build/java-diff-mc-owncapacity-selected-<run>
python3 evidence/java-evm/selected-table/preflight/repair_selected_copy.py \
  build/java-diff-mc-owncapacity-selected-<run>
python3 evidence/java-evm/selected-table/preflight/finalize_selected_pins.py \
  build/java-diff-mc-owncapacity-selected-<run>
python3 evidence/java-evm/selected-table/preflight/build_selected_drivers.py \
  build/java-diff-mc-owncapacity-selected-<run>
```

The driver uses normal owned/cloned public transport and opaque ZIP fixtures only;
it has no raw-class, host parser/inflater/evaluator, reflection, private state, or
page-code installation path. `initial-reconstruction-missing-local-solc.log` and
`reconstruction-import-namespace-failure.log` are retained failed attempts.
