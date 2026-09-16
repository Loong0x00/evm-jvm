# Java-on-EVM Minecraft bounded `Lock.lockInterruptibly` preparation

## Measured blocker

Accepted raw31 parent `parent-1e0e9e9aa` runs the unchanged pinned server with genuine `ProviderUtil.class` to12086J/42I and1730 canonical receipts. Both q7 and narrowed q1 atomically stop at `CallError(3,9)`. The published frames identify `ProviderUtil.lazyInit`, classIndex30/methodIndex5/PC9, whose genuine instruction is:

```
invokeinterface java/util/concurrent/locks/Lock.lockInterruptibly:()V
```

The accepted bounded `Lock`/`ReentrantLock` images currently expose only `lock()` and `unlock()`.

## Scope

1. Replace only the existing `java/util/concurrent/locks/Lock` and `ReentrantLock` bootstrap images, preserving their slots and all other84 images/order.
2. Add ordinary Java8 guest `lockInterruptibly()V` declaration and implementation. In the existing single-thread bounded lock model, the successful non-interrupted path increments the same hold count as `lock()`; retain reentrancy and `unlock()` behavior.
3. Declare Java's `InterruptedException` signature but do not claim interruption-state observation, blocking, scheduling, fairness, ownership enforcement, conditions or broad JUC compatibility.
4. Preserve raw31/262144,86 bootstraps, all fixed limits, optimizer200/viaIR/Cancun/metadata-off, outlined tail and runtime<=393216.
5. Generated gates cover interface-dispatched lockInterruptibly success, repeated/reentrant calls, unlock, catchable null receiver NPE, no-init/raw replacement controls, and all retained cap31/TreeMap/String/EnumSet/queue/OOM/canonical receipt gates.

Parent alone reruns original31. No provider result, factory, world or Done claim before measured execution.
