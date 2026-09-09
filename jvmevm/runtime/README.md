# JVM subset interpreter runtime

`JVMSubsetInterpreter.sol` is compiled reproducibly by `build.js` with pinned solc
0.8.30 settings. `npm run build` writes the checked-in deployed bytecode to
`JVMSubsetInterpreter.runtime.hex`; `npm run check` recompiles and compares it.
The build also recompiles and byte-checks all bootstrap sources with
`javac --release 8 -g:none`.

## Local MC-LB0 profile

Every invocation appends the canonical `Comparable`, `CharSequence`, and `String`
bootstrap images after the unchanged 24 legacy images. String constants are decoded
from strict classfile modified UTF-8 inside EVM, represented as ordinary String
objects backed by ordinary `char[]` heap objects, and interned per invocation in the
same heap/handle stream used by ordinary allocation and the exception arena. The
profile supports only `length`, `isEmpty`, `charAt`, `equals`, `hashCode`,
`toString`, `compareTo`, and `intern`; other String APIs remain explicit hard
profile errors. `charAt` supports valid indices only; invalid indices are a hard
`StringProfileError`, not a modeled String bounds exception. String construction,
Class mirrors, a main launcher, formatting, logging and continuation are deferred.

Current parent-reviewed candidate is166334bytes, SHA256
`ff9c9ff093e9d4885d7546e01db7aacd95cf999d5cf9b6d6b130fd43b791b982`.
Parent fixed inheritedStringlayout overflow to use ordinary catchable OOM rather
than a bootstrap-format error. Integration/legacy gates passed; see
`JAVA_EVM_MC_LB0_REVIEW.md` for evidence and pending extra review.

Local MC-LB0 tests use separately labelled finite ceilings: **100,000,000 gas / 30s**
for ordinary cases and **1,000,000,000 gas / 120s** for dedicated boundary probes.
These ceilings do not alter opcode gas charging or any historical/stock test budget.
The oversized runtime is executed directly by the local harness and is not evidence
of EIP-170-compatible deployment, Java SE coverage, Minecraft startup, host I/O, or
continuation support.
