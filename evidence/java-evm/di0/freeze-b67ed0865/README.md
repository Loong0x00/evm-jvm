# Post-freeze dependency and archive checks

No DI0 production acceptance. At b67ed0865, independently compared all565 manifest
payload hashes against actual committed Git blobs, not only working-tree bytes;
all pass (compressed fixture binary attributes preserved byte identity).

`make java-mc-as0-test java-mc-zi0-test` rebuilt/checked accepted embedded artifacts
and ran their full existing tests under the outer20min/4GiB watchdog:
30.024s/488304640B sampled groupRSS, exit0/no limit. Sources/core unchanged.

Two production writers started from b67ed0865 in separate mc-di0-runtime and
mc-di0-harness worktrees with Sol/high and no Fast/priority. Frozen ownership and
16 independent parent acceptance groups are in JAVA_EVM_MC_DI0_PLAN.md.
No official inflation, Java/Minecraft/EULA/listener/world/Done or push.
