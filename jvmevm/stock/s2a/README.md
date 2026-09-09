# Stock S2a independent validation

This directory is the independent verifier for the frozen Stock S2a slice. S2a
is a small, one-class, one-frame scalar Java `int` profile: the 201 unchanged
M1/M2/M2b catalogue rows (199 returned values and two terminal
`java.lang.ArithmeticException` outcomes). It is separate from accepted Stock S0
and S1 and from the oversized local M5d-a interpreter.

`validation_test.go` does not use S2a harness execution helpers. It decodes the
four pinned S2a artifact JSON files itself and reuses only accepted S0's raw
`ArtifactPage` artifact. Missing runtime artifacts or catalogue files are honest
integration failures; no fallback bytecode, injected code/storage, host result,
or hardcoded class offset is supplied. Tests fund only a deterministic genesis
EOA, sign and recover every transaction, keep nonce and transaction checks on,
and use ordinary `CREATE` and `core.ApplyMessage` calls.

The verifier independently recompiles the 11 trusted sources with the pinned
`javac --release 8 -d` boundary, checks source/class/payload hashes, preserves all
201 ordered rows and legacy gas limits, and recomputes schema-3 leaves and the
catalogue root. Its bounded decoder is assertion-only: raw class bytes alone are
sent to production registration. It checks the six-header/four-word method and
8-byte literal layout, parser-issued provenance, idempotence, roots, immutable
references, exact ABI/state/event canonicality, and deployment/gas limits.

Semantic probes cover signed division/remainder (including `MIN_VALUE / -1`),
bitwise operations, masked signed/unsigned shifts, narrowing conversions, the
retained S1 branch/loop/local rules, a genuine `ldc_w`, and the valid 32-method,
256-literal, 6,336-byte metadata boundary. The aggregate class is loaded with
`-Xverify:all` before use. `WideIntegerConstant.populateIntegerPool` remains an
ineligible Code-793 method whose 261 sites do not consume the literal quota,
while `loadWide` executes its real wide constant-pool load.

A zero divisor produces lifecycle 3/kind 1 at the actual `idiv`/`irem` PC. Tests
require one attempted fault instruction, unchanged pre-fault operands and locals,
no following instruction, committed successful prefixes, and exact cap
precedence: cap-before-fault is `STEP_LIMIT`, while a fault or return landing at
the cap wins. Unknown fault kinds (including kind 2), malformed lifecycle/result/
PC/tag/stack responses, and noncanonical incoming machines are rejected rather
than decoded as Java outcomes. Dirty-cap, reserve, nested/outer OOG, registration,
and component failures preserve the prior checkpoint and registry state; a
rejected fault response can be retried.

The verifier also retains stock EIP-170, EIP-3860, and EIP-7825 protocol-layer
checks. Registration is bounded by 8,000,000 gas, each resume by 2,000,000 gas,
the commit reserve remains 800,000 gas, and dirty-word caps remain at most 32.
No protocol, opcode, precompile, consensus, or block/transaction limit is changed.

This verifier does **not** establish acceptance by itself. Parent integration
must review the runtime, exact artifact hashes, harness results, signed replay,
gas measurements, and retained S0/S1/legacy gates. S2a has no calls, frame store,
private/void method profile, handlers, SOE, heap, arrays, long/FP, statics,
libraries, or S2b execution. It is not a full JVM, not arbitrary Java support,
and not a Minecraft startup or connectivity result. No Minecraft server is run
and no EULA or listener is used.
