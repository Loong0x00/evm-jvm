# Measured post-grouped-scan q1 gas blocker: unroll packed-u32 lanes

Accepted P19 grouped float validation reaches unchanged original Minecraft1.12.2 frontier 1,274,589 JVM /83 internal, lifecycle1,1365 verified successful receipts. Last q1 publishes a390015-byte checkpoint; next authorized LOCAL4.2B q1 atomically returns empty engine-bubbled data with unchanged root/head. No Java symbol or failed checkpoint is used. Evidence: `evidence/java-evm/minecraft-entry/parent-668583cae/`.

## One bounded exact-wire optimization

In canonical packed rank1-float records only, replace the existing inner `for lane<8` loops with fixed eight-lane memory-safe operations. Encoding may load each already-validated dense uint64 word, narrow to u32 and compose exactly one big-endian 32-byte wire word. Decoding may extract the eight big-endian u32 lanes from one already in-bounds wire word, eagerly store each into eight ordinary uint64[] words, and add exact per-lane nonzero predicates. Keep outer group loop and existing bounded `_put`/`_get` tail. No additional reads, skipped validation, write past tail, alias/lazy representation, cached state or wire/hash difference.

P19 runtime392090 leaves1126 bytes. Generated ordinary1B gates <=1200s must prove lengths1024/1025/1031 and all tails, q1/q7/direct/reopen, opaque same-domain P19 MR01 equality, grouped scan lane refusals, malformed packed/sparse/crossover, retained Integer/Object/Math/raw71/471911, canonical receipts and gas savings. Parent fresh-domain rebuild then untouched-original replay uses authorized LOCAL4.2B <=30s/call and successful checkpoints only. No worker original inputs, logger/world/EULA/`Done`, standard-chain, or push claim.
