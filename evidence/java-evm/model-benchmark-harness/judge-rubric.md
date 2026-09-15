# Independent blind-judge rubric

Judge A and B independently; do not infer identity and do not use prose length as quality.
Machine-gate failures are supplied as facts and are disqualifying; never replace tests.
For each dimension give 0–10, concrete citations, and uncertainty:

1. **Correctness** — semantics and claims match task/evidence; no fabricated success.
2. **Architecture understanding** — respects EVM ownership, continuations, initialization,
   canonical mirrors, limits and parent/worker boundary.
3. **Modification minimality** — only measured blocker, no unnecessary API/cap growth.
4. **Robustness** — negative paths, atomicity, exception/quota behavior and regression risk.
5. **Maintainability** — clear invariants, source verifier, comprehensible bounded design.
6. **Task completion** — requested deliverables, gates, evidence and clean state complete.

Also report blocker findings with critical/high/medium/low severity, accept/reject for each,
confidence 0–100, and optional preference/tie. A critical machine-verified failure forces
reject. Use per-dimension scores even when selecting a winner.
