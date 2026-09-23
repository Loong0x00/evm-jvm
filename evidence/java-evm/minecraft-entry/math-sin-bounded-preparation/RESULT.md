# Result: bounded integer-only `Math.sin(D)D` candidate

- Implemented global native binding 19 with finite symmetric raw magnitude bound `0x401921fb54442d18`, signed-zero preservation, nearest-even Q120 recurrence and final integer IEEE conversion. Values outside the bound and nonfinite values use an atomic `MathSinProfileError` refusal.
- Changed no bootstrap images (all 97 identical); source-derived ordered P2 root is `e8d2682b12ee29790e98011eb4745d7f41706d085b11c649de02faffd633efac`. Runtime: 386,037 / 393,216 bytes.
- Generated EVM gate passed in 465.513 seconds: q1/q7/direct/reopen for measured input, edge and sampled grid fixtures; 3,769 canonical receipts; sampled outputs <=1 ULP of Java 8 oracle and selected float casts exact; out-of-domain/nonfinite refusals atomic. Prior sqrt, sparse-array checkpoint/malformed and retained library/capacity regressions passed.
- Independent test-only 65,536-row Q120 comparison: maximum 1 ULP, 2,008 double bit differences, zero float-cast differences. It is not a universal correct-rounding or Java 8 equivalence claim.
- Durable evidence and hashes: latest `results/generated-gate-v2/`; `generated-gate-v1/` remains unchanged as historical. See `README.md` and `tools/verify_results.py`.
- Not parent-accepted: parent independent rebuild/gate and unchanged-original replay remain required. No Minecraft startup/Done claim.
