# 双盲第2轮独立审查报告：raw-class cap29 source + generated evidence

审查对象：本 worktree `mc-cap29-r2-deepseek`（分支 `mc-cap29-r2-deepseek`）的
提交 `d569188e0`（stage measured raw class cap 29 source）与 `17e21d664`（archive
raw class cap 29 generated evidence），基准为 `b985a6add`（accepted raw class cap 28
generated evidence）。

审查方法：只读。仅访问当前 worktree；未访问父目录/其他 worktree/原始 JAR/world/
网络；未修改任何受跟踪文件，未构建，未提交。所有哈希在本机独立重算，selector 用
自实现 Keccak-256 重算（已用空串 `c5d24601…` 与 `Transfer(address,address,uint256)`
`0xddf252ad…` 向量自检）。

---

## 一、结论

**接受（限定于“cap29 预检源为严格 28→29 增量、且生成的 28/29/30 门禁通过”这一
窄范围），附若干非阻断缺陷。**

- 未发现 cap29 证据自身声称范围内的**事实错误**：
  - 反向 delta 与 parent-b985a6add 逐字节精确一致；
  - 除 raw 上限与域/地址/引擎 pin 外，所有固定限制未变；
  - 三层 30 拒绝、28/29 各模式等价、拒绝原子性均真实成立；
  - artifacts 与 staged source/pins 的 bytes、SHA256、Keccak 全部吻合。
- 但存在**测试覆盖与可复现性漏洞**（见第三节 P1–P5），其中 P1 涉及一处**不精确的
  实现注释**，P2/P3 涉及证据完整性。它们不推翻上述窄范围结论，但足以要求在把这些
  证据当作更广结论（尤其 original29）依据前先补齐。

**明确不推断**：本报告不推断 original29 的任何后续执行结果、不声称 Minecraft/
world/Done/EULA/客户端连接。cap29-preflight 全程为生成的 `CountMain`/`Tail*` 夹具，
不含任何原始类；准备的 `StandardLevel.class`（2239B，SHA256
`3302ed556149697655f1c6ee87f6f531a6b1ae1969f2321c9eb3ab3e67d6e836`）只有算术
预测（245930+2239=248169），未见执行证据。

---

## 二、已独立核实为真的项目

### 2.1 反向 delta（严格）

以 `parent-b985a6add/artifacts/*` 为基，逐文件 diff 与 `tools/verify_source.py`
（独立运行，exit 0）一致：

| 文件 | 允许的替换 | 实测 |
|---|---|---|
| engine `MCEntryInterpreter.sol` | 域标签 `MC-CLASSCOUNT28-PARENT1`→`MC-CLASSCOUNT29-PREFLIGHT1`（9处）、`MAX_RAW_CLASSES = 28`→`29`、`uint32(28), uint32(262144)`→`uint32(29), …` | 完全一致，无其他改动 |
| coordinator `MCEntryCoordinator.sol` | 3 域、`[28]`→`[29]`（4处）、`n > 28`→`n > 29`、`ENGINE` 地址、`ENGINE_CODEHASH` | 完全一致 |
| driver `tools/Go.txt` | 域（5处）、`> 28`→`> 29`（2处，含 manifest 校验与 argv 守卫）、owner/engine 地址、engine SHA/Keccak、coordinator Keccak | 完全一致 |
| diagnostic `tools/checkpoint_diagnostic.py` | `classes<=109`→`<=110` | 完全一致 |

- `parent-input.json` 的 4 个 SHA256 与 parent 实际文件一致：
  engine `e9b36a78…`、coordinator `af400997…`、`executed-driver.go.txt` `d9a38890…`、
  `checkpoint_frames.py` `8a4c2dea…`。
- 81 个 `_bootstrap*` 十六进制镜像在 parent 与 staged 间**逐字节相同**（另有非镜像
  辅助函数 `_bootstrapRoot()`，其 `new bytes32[](81)` 引用全部 81 个镜像，故
  bootstrapCount=81 成立）。

### 2.2 artifacts / pins / source 一致性

- engine JSON `codeHashes` 与 `pins.engine` 全等：388963B，init `93984e61…`，
  runtimeSHA `7492348c…`，runtimeKeccak `982223439041411fc9d8b8a4586386ea7e2ff335f6396bd52e01ed05b93d6faf`。
- coordinator JSON 与 `pins.coordinator` 全等：4146B，init `77688b0d…`，
  runtimeSHA `92aaa8eb…`，runtimeKeccak `ebe274142f6eb10ff690bdd956c1b7b3ad6849725d2b309d24542b20e1df0d80`。
- `runtime.hex` 重算 SHA256 与 pins 一致；artifacts JSON `sourceHashes` 等于 staged
  `.sol` 实算 SHA256（engine `9a55dc09…`、coordinator `75756534…`）。
- `acceptedParentEngine`/`acceptedParentCoordinator` 等于 parent-b985a6add 的 pins，
  且后者与 parent artifacts 实算一致（388963B/`2617cd04…`/`b9511a4e…`，4146B/`6e4add4b…`/`991df8cd…`）。
