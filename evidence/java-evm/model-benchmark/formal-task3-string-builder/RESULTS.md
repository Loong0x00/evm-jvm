# Formal task 3/3 — bounded StringBuilder

Both corrected runs have clean instrumentation (`validForComparison=true`) and exited0, but both mandatory optimizer200 product builds exceeded LOCAL384, so both candidates are machine-ineligible and no blind judging/winner is declared.

| Metric | Terra/xhigh | DeepSeek V4.1 Flash/max |
|---|---:|---:|
| Outer wall | 1055.122 s | 972.593 s |
| Engine runtime | 395319 B (2103 over) | 395316 B (2100 over) |
| Java8 image | 542 B | 538 B |
| Requests | 49 | 121 |
| Input / output / cache-read tokens | 195763 / 35492 / 5643264 | 133213 / 122817 / 19174784 |
| Total tokens | 5874519 | 19430814 |
| Median first-any TTFT | 1845.975 ms | 1405.488 ms |
| Median first-action | 4692.541 ms | 2773.663 ms |
| Provider output throughput | 50.368 tok/s | 241.248 tok/s |
| UTF-8 throughput | 102.224 B/s | 860.138 B/s |
| Tool calls / errors | 62 / 3 | 147 / 2 |
| Provider-reported cost | $1.946083 | $0.302393 |

DeepSeek was 7.8% faster, had 23.9% lower median TTFT, 4.79x output-token throughput, and 84.5% lower reported cost, while consuming 3.31x total tokens and 2.37x tool calls. Terra's source used the correct final class flag and a 542-byte explicitly bounded non-null implementation; DeepSeek's 538-byte image omitted `final`. Neither difference overrides the mandatory runtime-cap failure.

The invalid 105.8-second harness-path launch is retained separately. Parent recovery is outside the formal comparison and is not a retroactive model win.
