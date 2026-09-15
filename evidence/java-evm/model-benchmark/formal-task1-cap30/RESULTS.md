# Formal task 1/3 — measured raw class cap30

## Outcome

Both candidates passed identical parent machine source builds and generated gates at `393205 / 393216` runtime bytes. Three independently run, position-counterbalanced Sol-xhigh blind judges unanimously **accepted Terra and rejected DeepSeek**. Terra is selected and integrated. The parent corrected only stale non-semantic diagnostic wording (`retained112` → cap30 `bound113`).

DeepSeek's product delta was machine-correct, but its runnable build/gate scripts hard-coded `/home/user/evm-jvm/geth/.../node_modules`, directly violating the frozen task's prohibition on accessing other worktrees. All three judges treated this as the acceptance blocker. Terra used worktree-relative dependencies, immutable parent hashes, exact 262144 refusal assertions, and canonical verification including reordered30.

## Candidate performance

| Metric | Terra/xhigh | DeepSeek V4.1 Flash/max |
|---|---:|---:|
| Outer wall | 1148.433 s | 802.179 s |
| Requests | 42 | 80 |
| Input / output / cache-read tokens | 188282 / 38240 / 4607488 | 140259 / 78429 / 11410432 |
| Total tokens | 4834010 | 11629120 |
| Median first-any TTFT | 2376.243 ms | 1499.286 ms |
| Median first-action | 7661.811 ms | 3127.029 ms |
| Provider output throughput | 51.580 tok/s | 241.952 tok/s |
| UTF-8 stream throughput | 97.107 B/s | 825.914 B/s |
| Tool calls / errors | 58 / 4 | 107 / 5 |
| Summed tool time | 297.369 s | 353.177 s |
| Provider-reported cost | $1.756942 | $0.204655 |

DeepSeek was 30.1% faster, had 36.9% lower median response TTFT, 4.69x token-stream throughput, and 88.3% lower provider-reported cost. It also consumed 2.41x total tokens and 1.84x tool calls. Performance did not override the explicit isolation failure.

## Blind score medians (three judges)

| Dimension | Terra | DeepSeek |
|---|---:|---:|
| Correctness | 9.6 | 8.5 |
| Architecture understanding | 9.5 | 9.4 |
| Modification minimality | 9.8 | 9.4 |
| Robustness | 9.5 | 8.8 |
| Maintainability | 8.8 | 6.8 |
| Task completion | 8.8 | 6.8 |

Per-judge scores, ranges/disagreement, private mappings, raw streaming metrics, tool counts, run records, and complete verdicts are retained below this directory. Neither candidate accessed original Minecraft artifacts; original30 remained parent-owned.