- 注意 parent 与 staged 的 engine/coordinator **字节数完全相同**（388963/4146），
  与“仅常量替换”一致。

### 2.3 固定限制未变

parent 与 staged `pins.json` 逐字段比较，仅以下变化：`basis`、`domain`、`address`、
`owner`、`rawLimits` 28→29、engine/coordinator hashes、新增 `profile`/`checkpointCap`/
`headCap`/`acceptedParent*`/`parentEvidence`。其余全部保持：
`bootstrapCount=81`、`globalNativeBindings=11`、`stringLocalBinding=10`、
`exceptionKinds=14`、`maxFrames=128`、`checkpointCap=1048576`、`headCap=32768`、
`runtimeCap=393216`（LOCAL384，build.js 强制 `runtime<=384KiB`）、
`externalLocalGas=1000000000`、`reserve=25000000`、`resourceLookupGas=1000000`。
engine 中 `MAX_RAW_BYTES=262144`、`new bytes32[](81)`、`new uint256[](14)` 未变。

### 2.4 三层 30 拒绝（独立路径，均原子）

- driver：`30-driver-pre-mutation-refusal` exit=2，world 目录不存在（`fixtureNames`
  在任何 `newEnv` 之前 panic）。gate 断言 `not w.exists()`。
- coordinator：`30-coordinator-atomic-refusal` → `MR0Error(2)`（`0xab23ed08…0002`），
  rootBefore==rootAfter；使用**产品** coordinator（仅临时 clone driver 放宽 argv 守卫）。
- engine：`30-engine-atomic-refusal` → `LinkError(1,30)`（`0x427cfac5…0001…001e`），
  rootBefore==rootAfter；使用**产品** engine，仅以临时放宽容量的 disposable
  coordinator 触达 engine。
- selector 名称经自算 Keccak 确认：`MR0Error=0xab23ed08`、`LinkError=0x427cfac5`、
  `LC0StateError=0x71540d20`。

### 2.5 28/29 各模式与 reordered

- 28：q1 epoch112/jvm112、q7 epoch16/jvm112、direct epoch1/jvm112；
  29：q1 116/116、q7 17/116、direct 1/116。三者 machineRoot 与
  `cp[280:]` 不透明载荷 SHA256 各自相等（量子不变）。
- 29-reordered：packageRoot 与 direct 不同（`0xad3a4907…` vs `0xe7a899ec…`），
  machineRoot 不同（`0x517de238…` vs `0x218368e7…`），不透明体相同，reopen 成功。
- 全部 26 条 gate 命令 exit 符合预期；`gate.log` 结果逐条与归档 `heads/*.json`
  的 epoch/jvm/machineRoot 吻合。

### 2.6 边界原子性

4 个拒绝路径均 `rootUnchanged=true` 且 rootBefore==rootAfter：
`29/262144`（`0x71540d20…0001…0000`）、`29/262145`（`MR0Error(12)`
`0xab23ed08…000c`）、`30/coordinator`、`30/engine`。

### 2.7 证据完整性（基本）

- `artifacts/SHA256SUMS`：71/71 全部成功，且恰好覆盖 artifacts 下除自身外全部 71 个文件。
- cap29 证据内**零** `.class/.jar/.zip/.bin` 载荷；无 `StandardLevel`/`log4j`/
  `net/minecraft` 等原始名。
- `verify_receipts.js` 与 parent 版本逐字节相同（`7356b4a0…`）。
  `canonical-receipts.json` 总 264 条，逐 world 与 `gate.log` 的 epoch/jvm 完全吻合。

---

## 三、发现的问题（事实层面 / 测试漏洞 / 不精确声称）

**P1（中，不精确声称 + 实际测试漏洞）：262144“边界”并非 raw-byte parser 边界。**
staged `tools/gate.py` 注释称 “Exact aggregate byte boundary reaches the honest
parser”。但实测该夹具（29 类、合计恰 262144B、单类 257557B，含 5 个约 65000 字符的
静态 String 填充）在**首个 checkpoint 提交**阶段以 `LC0StateError(1,0)`
（`0x71540d20…0001…0000`，即 1MiB checkpoint 容量上限）回滚，而非 engine 的
`total > MAX_RAW_BYTES`（其语义为 `>` 262144，恰 262144 应通过）拒绝。
因此：
- engine 的 raw-byte 上限路径在 262144 侧**未被正向证明可接受**；确切边界只在
  +1 侧由 coordinator `MR0Error(12)` 证明；
- 由于填充全堆入单类，coordinator 的单类上限 `size > 262144`（`MR0Error(11)`）
  **从未被任何 fixture 触发**，该守卫无覆盖。
- 该行虽被诚实标注 `infeasible`，但注释“reaches the honest parser”会误导读者以为
  parser 本身是边界判据。属应修正的表述/测试设计缺陷，不改变“+1 被拒”的事实。

