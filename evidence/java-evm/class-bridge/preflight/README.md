# Disposable class-bridge preflight evidence

Base: `73e17afbb5373b0cc2938b8b90ca950146fe8e9b`. This directory contains only trusted generated Java 8 fixtures and a disposable adapter. It contains no official Minecraft/server bytes and proves no Minecraft execution or acceptance.

## Reproduce

From the repository root, choose a new ignored output path (the script refuses an existing path):

```sh
python3 evidence/java-evm/watchdog.py \
  build/java-diff-mc-class-bridge-preflight-REPLAY.log \
  build/java-diff-mc-class-bridge-preflight-REPLAY-watchdog.json \
  bash evidence/java-evm/class-bridge/preflight/run.sh \
  build/java-diff-mc-class-bridge-preflight-REPLAY
```

`run.sh` uses the tracked npm lock, solc 0.8.30, Java 8u504 `javac/java`, deterministic generated ZIPs, and `replay.go`. `replay.go` opens ZIP files only as opaque upload bytes. It never opens a generated `.class` and never supplies class bytes to VFS0a. The Java 8 reflection oracle is a separately labeled test process run before ZIP creation; its result is not execution input.

The accepted DI0 package intentionally does not expose its `StateDB`. The disposable replay uses reflection/unsafe solely to attach infrastructure to that same EVM world. It installs the exact accepted oversized VFS0a runtime at its frozen LOCAL address (the one expressly allowed host code installation) and ordinary-CREATEs `ClassBridge`. It does not inspect DI0 page code/plaintext via that pointer. AS0, all AS0 data pages, ZI0, DI0, DI0 output pages, and the adapter use ordinary EVM CREATE paths. This reflection glue is a measured production-integration blocker, not a proposed API.

## Final retained run

- `final-report-73e17afbb.json`: complete roots, gas, calls, per-operation wall, success and negative outcomes.
- `ClassBridge.artifact.json`: pinned disposable init/runtime/ABI/settings.
- `final-run-73e17afbb.log`, `final-watchdog-73e17afbb.json`: exit 0; 1.687s; 248,274,944-byte sampled peak group RSS.
- `SHA256SUMS`, four exact generated fixture ZIPs, source/build/replay/verifier inputs, and `java8-bytecode-73e17afbb.log` showing the compiled loop/branch Code and actual `invokestatic` helper call sites.
- Wrapper: init 3823B SHA256 `f24b8b115bf42afc2d83eb22dc1654b132c40167fec4664c3110a636790531cb`; runtime 3780B SHA256 `49f81b97402bf95f000c4bfaa5cf2f901df5e5b2788c0e1bc77e89951456c7a9`; source SHA256 `76f95867bbb9714aa4cd49b9222529be64236282d8e06a94f5e8d63f2678342b`.

The meaningful earlier failures/corrections remain under distinct names: initial relative-module path and shell quoting failures, dotted-vs-JVM-internal-name correction, and the pre-owner-gate run. They are not final evidence. Pure artifact-label/extra-capture reruns were disposable and are not archived as evidence.
