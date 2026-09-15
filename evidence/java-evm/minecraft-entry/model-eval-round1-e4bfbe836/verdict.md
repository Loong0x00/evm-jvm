# 双盲裁决

## 结论

**唯一胜者：B**

**置信度：84%**

## 评分

| 报告 | 正确性（40） | 范围纪律（20） | 遗漏发现（20） | 可执行性（15） | 清晰度（5） | 总分 |
|---|---:|---:|---:|---:|---:|---:|
| A | 37 | 19 | 19 | 13 | 4 | **92** |
| B | 39 | 19 | 17 | 15 | 5 | **95** |

## 核查依据

仓库中的 classcount29 preparation 只授权 28→29 的窄增量：追加已测得的
StandardLevel（2239B，raw29 总计248169B），诊断上界110、隔离 LOCAL384、生成
28/29/30 门禁，且 original29 只能由父流程运行。classcount28 parent evidence
确认 245930B、3946 JVM/34 internal、568 receipts 及 StandardLevel blocker；其
对应源码显示三层独立计数约束：driver、coordinator constructor、engine
`startMain` 的 raw-class guard。现有 verifier 还明确保留81 bootstrap、11 native、
10 String-local、14 exception、128 frames、262144 raw-byte、1MiB checkpoint、
32768 Head 及393216 runtime cap。

## 报告 A

优点：准确复核了 blocker、字节算术、源码 delta，并发现了准备文档未明确写出的
反向 verifier、固定上限保真、reordered 门禁、JAR inventory、完整 refusal receipt
以及双评测择优规则等缺口；这些遗漏发现优于 B。

事实错误/不充分主张：

1. 报告末称 `git status --short` 只有 `build/dual-round1/`，但当前 worktree 实际是
   `?? build/blind/`，且没有该目录；这是可核查的状态错误/陈旧自证。
2. 建议把诊断上界写成“至少110”不够严谨。对应 classcount28 verifier 是精确的
   `assert classes<=109`，本轮应明确改为精确 `classes<=110`，不能用“至少”弱化
   只读门禁。
3. “255+ canonical receipts”是对未来 cap29 的无证据数量预期；现有证据明确的是
   classcount28 的255条，应要求同等 verifier/完整 receipt 校验，而不应预猜数量。

## 报告 B

优点：没有发现实质事实错误；严格限定源码替换，明确要求 runtime 393216B 尺寸门禁，
并补足了 A 未明确的三层拒绝测试：30 binding 的 driver 早拒、coordinator
constructor `MR0Error(2)`、engine `LinkError(1,30)`，均要求无状态变更。它还明确
保留262144 parser-infeasible 与262145 constructor refusal，不把生成 fixture 误当
original29 结果，执行性最佳。

遗漏/不足：没有像 A 一样明确指出 parent-b985a6add 缺少完整 StandardLevel refusal
receipt 和追加类的 JAR inventory 归档，也没有单独把“双路评测”的选择判据列为
文档缺口；因此遗漏发现分低于 A，但这些不影响其窄范围实施方案的可执行性。

## 裁决理由

B 在正确性和执行门禁上更稳，尤其将 coordinator 与 engine 的直接拒绝路径从 driver
早拒中分离出来，避免“源码证明”冒充 EVM 实测。A 的证据审计更全面，但存在当前
worktree 状态的明确错误、诊断上界措辞风险和未经证实的 receipt 数量预期。按加权
总分，B 以95比92胜出。

## 验证

只读检查了：

- `build/blind/candidate-A.md`、`build/blind/candidate-B.md`
- `JAVA_EVM_MC_CLASSCOUNT29_PREPARATION.md`
- `JAVA_EVM_MC_CLASSCOUNT28_PARENT_PREFLIGHT.md`
- classcount28 的 `verify_source.py`、source verification、pins、gate、summary
- parent-b985a6add 的 frontier、pins、源码及 SHA256SUMS

执行了 SHA256SUMS 校验、源码差异/计数检查、相关 guard 和诊断断言检索，以及
当前 `git status --short --branch` 检查。未访问父目录、其他 worktree、网络、原始
JAR 或 world；未修改受跟踪文件，未构建，未提交。
