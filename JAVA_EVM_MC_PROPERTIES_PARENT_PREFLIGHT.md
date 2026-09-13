# Parent Properties recovery / preflight

**In progress; not accepted.** The worker stopped with a WebSocket error, but its
worktree was clean and contained four commits:5998b3d81,35433e305,bfc989092,c24d374bc.
No worker/build processes remained. Parent recovered these locally as aa07cffe3,
6ec5def48,3d6584cd7,b035397d0; neither interruption nor worker claims are acceptance.
No push; public snapshot remains the expressly authorized1e4027b9b.

Evidence/recipes: `evidence/java-evm/minecraft-entry/parent-c24d374bc/`.

## Source finding under independent reproduction

The owned `Properties.getProperty` calls `get(key)` virtually. Java8's actual
implementation invokes `Hashtable.get` with `invokespecial` instead. A legitimate
subclass overriding `get` should not intercept `getProperty`; the candidate lets
it do so. Java8's `setProperty`, conversely, **does** invoke `put` virtually, and
defaults lookup must retain virtual `getProperty` dispatch.

`OverrideProbe.java` is a generated TEST-only discriminator with counters for
both overrides and a virtual-defaults control. The Java8 oracle and candidate
EVM replay run independently. Candidate failure is not used as execution input.
The narrow repair is `Object value = super.get(key);` in the owned guest source,
followed by source-only bootstrap/engine/coordinator builds and new identities.
No original Log4j/Minecraft code is edited or replaced.

## Pending parent gate

`run.sh` runs under one20min/4GiB process-group watchdog, absolute fresh ignored
TMPDIR directories, with file-backed child output and no nested session escape:

1. Rebuild candidate bootstrap and full Solidity artifacts from source; compare
   complete artifacts with recovered pins, reproduce the override difference.
2. Rebuild the narrow getter repair with new engine/domain/address/store pins.
3. Java8 TEST oracles; construction, full storage/defaults and override controls
   under q1/q7/direct/reopen, actual lifecycle and opaque terminal equivalence.
   Large direct storage reserve refusal remains labeled, with no rescue.
4. Independently re-encode canonical receipt ABI/events/CP hashes/counter chains.
5. New original20 world with repaired pins, actual EVM archive/resource/class
   processing only; stop at the next real blocker.

The worker's runner unsets TMPDIR and has no RSS sampler; parent does not use it
as a whole-budget acceptance recipe. Worker checkpoint-sequence hashes alone are
not proof of each omitted receipt; parent emits and validates fresh full receipts.

All original24/262144, CP4096, Code65535, heap/VFS/frames,1MiB checkpoint,32768B Head,
320KiB engine and100M/30s/25M reserve limits remain unchanged. Prior45 bootstraps
are preserved; Dictionary/Hashtable/Properties append as45..47. No constructor
shortcut, frame/gas inflation, fabricated properties/resources or main/Done claim.
Original20 previously had14 physical frames and a97161371gas successful slice;
this pressure must be measured, not hidden.
