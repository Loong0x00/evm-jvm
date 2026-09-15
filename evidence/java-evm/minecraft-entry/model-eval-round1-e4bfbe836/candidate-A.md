# 双模型盲测第1轮 — 独立审查报告（不含模型身份）

范围：只读审查当前 worktree。未访问父目录、其他 worktree、原始 Minecraft JAR/world，未联网，
未修改任何受跟踪文件，未构建、未提交。审查对象为
`JAVA_EVM_MC_CLASSCOUNT29_PREPARATION.md`、`JAVA_EVM_MC_CLASSCOUNT28_PARENT_PREFLIGHT.md`、
`evidence/java-evm/minecraft-entry/classcount28-preflight/**`、
`evidence/java-evm/minecraft-entry/parent-b985a6add/**`（source verifier / pins / frontier / receipt）。

---

## 1. 结论摘要

- **测得阻塞（cap28→29）可靠，且是当前唯一被记录的下一步边界。** 证据自洽、哈希可校验。
- **cap29 方案的实现范围（scope）充分且最小**：与已接受的 25→26→27→28 增量模式一致。
- **方案的验收文本不充分**：缺少若干在 25/26/27/28 中显式给出的门禁子项（反向 source verifier、
  reordered 包承诺、固定上限保真清单、JAR 成员校验），并且是首次引入“双评测择优”流程，
  该流程本身缺少可执行判据。
- **证据完整性缺口**：`parent-b985a6add` 归档未包含 StandardLevel 阻塞的原始 refusal receipt
  （selector/gas/root 不变性），也未包含为达到 28 所追加类的 JAR inventory verification。

---

## 2. 测得阻塞复核

来源：`parent-b985a6add/original28-frontier.json`（SHA256SUMS 第52行，已 `sha256sum -c` 通过）。

| 项 | 值 |
|---|---|
| profile | `MC-CLASSCOUNT28-PARENT1` |
| rawClassCount / rawBytes | 28 / 245930 |
| head | epoch 568, jvmSteps 3946, internalSteps 34, lifecycle 1, outcome 1 |
| q1Transitions | 5 |
| blocker | context `16`, name `org/apache/logging/log4j/spi/StandardLevel`, site `4103` |
| next | `.../StandardLevel.class`, 2239B, SHA256 `3302ed556149697655f1c6ee87f6f531a6b1ae1969f2321c9eb3ab3e67d6e836`, rawCount 29, rawBytes 248169 |
| claims | mainBody=false, world=false, done=false |

一致性检查（本机复算）：
- `245930 + 2239 = 248169`，与 frontier 的 `next` 一致；相对字节上限 `262144` 余量 `13975B`。
- `29 + 81(bootstrap) = 110`，与 cap29 准备文档“diagnostic bound110”一致。
- `blocker` 的 `site=4103` 与上一级 a1e9 frontier 中 Level 的 `site=4103` 相同（缺失类同一调用点），
  属真实的 EVM MissingClass 拒绝路径。

复核结论：**该阻塞是一次真实测得的 EVM refusal，cap28→29 的 2239B/248169B 数值自洽，可作为下一步边界。**
未测得的“再下一个阻塞类”不得在此推断。

`parent-b985a6add` 其余关键证据均通过 `sha256sum -c`：engine 388963B / runtimeSHA256
`2617cd04a81faa4050075cdf9f3969993e13d047f7bb07f1fac7721bd642a705` / runtimeKeccak
`b9511a4e6592fca77e480ad77e355d66b91ab9af9fa2c69dca2b7e485ef97e89`；coordinator 4146B /
runtimeKeccak `991df8cd08ab61c01bbf36429d7f76e27e36ce14c156d36d6673d6de9f6b2035`；
runtimeCap 393216；rawLimits `[28,262144]`；bootstrap81 / native11 / String-local10 / exception14 /
frames128 / reserve25M / externalLocalGas1e9。

`classcount28-preflight/artifacts/SHA256SUMS` 全部 `sha256sum -c` 通过，其 engine/coordinator 字节数
（388963/4146）与 parent28 一致；preflight 与 parent28 源码仅差 `PREFLIGHT1`↔`PARENT1` 标签与
preflight 地址/engine pin（已逐文件 diff 确认）。

---

## 3. cap29 方案是否充分

