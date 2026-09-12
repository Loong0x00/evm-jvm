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

## First build evidence (not an EVM gate)

A fresh reconstructed copy compiled with solc
`0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, viaIR, Cancun and metadata
off. The build script reported runtime 292605 B, SHA-256
`b8013a6592938b8ba58129fbb4d3db6d6ee87a15856515e4f3aafa0e5cab6ed7`, below the
320 KiB LOCAL experiment cap. This differs from the capacity reference engine and
therefore requires different code/config/package/instance/machine roots; no
cross-engine literal-root equality is claimed.

The initial draft contains the narrow source patch and public-transport driver
recipe only. Real opaque ZIP -> AS0 -> ZI0 -> DI0 FINAL -> coordinator EVM gates,
allocation/peak-memory measurements, selection regressions, and watchdog results
must be archived before this can be assessed. Ordinary 100M/30s remains first;
1B/120s is reference/boundary-only and never a rescue.

## Reproduction

From the repository root, with a nonexistent fresh output directory:

```sh
python3 evidence/java-evm/selected-table/preflight/prepare_selected_copy.py \
  build/java-diff-mc-owncapacity-selected-<run>
python3 evidence/java-evm/selected-table/preflight/repair_selected_copy.py \
  build/java-diff-mc-owncapacity-selected-<run>
python3 evidence/java-evm/selected-table/preflight/build_selected_drivers.py \
  build/java-diff-mc-owncapacity-selected-<run>
```

The driver uses normal owned/cloned public transport and opaque ZIP fixtures only;
it has no raw-class, host parser/inflater/evaluator, reflection, private state, or
page-code installation path. `initial-reconstruction-missing-local-solc.log` and
`reconstruction-import-namespace-failure.log` are retained failed attempts.
