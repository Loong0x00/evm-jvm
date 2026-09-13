# Parent System.arraycopy investigation

Status: **in progress, not accepted**. Source/evidence directory:
`evidence/java-evm/minecraft-entry/parent-f780f1a13/`.

The user explicitly authorized a push during this investigation. Only the
previously reviewed main was pushed: remote `origin/java-on-evm` independently
confirmed `1e4027b9b48fd7b63103aa27e4fe911af513b928`, replacing `31e40ad6f`.
The subsequent candidate integration/repair remains local; this is not standing
permission to publish future work.

## Independently reproduced candidate failure

Worker `fd614c645` / `f780f1a13` was integrated locally as `1747c4925` /
`0e60ebab6`, not accepted from its report. Parent reconstructed the candidate
engine and coordinator from Solidity alone, matched the complete compiler
artifacts, rebuilt the actually bounded parent Go transport, and ran fresh
q1/q7/direct generated worlds.

* q1: epoch176 / Java176 / internal3, **RUNNING**, main PC106 with five operands.
* q7: epoch25 / Java175 / internal3, **RUNNING**, main PC105 with four operands.
* Both next resumes and direct q4096 fail with EVM Panic `0x32`, with unchanged
  published roots. A host `final-reopened` label does not establish Java VOID.
* Thus these are differing prefix boundaries before the **same** failure, not
  demonstrated terminal quantum divergence. The worker's VOID claim is false.
* Source cause: `_loadNativeCallee` removed `s.argumentCount = 1` without setting
  the parsed count. Invocation calculates `base = sp` instead of `sp - 5` and
  reads outside the operand-stack allocation at the first arraycopy.
* The worker's Go driver also still appends read sizes and PIDs to Head; its
  assertion that it retained bounded metadata is false. Parent reconstruction
  uses `parent-25b1f35a0/executed_bounded_driver.go.txt`, preserving the 32768B cap.

## Narrow repair under test

The reconstruction recipe changes only native argument count to the parsed
argument-kind count (five for arraycopy, one for the prior FP bit intrinsics),
plus isolated identities and the resulting code pin. New address:
`0x4d434152524159434f5059504152454e54000001`; domain `MC-ARRAYCOPY-PARENT1`.
No old-code checkpoint is reused. Exact oversized engine is LOCAL initial state,
not ordinary CREATE; coordinators and resources remain ordinary CREATE.

Tests require actual terminal lifecycle/outcome, guest final static sentinel,
q1/q7 opaque machine equality, ordinary call limits, and successful events.
An additional parent Java8 fixture covers real Marker interface arrays, aliasing,
both overlap directions, actual exact-end zero length, null/type/bounds/overflow
precedence, partial reference-copy effects, and nested array component checks.
Compilation/worker completion is not acceptance. Original13 is retried only
after these tests, in a new world through EVM AS0/ZI0/DI0.

Accepted sources/quotas remain untouched. No complete System/JVM/Class/map,
concurrency, Session, Minecraft main-body/world/Done claim.
