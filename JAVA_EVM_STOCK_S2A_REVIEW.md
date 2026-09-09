# Stock S2a independent correctness review

Review target: integrated commit `ba499c561d1393b4d934269504c881d096a31a0d` and frozen `JAVA_EVM_STOCK_S2A_PLAN.md` (SHA-256 `d39a170503d6961416c41719bf6133da2f8e880d6a47c522228c21a5b9baf484`). This review changed no Solidity, artifact, harness, verifier, fixture, S0, S1, monolith, core, limit, or build file.

## Result

**No concrete semantic defect was reproduced in the frozen Stock S2a profile at the reviewed target.** The corrected catalogue representation is internally consistent: both arithmetic-fault rows store numeric `MachineV3.result == 0`, lifecycle 3, kind 1, `pc == faultPC == 2`, a preserved tagged zero divisor, and the expected ArithmeticException label. It must not be interpreted as a returned integer zero.

The independent review tests pin the four artifact byte identities and compare every artifact's six recorded source hashes with the actual local Solidity sources. They directly exercise all eleven added integer opcodes through parser-issued program contexts, and exercise a cross-resume divide fault with a retained lower stack value, three locals, exact instruction count/PC, cap precedence, reserve and dirty-cap rollback, retry, and terminal rejection.

This result is limited to the one-class, one-frame scalar integer/fault S2a contract. It is not acceptance by itself, a full JVM/profile deployment, S2b/frame support, arbitrary Java support, or Minecraft startup/connectivity evidence.

## Correctness audit

Source inspection and actual-EVM probes found behavior consistent with the frozen contract in these areas:

- **Integer operations:** `idiv` and `irem` widen signed int32 operands to int64, so `MIN_VALUE / -1` yields low bits `0x80000000` without a Solidity panic and the corresponding remainder is zero. Other signs truncate toward zero and preserve the dividend sign for remainder. Shift counts use low five bits; `ishr` sign-extends while `iushr` does not. `i2b`/`i2s` sign-extend and `i2c` zero-extends. Bitwise and shift results remain low 32 bits in tagged cells.
- **Fault ordering/state:** arity and both operand tags are checked before a zero divisor becomes a Java outcome. The throwing `idiv`/`irem` is counted once while PC, all pre-instruction stack cells, locals, and the zero divisor remain unchanged. Successful prefix instructions in the batch commit. A cap before the opcode becomes `STEP_LIMIT`; a fault or return on the cap wins. Fault `result` remains numeric zero.
- **Machine/canonical replies:** incoming active/inactive cells, initialized locals, PC starts, lifecycle, result and fault fields are bounded. The coordinator accepts exactly 24 static ABI words, manually checks narrow-word and signed-int32 canonicality, rejects module-returned `STEP_LIMIT`, invalid counts and malformed fault combinations, and validates kind 1 against immutable selected Code and a tagged zero top operand.
- **Parser/flow/cache:** all Code bytes are predecoded, including unreachable unsupported instructions and branch operands. Signed branch targets must be instruction starts. Flow analysis enforces stack height and definite-local joins. Eligible literal records remain ordered and method-scoped; ineligible methods have zero Code-derived fields. The real `WideIntegerConstant.loadWide` path and the discarded oversized unused method are covered by the integrated verifier. The valid 32-method/256-literal/6,336-byte metadata boundary succeeds within the unchanged registration limit.
- **Selection/metadata/provenance:** name ambiguity is detected before selected descriptor/access/Code/argument completion. Metadata keeps the schema-3 six-header/four-word-method/eight-byte-literal layout. Class/program/args/input/digest hashes use the frozen ABI-encoding domains. Step and resume recheck parser registry issuance plus parser/module/raw/metadata code hashes; caller-supplied addresses and hashes alone are not treated as attestations.
- **Continuation/atomicity:** progress depends on positive executed count, so valid same-PC loops continue. Dirty accounting conservatively includes three header words and every changed logical machine word, with a maximum of 26 under the frozen machine. Dirty and reserve failures occur before persistent commit. Registration OOG, nested module failure, outer OOG, malformed response, reserve failure and dirty-cap failure retain the prior registry/checkpoint and logs; rejected fault transitions retry from the same epoch.
- **ABI/deployment/replay:** parser/module are stateless constructor deployments, coordinator immutables are checked against compiler reference ranges, and metadata is ordinary `STOP || payload` code. Tests use signed transactions with sender recovery and nonce/transaction checks enabled. Deterministic direct replay compares transaction hashes, gas, outputs, logs, deployed code hashes, checkpoint and explicit-context state root. EIP-170, EIP-3860 and EIP-7825 remain tested at protocol level.

## Artifact evidence

The source-hash and byte-identity review test checks these pinned templates:

| Artifact | Init bytes | Runtime bytes | Runtime SHA-256 | Runtime Keccak-256 |
|---|---:|---:|---|---|
| `S2aMetadataPage` | 339 | 3 | `0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438` | `3c55237b3869f93f3e570793afec9785f20a4ee7cd0a7798a418838c833228e0` |
| `S2aClassParser` | 15,685 | 15,659 | `8ae89c4943c83f7a138440a1227a094415a107f87bcf7a7e814bc4f911453b7d` | `9746182e3ecdfeace27d26210aaf92997c1b8a74ae34f987bc2a4955433eae6e` |
| `S2aStepModule` | 9,496 | 9,470 | `0f4e6a75ab95b7e289bd91ad8f587b63f9d5b2503934b10fbca5b498dd99129f` | `d004fc0eae66bbf550a65449528b8ff2d96c7f46b5caeed9177b8a68b0164226` |
| `S2aCoordinator` | 13,140 | 7,694 | `e464b3a2237b598de447d369f1cdcb9af568ba7eba2a06168ee1e12a44292212` | `82bbb59342eaeedd9ee649102ed3d70917cafc9f7ec68417669cbe9f41658cc5` |

The local pinned `solc` Node dependency was absent, so `npm run check` was not run and no package install/update was forced. This review therefore provides source-hash, exact-byte, deployment, and execution evidence, not an independent compiler reproduction.

## Test and measurement evidence

Commands run from the assigned worktree:

```sh
go test ./jvmevm/stock/s2a -run '^TestStockS2aReview' -count=1 -v -timeout=10m
go test ./jvmevm/stock/s2a -count=1 -timeout=20m
go test ./jvmevm/stock/s2a -run 'TestStockS2aHarness(CatalogueJVM8JVM21MonolithAndBoundedTrace|SignedAll201ReuseBudgetsPrefixesAndDirectReplay)$' -count=1 -v -timeout=20m
go vet ./jvmevm/stock/s2a
```

All passed. The full package completed in 25.268 seconds. The verbose oracle gate reported 201 rows, 60 programs, 2,642 attempted instructions, `javac 21.0.9`, OpenJDK 8 `1.8.0_504`, Java 21 `21.0.9`, and monolith test-oracle runtime SHA-256 `dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.

The signed all-201 gate reported 24 shared setup transactions, maximum isolated cost 12,029,686 gas over 18 external transactions, maximum 13 resumes, and no failed positive transaction. Across all repeated budget/prefix runs it recorded 2,691 signed transactions; that 2,282,704,065-gas test total is an aggregate across many separately mined transactions, not one block or one workload. Parser and module CREATE used 3,438,259 and 2,101,166 gas respectively. The tests retain the per-transaction 8M registration, 2M resume, 30M block, 800k reserve, and dirty-word limits.

Ignored logs are under `build/java-diff-stock-s2a-review/`. No Minecraft software was run, no EULA was accepted, and no listener was opened.
