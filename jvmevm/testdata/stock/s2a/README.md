# Stock S2a trusted catalogue

`catalogue.json` is test-only evidence for the 201 ordered legacy `m1`, `m2`,
and `m2b` rows: 199 integer values and two terminal
`java.lang.ArithmeticException` outcomes. Tests still read the original
`jvmevm/testdata/differential/cases.json` and eleven Java sources unchanged.

The classes are compiled together with `OracleMain.java` using `javac --release
8 -d <output>` with default debug attributes (no `-g:none`). Their pinned raw
class SHA-256 values are:

- Comparisons: `5c4a076b97e146ed73e14a5bea4f3722d3a18be284abd23bf0a56a5848d3cb9e`
- Constants: `6b3473ae373a53d0c6a8a2a8df4b00b978a9c2db4890bacf14900717d60701a1`
- IntegerArithmetic: `69c6a01e0045efc1caa3e2a9c598a4dd75530fe74f5b4e2c378689feb1c27d43`
- IntegerBitwise: `8cece8e7b75cf657b146eade5cd73d8616826f73ac14427e8e1f0c51fa9dc018`
- IntegerConstants: `189ac9b47a7f09a080a64be3e662aba0045440ca78a6d65674256e0cb0aaf0fd`
- IntegerConversions: `ba383508690bf9aab643b26af435077cc002d8b4ccd61cd6b52b734a82e7fd08`
- IntegerShifts: `1cd887856a8e6922e14c5246c3c563dd5914d499511b0be0fc9b35178d9df2bc`
- LocalsAndArithmetic: `423ca06bab0adebb43e8d98df8438840fe4635bfa73e2e6c28b6397d1b195653`
- Loops: `c9043994623a900a6c1f4ed096c9d1c23783842d2e5e1406646deea9db20fa38`
- M1Baseline: `1e71a54ba434b943b44c8633a1fb9e4c52e4f435eaeffb5ebf47e546c49d0813`
- WideIntegerConstant: `fbf7d7498a50fa0ed8adba88ef74f702cdd4bc82fdab94ba75c8e54a77eb9137`

For ordered row index `i`, each leaf is:

```text
keccak256(abi.encode(
  uint32(3), uint16(i), keccak256(bytes(caseId)), rawPayloadHash,
  keccak256(bytes(binaryClassName)), keccak256(bytes(entry)),
  keccak256(bytes(descriptor)), keccak256(abi.encode(int32[] args))))
```

The catalogue root is
`keccak256(abi.encode(uint32(3),uint16(201),bytes32[] orderedLeaves))` =
`0x1273f2302d2898a2eb0ff391f9cf7ff2c9b64749fd0821df891b921499aa8d0d`.
The catalogue records 60 roots and 2,642 attempted terminal instructions. Its
expected outcomes, PCs, stacks, locals, and trace counts are assertions only;
production calls receive raw pages, entry bytes, arguments, and a finite step
cap, never host Code offsets, targets, results, fault decisions, or trace state.

The S2a Go package embeds only pinned artifacts under
`jvmevm/stock/s2a/runtime/artifacts`. A harness-only checkout before the separate
runtime commit is integrated fails on that missing embed dependency instead of
substituting generated or fabricated bytecode.
