# Preserved candidate failures

These are development observations, not accepted receipts.

1. The first generated probe called `getSystemClassLoader` before creating any raw
   Class mirror and honestly reverted `LC0StateError(7,0)`. This is the pre-existing
   canonical-loader invariant: the system getter returns an existing canonical loader.
   The final generated probe first evaluates its raw nested class literal.
2. The first binding-8 candidate created a mirror but did not publish
   `arena.nextHandle` and heap aliases before the public Java wrapper's `areturn`.
   It honestly reverted `ReferenceError(1,4)`. The final source publishes that frontier
   immediately after `_loadClassByBinaryName`; direct/q1/q7 receipts prove the repair.
3. An initial local node build used this worktree's absent `jvmevm/runtime/node_modules`
   and failed module resolution for `solc`. The final recorded source build uses the
   absolute pinned LOCAL node module path and solc 0.8.30. No build failure was treated
   as a passing result.

No whole compiler-plus-EVM process-tree watchdog peak was captured in this worker run;
that measurement remains explicitly uncredited.
