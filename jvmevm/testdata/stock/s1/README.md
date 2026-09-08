# Stock S1 trusted catalogue

`catalogue.json` is test-only evidence for the 82 ordered legacy `m1`/`m2`
rows. Tests continue to read `jvmevm/testdata/differential/cases.json` and the
five original Java sources in place; this directory does not replace or modify
those inputs.

The classes are regenerated together with `OracleMain.java` using `javac
--release 8 -d <output>` (default debug attributes, deliberately no `-g:none`).
The pinned raw class SHA-256 values are:

- Comparisons: `5c4a076b97e146ed73e14a5bea4f3722d3a18be284abd23bf0a56a5848d3cb9e`
- Constants: `6b3473ae373a53d0c6a8a2a8df4b00b978a9c2db4890bacf14900717d60701a1`
- LocalsAndArithmetic: `423ca06bab0adebb43e8d98df8438840fe4635bfa73e2e6c28b6397d1b195653`
- Loops: `c9043994623a900a6c1f4ed096c9d1c23783842d2e5e1406646deea9db20fa38`
- M1Baseline: `1e71a54ba434b943b44c8633a1fb9e4c52e4f435eaeffb5ebf47e546c49d0813`

For row index `i`, the frozen leaf is:

```text
keccak256(abi.encode(
  uint32(2), uint16(i), keccak256(bytes(caseId)), rawPayloadHash,
  keccak256(bytes(binaryClassName)), keccak256(bytes(entry)),
  keccak256(bytes(descriptor)), keccak256(abi.encode(int32[] args))))
```

The catalogue root is
`keccak256(abi.encode(uint32(2),uint16(82),bytes32[] orderedLeaves))` =
`0xf98038bd7cb12d165c0b22dd7feca869803efce86a8194f4a3ddb1973f84764b`.
The 82 expected values, 2,213-step trace totals, PCs, and locals are assertions
only. Production S1 calls receive raw pages, entry bytes, arguments, and the
finite step cap; they never receive catalogue results, Code offsets, PCs, cache
records, or trace state from this file.

The S1 Go package intentionally embeds only pinned artifacts produced under
`jvmevm/stock/s1/runtime/artifacts`. On a harness-only checkout where that
separate runtime output has not yet been integrated, package compilation reports
the missing embed dependency rather than substituting fabricated bytecode.
