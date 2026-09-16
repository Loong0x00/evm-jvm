# Result

Generated-only bounded `Lock.lockInterruptibly` stage completed from accepted cap31 parent `parent-1e0e9e9aa`.

- Replaced only the existing `Lock` and `ReentrantLock` Java-8 bootstrap images; all other 84 image bytes and the 86 slots/order remain verified unchanged.
- `lockInterruptibly()V throws InterruptedException` now follows the single-guest-thread successful hold-count path; no interruption, blocking, scheduler, fairness, ownership, condition, timed-lock, or broad JUC claim is made.
- One source build produced engine `387394 / 393216` bytes and coordinator `4146` bytes.
- Full generated gate passed: 251 commands, 78 canonical receipt worlds, and 2700 verified receipts, including interface/reentrant/unlock, null NPE, no-init, both raw replacements, cap31 limits, TreeMap/String/EnumSet/queue/OOM controls.

Evidence: `evidence/java-evm/minecraft-entry/lock-interruptibly-5a2d3b34c1/`.

No original artifact/JAR/class/resource, ProviderUtil/factory, Minecraft/world, or Done execution was run or claimed. Parent alone runs original31.
