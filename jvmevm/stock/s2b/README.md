# Stock S2b-L independent validation

This directory contains the independent verifier for the frozen Stock S2b-L
registration/link slice. S2b-L creates reusable schema-4 method, literal and
same-class `invokestatic` metadata in ordinary EVM contracts. It does **not**
contain a frame store, Java call execution, resume operation, Java outcome
interface, or a claim that the 268-row M3a catalogue executes through stock EVM.

`validation_test.go` intentionally does not use S2b-L harness execution helpers.
It decodes the three pinned artifact JSON files again, loads only accepted S0's
`ArtifactPage` and S2a's parser for compatibility setup, funds a deterministic
test EOA, and signs and recovers every transaction. Transactions retain nonce
and transaction checks and run through `TransactionToMessage`, `ApplyMessage`,
and ordinary `CREATE`; no code or storage is injected.

The verifier checks:

- pinned solc 0.8.30/via-IR/Cancun/optimizer/metadata settings, ABI, deployed
  analyzer bytes, linker immutable ranges and getters, EIP-170/EIP-3860/EIP-7825
  layers, and the 20 KiB/12 KiB/24 KiB component limits;
- exact schema-4 headers, five-word declaration records, instruction-start maps,
  compact literal/call records, code hashes, class IDs, events, unknown records,
  and real-count idempotence;
- all 14 frozen Java classes compiled with `javac --release 8`, their exact raw
  SHA-256 identities, all 51 M3a call records, and direct versus S2a-adapter
  registration equivalence;
- tag-10 CP chains, external owners, tag-11 interface references, missing and
  duplicate exact targets, overloads, private/package/protected methods, void and
  six-argument descriptors, reserved/nonstatic/native/abstract/synchronized and
  malformed-Code targets, and exact deferred method/bytecode/call domains;
- the immutable Phase-A policy: a valid caller keeps its symbolic call cache when
  the callee's final body has a bytecode or call error, while an unusable Phase-A
  envelope produces `CallError(4)`;
- width, branch-target, underflow, return-shape, stack-capacity, local-range,
  definite-initialization, fallthrough, unreachable-unsupported and aggregate
  cap negatives, with no cache fragments on ineligible methods;
- a Java-verified dense CFG whose independent target-first FIFO simulation makes
  279 cumulative enqueues for 192 code bytes, proving that the obsolete
  `CodeLength+1` cumulative queue limit would reject a legal graph. Java 8 is
  also used when installed, in addition to the current JVM with `-Xverify:all`;
- the shared exact cap class (`0e3e…46f33`): 3,574 raw bytes, 32 methods, 256
  literals, 32 calls and a 7,936-byte payload. Direct and adapter paths must fit
  the unchanged 8,000,000 gas limit. A fresh linker's one-less-gas failure must
  leave no registry record, metadata page, linker CREATE nonce, or event, and a
  normal-gas retry must succeed;
- canonical analyzer and legacy-parser returndata boundaries. Test mocks are
  ordinary deployed EVM bytecode, not production Solidity writers. They exercise
  exact offsets, high bits, padding, trailing data, bounded size, identity/header
  hashes, H6, reserved words, dimensions and caps. A configured canonical mock is
  accepted to show that the linker does not duplicate per-record Java analysis;
  this is not analyzer attestation. Separate gates pin the real analyzer code;
- accepted S2a metadata provenance, old class-ID recomputation, schema-3 versus
  schema-4 namespaces, direct/adapter ordering, malformed registry replies and
  old headers; and deterministic signed replay of addresses, gas, output, logs,
  code hashes, registry values and state root.

Missing S2b-L artifacts or shared fixtures are hard integration failures. The
verifier supplies no fallback bytecode, host-derived offsets, CP targets, Code
maps, metadata, Java result, or class-specific executable. Host Java is used only
as a trusted test compiler/verifier oracle.

Passing these tests establishes registration/link metadata evidence only. It does
not establish Java call execution, recursion or stack-overflow outcomes, a stock
execution count for M3a, arbitrary Java support, Java SE conformance, standard
Minecraft deployment/startup, client connectivity, or any EULA/listener action.
All original EVM opcode, gas, consensus and protocol limits remain unchanged.
