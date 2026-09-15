# Paired model benchmark harness

This harness accompanies three real JVM-for-EVM Minecraft blocker tasks. It does not
replace parent acceptance. Each task freezes one task file/hash and base commit, then runs
`openai-codex/gpt-5.6-terra:max` and `deepseek/deepseek-flash:max` sequentially in sibling
worktrees with the same tracked bytes and tool allowlist. Execution order is randomized.
Only one semantic Solidity candidate runs at a time. Original Minecraft artifacts/worlds
remain parent-only.

`metrics.ts` timestamps the provider-request hook, response headers, first reasoning delta,
first text/tool-action delta, message completion and tools with monotonic nanoseconds.
`summarize.py` reports per-request and aggregate TTFT, provider-reported input/output/cache
usage, model stream output tokens/s, UTF-8 bytes/s, tool calls/errors and durations.
Provider token units differ, so token throughput is accompanied by byte throughput. Model
stream speed excludes tool intervals; end-to-end wall includes them. HTTP/provider retries,
process failures and human interventions are separately retained in raw JSONL/run records.

For each task, automated verification records task/context manifests, diff files/lines,
tests added, existing/new gate outcomes, regression/TODO scans, tool traces and environment
versions. A failed mandatory machine gate is disqualifying regardless of judge score.

Three independent `openai-codex/gpt-5.6-sol:xhigh` judges receive anonymized A/B artifacts
in separately randomized order. They do not receive model, timing, token or price data.
Each scores both candidates with cited evidence on: correctness, architecture understanding,
minimality, robustness, maintainability and task completion. They also list blocker severity,
accept/reject and confidence. Aggregation uses per-dimension medians, disagreement/spread and
majority acceptance; ties remain ties. Judges assess qualities not established by machine
verification and never substitute for tests.

Anomaly records include duplicate reads/commands, no-op or failing tools, timeouts, retries,
unauthorized-path attempts, long no-event intervals, abandoned approaches, correction
latency, final-report/worktree mismatch and human intervention. Three tasks are a small
paired project sample, not a statistical-significance claim.