**P2（中，可复现性）：receipt verifier 的输入未归档，且 gate 未调用它。**
`canonical-receipts.json`（264 条）由 `tools/verify_receipts.js` 产出，但其需要的
world 目录（`durable-head.json`、`reports/slice-*.json`、`checkpoints/*.bin`）全部位于
未提交的 `build/` 下；`tools/gate.py` 也未在任何位置调用 `verify_receipts.js`（对比
其它阶段有 `smoke.py` 调用）。因此从提交证据只能做“与 gate.log 数值自洽”的核对，
无法独立重放 264 条 receipt。此限制与 parent-b985a6add（仅归档 verifier 输出
`verified-original28.json`）相同，属既有惯例，但对“同等 verifier/完整 receipt 校验”
的要求构成未闭环项。

**P3（低，证据完整性）：staged 源/工具本身无校验清单。**
`artifacts/SHA256SUMS` 只覆盖 `artifacts/` 下 71 个文件；`engine/*.sol`、
`coordinator/*.sol`、`tools/*`、`pins.json`、`parent-input.json`（共 13 个文件）
不在任何 SHA256SUMS 中，仅依赖 git 对象哈希。parent-b985a6add 则用覆盖全树的
SHA256SUMS。cap29 应补一份覆盖源与工具的清单。

**P4（低，跨阶段档案错误，非 cap29 自身）：** 紧邻的 `classcount28-preflight/artifacts/README.md`
把同一 262144 回滚写成 “honestly parser-infeasible (`LinkError(1,0)`)”；
该 selector 实为 `LC0StateError(1,0)`（`LinkError` 是 `0x427cfac5`，`LC0StateError`
是 `0x71540d20`）。cap29 的 `gate.py` 断言 selector `0x71540d20` 正确，但注释仍不精确，
建议统一措辞并在文档中说明真实机制为 1MiB checkpoint 上限。

**P5（低，来源/可复现细节）：**
- `classcount29-preflight` 无 `README.md`（cap28-preflight 有），因此没有对“生成本
  门禁、未跑 original29”的显式范围声明；范围声明目前仅见于仓库根
  `JAVA_EVM_MC_CLASSCOUNT29_PREPARATION.md`。
- `pins.json` 的 `worker` 字段等于基准提交 `b985a6add`（非 worker 标识），`basis`
  与 `worker` 相同，语义含糊。
- 归档的 `logs/*.json`、`build.log` 命令路径指向**兄弟 worktree**
  `/home/user/evm-jvm/mc-classcount29/…`；`build.py`/`gate.py` 还硬编码依赖
  `/home/user/evm-jvm/geth/jvmevm/runtime/node_modules`。即证据是在另一 worktree
  且借助外部 node_modules 生成的；在当前 worktree 内无法原样重放（需重建/改路径）。
- `gate.log.wholeGateSeconds=36.987637836` 与 `gate.monitor.json.elapsedSeconds=37.016815332`
  相差 0.029s（前者为脚本内计时、后者为进程外部计时），属正常计时差，非篡改。

---

## 四、对“越界/不实”的结论

- **未发现越界**：staged 源只改 cap/域/地址/pin/诊断上界；gate 的 disposable probe 与
  放宽 driver 均在未提交 `build/` 内生成，产品 pins 未被改写；未触碰 consensus core、
  已接受 profile、100M/1B、25M reserve、320KiB/384KiB 之外任何上限。
- **未发现 cap29 证据对结果的伪造**：`gate.log` 与 `heads/*.json`、
  `canonical-receipts.json`、fixtures JSON 四方自洽；refusal 的 rootBefore==rootAfter
  与 selector 均可重算确认。
- **唯一“不精确声称”** 是 P1 中 262144 边界的实现注释（以及 P4 的跨阶段 README
  错误），均不影响“30 拒绝、28/29 接受、+1 拒绝、原子性”这些被断言并归档的结论。

---

## 五、附：本报告执行的关键只读校验

- `git status --short`（仅 `?? build/dual-round2/`）；`git diff --stat b985a6add HEAD`。
- `diff` parent→staged 的 engine/coordinator/Go/checkpoint_frames；
  `python3 -B tools/verify_source.py`（exit 0）。
- `sha256sum -c`：cap29 artifacts 71/71；parent SHA256SUMS 57/58（缺
  `__pycache__/checkpoint_frames.cpython-314.pyc`，为未提交 pyc，属 parent 既有小瑕疵）。
- 重算 engine/coordinator JSON `codeHashes`、`sourceHashes`、`runtime.hex`；
  校验 `pins.json` vs `build.json`（全等）。
- 解析 `gate.log` / `gate.monitor.json` / `canonical-receipts.json` / fixtures JSON /
  `heads/*.json`，交叉核对 epoch、jvm、machineRoot、packageRoot、selector、words。
- 自实现 Keccak-256 重算 `MR0Error`/`LinkError`/`LC0StateError` selector。
- 全目录扫描确认无 `.class/.jar/.zip/.bin` 原始载荷。

（本报告不含任何模型身份信息。）