**范围充分（正确的最小增量）。** 与已验证的 count27→28 增量（`classcount28-preflight/tools/verify_source.py`
对 `parent-a1e9e0f64` 的严格反向断言）逐项同构：engine 只动 9 个域标签 + `MAX_RAW_CLASSES` +
DCFG 首字；coordinator 只动 3 域 + 4 个定长数组 + 1 处 `n>` guard + ENGINE 地址/codehash；
driver 只动 profile pin/地址/域/2 处 guard；diagnostic 只动 class 上界。
cap29 的 `isolated LOCAL384 domain`、`generated exact28/29 and30 refusal/boundary/canonical gates`、
`Parent alone runs original29` 均与既往接受模式相符。

**验收文本不充分。** cap29 准备文档相对 25/26/27/28 缺少以下显式条款（见第 5 节 R3/R4/R5），
且首次引入“双评测择优”，但未给出可执行判据。

### 3.1 精确 source delta（以 `parent-b985a6add` 已接受源码为基线）

**`MCEntryInterpreter.sol`（engine，388963B，字节数不变）**
1. 9 处标签替换：`MC-CLASSCOUNT28-PARENT1` → `MC-CLASSCOUNT29-PARENT1`，命中
   `EMPTY_ARGS_COMMITMENT`、`DROOT`、`DART`、`DBOOT`、`DCFG`、`DMACH`、`DSEED`、`DVFS`、`DFILE`。
2. `uint256 private constant MAX_RAW_CLASSES = 28;` → `= 29;`（仅定义行；两处使用处自动跟随）。
3. 执行配置首字：`uint32(28), uint32(262144), uint32(64), uint32(32), uint32(65536),` →
   `uint32(29), uint32(262144), ...`（字节上限 262144 不变）。
   其余 81 个 bootstrap 函数逐字节不变。

**`MCEntryCoordinator.sol`（coordinator，4146B，字节数不变）**
4. 3 处域标签替换：`PACKAGE_DOMAIN` / `RESOURCE_DOMAIN` / `VM_DOMAIN`，28→29。
5. 4 个定长数组容量 `[28]` → `[29]`：`decoders`、`resourceRoots`、`classSizes`、`rawNames`。
6. 构造 guard：`n == 0 || n > 28 || ...` → `n > 29`（仅 1 处）。
7. `ENGINE` 常量地址 → 新的 LOCAL384 隔离地址。
8. `ENGINE_CODEHASH` → 新 engine 的 runtimeKeccak256。

**durable driver（Go）**
9. `format` 字符串 28→29。
10. 3 个 pin：engine runtimeSHA256、engine runtimeKeccak、coordinator runtimeKeccak。
11. `owner` 地址、12. `engine` 地址。
13. `packageDomain` / `resourceDomain`（2 处），14. `fixture-instance/v1` 域（2 处）——共 5 处 profile 名。
15. 2 处 cap guard：manifest decoder 数 `> 28` → `> 29`，路径分段数 `> 28` → `> 29`。

**read-only diagnostic（`checkpoint_frames.py` / `checkpoint_diagnostic.py`）**
16. `assert classes<=109` → `classes<=110`（建议表述为“至少 110”，只读消费、不影响 EVM 语义）。

**不得改动**：81 bootstrap 镜像、native11、String-local10、exception14、`MAX_RAW_BYTES=262144`、
frames128、CP4096、Code65535、heap/VFS/checkpoint1MiB、Head32768、LOCAL1B/25M reserve/单次30s/
整轮20min/4GiB；accepted320 与 accepted27/28 工件不变。

---

## 4. 必须门禁（建议冻结为验收子集）

1. **反向 source verifier（硬门禁）**：对 `parent-b985a6add` 严格断言“仅第 3.1 节列出的变换”，
   并断言 81 bootstrap 函数逐字节相同、`globalNativeBindings==11`、`stringLocalBinding==10`、
   `exceptionKinds==14`、`rawLimits==[29,262144]`、`maxFrames==128`、`checkpointCap==1048576`、
   `headCap==32768`、`runtimeCap==393216`、`reserve==25000000`。
2. **engine/coordinator 新 pin**：engine runtimeSHA256/Keccak 与 coordinator runtimeKeccak 生成后回填
   driver 与 coordinator 锚点。
3. **生成门禁（Java8, `--release 8`）**：exact28 成功（q1/q7/direct q4096/reopen/canonical）、
   exact29 成功（同上）、**reordered29** 的 `packageRoot` 与顺序无关承诺区分、exact30 在世界目录创建前拒绝、
   `262144` 聚合字节的 parser-infeasible **如实记录**、`262145` 返回构造函数 `MR0Error(12)` 且
   `rootBefore==rootAfter`（原子、无部分状态）。
4. **canonical receipts**：255+ 条公开 checkpoint/event 的嵌套 ABI 重编码、CP 哈希、计数链与
   read-range 校验全部通过。
