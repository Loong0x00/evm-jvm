# Java-on-EVM Minecraft measured raw class cap31 preparation

## Measured blocker

Accepted parent `parent-4fc3c418b` runs the unchanged pinned Minecraft1.12.2 server with raw30 to12005J/40I and1715 canonically verified receipts, then atomically refuses at `LogManager.<clinit>` PC88:

```
MCEntryMissingClass(4107,88,"org/apache/logging/log4j/util/ProviderUtil")
```

The genuine same-JAR entry is4978 bytes, SHA-256 `4cfbc8945526b6d059bfe2b23597898d260035f4cbfae206ae6b3902b2d86bc0`. Appending it produces raw31/256430, still below the fixed262144-byte cap by5714 bytes.

## Authorized scope

1. Raise only the raw selected-class count cap30->31 and its exact derived diagnostic class bound116->117.
2. Preserve all86 accepted bootstrap images/order, raw byte cap262144, CP4096, Code65535, frames128, heap/VFS/checkpoint1MiB, Head32768B,12 native bindings,14 exception kinds, optimizer200/viaIR/Cancun/metadata-off, outlined tail and runtime <=393216.
3. Candidate work uses generated classes only and cannot access original artifacts. Parent alone appends the genuine pinned ProviderUtil entry and runs original31.
4. Generated gates must prove raw31 success, raw32 atomic refusal at driver/coordinator/engine boundaries, byte262144 success/262145 refusal, and retain all accepted TreeMap/String/EnumSet/queue/OOM controls with canonical receipt verification.
5. No provider result, LoggerContextFactory, world or Done claim until genuine execution reaches it.
