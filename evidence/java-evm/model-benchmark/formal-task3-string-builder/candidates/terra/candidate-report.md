# BENCHMARK_RESULT

## Result
Blocked: the one pinned solc build measured a 395319-byte engine runtime, exceeding
393216 by 2103 bytes. The generated gate was not run.

## Files Changed
- `evidence/java-evm/minecraft-entry/string-builder-preflight/`
- `evidence/java-evm/minecraft-entry/string-builder-failure-0153480d1/`
- `BENCHMARK_RESULT.md`

## Verification
- Strict parent-89928ece8 reverse/source verifier passed; it compiled and pinned the
  542-byte Java-8 StringBuilder image and checked image85, raw30, and fixed limits.
- Required solc 0.8.30 / optimizer-runs 200 / viaIR / Cancun / metadata-off build
  stopped at the fixed runtime cap. Durable logs and hashes are in the failure evidence.

## Remaining Uncertainty
No q1/q7/direct/reopen/canonical gate ran because the runtime cap failed. A scoped
size repair would need a new authorization/build attempt; this candidate is not accepted.
