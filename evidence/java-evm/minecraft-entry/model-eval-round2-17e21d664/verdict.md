# 第2轮双盲裁判结论

## 裁决

**唯一胜者：A**
**置信度：88%**

| 报告 | 事实正确（40） | 真实阻断（25） | 范围纪律（15） | 证据严谨（15） | 清晰（5） | 总分 |
|---|---:|---:|---:|---:|---:|---:|
| A | 39 | 23 | 14 | 14 | 5 | **95** |
| B | 37 | 11 | 12 | 14 | 5 | **79** |

## cap29 当前裁决

**拒绝当前提交的 cap29 source + generated evidence 验收。**

源码窄 delta 本身没有被核查出错误：`verify_source.py` 通过，engine/coordinator、driver
和 diagnostic 的 28→29 替换、81 bootstrap、各固定 cap 以及 artifacts 的代码哈希均相符。
这只足以支持“源码增量正确”的结论，不足以覆盖归档/复现验收。

A 找到的两项核心问题是真实阻断，而不是要求超出 generated gate：

1. `verify_receipts.js` 明确需要每个 world 的 `durable-head.json`、逐 slice report 和
   checkpoint blob；classcount29 的 Git-tracked artifacts 只有摘要、heads、日志和短 receipt
   输出，没有这些输入。因此 `verifiedReceipts: 264` 不能在当前归档中独立重放。
2. `tools/build.py` 与 `tools/gate.py` 硬编码当前 worktree 外的 `NODE_PATH`，归档命令还指向
   另一个 worktree 的 build 路径。当前 worktree 内没有这些 node_modules；这不是仅要求额外
   generated case，而是 source/artifact 的复现链断裂。

这些问题直接违反仓库关于关键复现状态不得只留在临时 build、应在 Git-tracked evidence 中
带哈希归档的纪律。B 虽然识别了同一缺口，却把它降为“不影响窄范围接受”，因而在本轮关键
判据上判断错误。parent 的 `SHA256SUMS` 缺失工作树中的 pyc 及拒绝路径 receipt 不对称是真实
瑕疵，但主要影响 parent/证据强度，不单独证明 cap29 源码错误；A 对其阻断等级略有扩大。

B 额外正确发现：所谓 `262144` case 实际以 `LC0StateError(1,0)` 在 1 MiB checkpoint
限制处回滚，并非 engine raw-byte parser 的正向边界证明；`262145` 才是 coordinator 的
`MR0Error(12)`。这是应修正文案/测试设计的非核心缺陷，不能抵消上述归档阻断。

## 只读核查

- `python3 -B evidence/java-evm/minecraft-entry/classcount29-preflight/tools/verify_source.py`：通过。
- 在 classcount29 `artifacts/` 内运行 `sha256sum -c SHA256SUMS`：71 项通过。
- parent `sha256sum -c SHA256SUMS`：因缺失 `__pycache__/checkpoint_frames.cpython-314.pyc` 失败；该 member 仅见于归档 tar。
- 静态检查 `verify_receipts.js` 的输入要求、classcount29 目录内容、build/gate 的绝对路径及
  262144/262145 refusal 记录；未构建、未提交、未访问原始 JAR/world、网络或其他 worktree。
