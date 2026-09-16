# Generated bounded `Lock.lockInterruptibly` evidence

Source commit `5a2d3b34c1` derives only from accepted cap31 parent
`parent-1e0e9e9aa`. One source build produced a 387394-byte local engine
(under the 393216-byte cap) and a 4146-byte coordinator with pinned solc
0.8.30, optimizer 200, viaIR, Cancun and metadata off.

Java-8 guest `Lock` and `ReentrantLock` are the only replaced bootstrap images:
`Lock` SHA-256 `7a6fbd36152059e1c65f2044fda847ebb11a57d32985ff60998b8d4d147880f7`
(208 bytes) and `ReentrantLock` SHA-256
`a677d76e2d51c13bbdb120eafc1f88098cf0d65e6a0e0c650e76c05f84664175`
(458 bytes). The strict source verifier rebuilt them with Java 8, confirmed the
`InterruptedException` declaration, and proved the other 84 image bytes and
all 86 slots/order unchanged.

The full generated-only gate passed in 191.03391028795158 s: 251 commands,
78 terminal/reopen receipt worlds and 2700 independently canonicalized receipts.
It includes interface dispatch/reentrancy/unlock, catchable null NPE, no-init and
raw replacements for both changed names, plus retained cap31, TreeMap, String,
EnumSet, queue and OOM controls. `RESULT.json` is the compact machine-readable
summary; `source-manifest.json` binds source and untracked build-output hashes.

No original artifact/JAR/class/resource, ProviderUtil/factory, Minecraft/world,
or Done execution was read, run or claimed. Parent alone runs original31.
