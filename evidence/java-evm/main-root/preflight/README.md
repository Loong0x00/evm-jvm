# MR0 disposable direct-main COPY experiment

This directory is the only implementation surface. It carries copies of the
accepted VFS0a interpreter and CB0 coordinator, renamed and domain-separated;
the repository sources remain untouched. `engine/build.js` and
`coordinator/build.js` use the pinned 0.8.30 optimizer-200/viaIR/Cancun/no-CBOR
compiler configuration and emit checked source/ABI/init/runtime hashes.

The engine's only launch is `startMain`: it chooses exact public static
`main:([Ljava/lang/String;)V`, allocates an ordinary heap rank-one String array
with length zero, writes its non-null reference to root local 0, and uses the
ordinary checkpoint heap codec. The prelude magic is `MR01`; root kind and
empty-argument commitment are serialized. Resume decodes/validates the retained
array instead of creating it. Root return is tagged void versus Java exception.
The copied coordinator has only `startMain`/`resumeMain`, retains CB0's EVM FINAL
DI0 <=4096 reads and 1..4/65536 constructor checks, and pins the compiled isolated
engine code hash/address. Its normal resources/controllers are ordinary CREATE;
only the isolated engine code address is a disposable LOCAL initial-state install.

`fixtures/` is generated Java 8 only. Its ZIPs are intended for the AS0->ZI0->DI0
route; `Oracle.java` is deliberately not in them. No official jar/class is used.

**Current evidence is compilation and fixture construction only, not an EVM
execution or acceptance gate.** No Go driver/transport copy has yet executed
start/resume, so direct/q1/q7, CAS/publication/disk process, typed refusal, gas,
checkpoint, and persistence claims remain unmeasured. This is a material blocker,
not a substitute result. The parent must independently reconstruct a public-only
isolated harness before any acceptance discussion.