5. **fresh LOCAL384 构建**：watchdog ≤1200s / ≤4GiB，记录 peak RSS 与 pins。
6. **父流程独立重建**：真实 Java8-g:none 源码构建 + 重放生成门禁 + **父进程单独运行 original29**
   （仅追加 StandardLevel.class），q7 后 q1 推进到下一个**实测** refusal；失败时保 trie/head 不变。
7. **边界不变**：accepted4/65536 与 accepted320/27/28 不变；禁止 lazy load / 伪造类 / 读取失败状态恢复 /
   放宽上限 / push。

---

## 5. 潜在遗漏与风险

- **R1（证据缺口，中）**：`parent-b985a6add` 只归档了 `blocker{context,name,site}`，**未归档原始
  refusal receipt**（selector/gas/rootBefore/rootAfter）。对照 `parent-a1e9e0f64/original27-frontier.json`
  内嵌了 `q7Refusal{selector,diagnostic,gas,rootBefore,rootAfter}`。建议父流程在依赖该阻塞前补齐
  完整 refusal JSON 并纳入 SHA256SUMS。
- **R2（证据缺口，中）**：b985a 未归档“为达到 28 所追加类”的 JAR inventory verification
  （cap27 有 `original27-inventory-verification.json`，含 jarSHA256/addedName/addedBytes/addedSHA256）。
  cap29 依赖 frontier 对 StandardLevel 的 same-JAR 断言（2239B/SHA256）却无可独立复算的 inventory。
  建议父流程以 JAR 清单核验 `name/size/SHA256` 后再追加。
- **R3（欠规定，中）**：cap29 准备文档未显式要求反向 source verifier、reordered 门禁、
  固定上限保真清单（25/26/27/28 均写明）。仅写“Implement count28→29 only”，易被弱化。
- **R4（欠规定，低）**：未显式声明 accepted320 与 accepted27/28 工件必须保持不变（历史推定）。
- **R5（流程欠规定，中）**：“两路 Terra/V4.1-Flash 隔离评测、匿名、盲评、择优指定唯一语义写入者”
  未定义：相同只读输入集合、评测输出格式、验收判据与平局裁定。建议父流程冻结输入清单与选择规则。
- **R6（外部依赖，低）**：StandardLevel 2239B/SHA256 无法在本 worktree 独立复算（无 JAR/网络）。
  即使该成员尺寸略有差异，字节余量 13975B，29 类仍在 262144 上限内；但 rawBytes 数值需以 inventory 为准。
- **R7（表述，低）**：diagnostic 上界 110 仅为只读消费者，建议写“≥110”，并明确不构成 guest 限制。
- **R8（纪律）**：24→29 的历史模式显示每次追加后往往立即暴露下一个缺失类，但**本轮不得推测**
  StandardLevel 之后的下一个阻塞；须由父流程 original29 运行实测。

---

## 6. 父流程下一步

1. 完成本轮双路隔离评测并匿名盲评，按冻结判据指定**唯一**语义写入者。
2. 以 `parent-b985a6add` 为基线冻结第 3.1 节 delta 与第 4 节门禁（补齐 R3/R4/R5 条款）。
3. 写入者仅实现 28→29，产出反向 source verifier + 生成门禁 + LOCAL384 pins。
4. 父流程独立源码构建/重放/校验 receipts，随后**独自**运行 original29（仅追加 StandardLevel.class），
   q7→q1 推进至下一个实测 refusal；成功则记录接受，失败则保真失败证据、不迁移失败状态。
5. 补归档 StandardLevel 的完整 refusal receipt（R1）与追加类的 JAR inventory（R2）。

---

## 7. 审查自证

- 只读操作；`git status --short` 仅新增未跟踪的 `build/dual-round1/`。
- `sha256sum -c`：`parent-b985a6add/SHA256SUMS`（除未跟踪的 `__pycache__/*.pyc`）与
  `classcount28-preflight/artifacts/SHA256SUMS` 全部通过；`original28-frontier.json`、
  `original28-bindings.json`、`pins.json`、`verified-original28.json`、
  `candidate-source-verification.log`、`executed-driver.go.txt` 逐一比对通过。
- `parent-b985a6add` 与 `classcount28-preflight` 的 engine/coordinator 逐文件 diff 仅差
  `PREFLIGHT1`↔`PARENT1` 标签与 preflight 地址/pin；确认无隐藏语义变更。
- `verified-original28.json`：568 receipts / 3946 Java / 34 internal / peakGas 371817775 / lifecycle1。
