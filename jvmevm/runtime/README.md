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

Current accepted MC-LB0 runtime is166385bytes, SHA256
`ea94075540b8b66aa8e85823ee66e9dba4a2be65f29942855a8f59478bca0cbf`.
Parent fixed inheritedStringlayout overflow to use ordinary catchable OOM rather
than a bootstrap-format error. Parent also fixed malformed String-call descriptor precedence. Independentreview
and allintegration/legacy gates passed; see `JAVA_EVM_MC_LB0_REVIEW.md`.

Local MC-LB0 tests use separately labelled finite ceilings: **100,000,000 gas / 30s**
for ordinary cases and **1,000,000,000 gas / 120s** for dedicated boundary probes.
These ceilings do not alter opcode gas charging or any historical/stock test budget.
The oversized runtime is executed directly by the local harness and is not evidence
of EIP-170-compatible deployment, Java SE coverage, Minecraft startup, host I/O, or
continuation support.
