# LOCAL1M ArrayList raw150/1,063,930-byte append-only envelope

This stage is derived from the guarded `array-list-local1m-safe` stage at
`fff70258a`. It changes only the independent raw input quotas: 150 raw classes
and 1,063,930 aggregate raw bytes. The 99 bootstrap images, Native21,
String-local12, VM semantics/opcode gas, runtime ceiling (1,048,576 bytes),
and existing 1 MiB checkpoint ceiling are unchanged. Generated tests measured
the checkpoint ceiling sufficient, so it was not increased.

## Verified generated-only results

The durable run is [`runs/raw150-positive-004/`](runs/raw150-positive-004/).
Its manifest pins stage/fixture source hashes; build and execution logs, gate
summaries, reopen summary, and successful checkpoint blobs are archived there.

- Fresh source proof permits only scoped engine/coordinator raw-count and
  byte-limit changes. The 99 bootstrap images, runtime semantics, and opcode
  charging are unchanged.
- Engine runtime is 394,996 bytes (under the 1 MiB cap); coordinator runtime is
  5,411 bytes. Raw150 q1/q7/q65536/q4096 schedules all terminate in MR01 with
  150 raw and 249 diagnostic classes. q1 checkpoint reopening succeeds in a
  distinct process.
- The generated exact boundary is 150 classes / 1,063,930 bytes. The +1-byte
  case (1,063,931) and 151-class case are refused by the engine envelope;
  old-engine-codehash resume refusal is preserved. Exact-boundary checkpoints
  are 11,914 bytes.
- A generated-only EVM route uses ordinary CREATE for the AS0 controller, ZI0
  index, all 150 DI0 decoders, and coordinator, then calls the pinned local
  engine. EVM ZI0 discovers 150 generated ZIP entries; DI0 publishes the raw
  generated class bytes. The coordinator reaches terminal MR01 at the exact
  raw-byte boundary. Its constructor refusals are MR0Error(2) for 151 classes
  and MR0Error(6) for an invalid class namespace; the latter preserves the
  committed engine head.
- The coordinator route made 3,224 EVM calls: 11,813,734,408 gas aggregated
  across them, with a maximum individual call of 438,085,981 under the explicit
  1,000,000,000 per-call test budget. This aggregate is not one transaction's
  gas. The complete gate took 88 seconds within its separate 1,200-second
  test-only wall budget. Neither test budget needed expansion.

No original Minecraft JAR or parent receipt is used by these gates. The
interpreter is local preinstalled EVM code, not ordinary CREATE deployment; the
coordinator's ordinary-creation route is only a generated-input integration
check. No original replay, Minecraft readiness, EULA, or `Done` claim is
included.
