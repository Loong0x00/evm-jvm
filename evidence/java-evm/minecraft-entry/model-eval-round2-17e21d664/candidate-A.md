# Cap29 双模型盲测第 2 轮：独立审查

## 结论：拒绝当前 cap29 的“已提交 source + generated evidence”验收

28→29 的**源码窄 delta 本身通过**：以 `parent-b985a6add` 中四个被 pin 的输入为基准，engine、coordinator、driver、diagnostic 的反向替换均精确成立。engine 只将 raw class cap 28→29、相应 domain/commitment 改为 cap29；coordinator 的四个定长数组和构造上限为 29；driver 的上限/地址/哈希同步；诊断为精确 `classes<=110`。81 bootstrap、11 global native、String-local 10、14 exception kinds、128 frames、262144 raw bytes、1 MiB checkpoint、32768 Head、25M reserve 以及 1B LOCAL external gas 均仍由该 exact-delta 关系或 pin 约束。重新计算的 source/artifact SHA、init/runtime SHA、Keccak 和 pins 一致；engine 388963 B，距 393216 B LOCAL384 cap 尚余 4253 B。

生成门禁的**设计和已归档摘要**也覆盖了 28/29 的 q1、q7、direct，29 reordered，262144 与 262145 边界，以及 30 的 driver/coordinator/engine 三层：

* driver 是 `>29` 的 pre-world 早拒；
* product coordinator 的构造拒绝为 `MR0Error(2)`，并记录 `rootUnchanged`；
* 经仅为测试而机械放宽的 coordinator 到达 immutable product engine 后，engine 拒绝 `LinkError(1,30)`，并记录 `rootUnchanged`。

这两项不能弥补以下验收阻断问题。

## 阻断问题

1. **receipt verifier 的输入没有被归档，`264` 条“已验证”不能独立复核。**
   `tools/verify_receipts.js` 要求每个 world 的 `durable-head.json`、`reports/<label>/slice-*.json` 和每个 receipt 指向的 `checkpoints/<sha>.bin`，以重算 checkpoint SHA/Keccak、嵌套 ABI、event、计数链和逐片 DI0 read range。提交的 `artifacts/` 只有扁平的 `heads/*.json`、最终 `receipts/*` 摘要和 `canonical-receipts.json` 输出；没有上述 checkpoint 和逐 slice receipt 输入。因此 verifier 无法对已提交 evidence 执行。`canonical-receipts.json` 的 `verifiedReceipts: 264` 是未能从归档输入再现的断言，不是可复验 receipt 证据。

2. **构建/门禁不满足“仅当前 worktree”的可复现性。**
   `tools/build.py` 和 `tools/gate.py` 直接 pin `NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules`，而归档 `gate.log` 的所有可执行命令也指向 `/home/user/evm-jvm/mc-classcount29/build/...`。这些都是当前 worktree 外的绝对路径。因而“reproducible LOCAL384 build/generated gate”的证据不能在本 worktree 独立重跑；这也是越界依赖，而非已归档的、经 hash pin 的本地工具输入。

3. **parent evidence 的根 SHA256SUMS 不能按文件树直接验证。**
   `parent-b985a6add/SHA256SUMS` 和 `archive-files.json` 都列出 `__pycache__/checkpoint_frames.cpython-314.pyc`（SHA256 `732ed1…6293`），但该文件未 materialize 在该目录，故 `sha256sum -c SHA256SUMS` 失败。该 member 的确存在于 `parent-evidence.tar.gz` 且抽取后哈希匹配，不过该 tar 的 SHA256 未被同一 `SHA256SUMS` pin。四个实际反向 delta 输入的 SHA 均匹配 `parent-input.json`，所以这不推翻窄源码结论；但它破坏了所声称 parent evidence 的完整、单命令 checksum 验证链。

4. **拒绝路径的归档强度不对称。**
   `gate.py` 在执行时对 driver 早拒仅做 `assert not w.exists()`；提交 evidence 只留下 exit=2 的日志，没有一个可独立检查的 pre/post-root 或“world absent” receipt。coordinator/engine 的失败 JSON 提供了 root 值，但它们不在成功 receipt verifier 的覆盖范围。故“三层 30 拒绝均已独立、原子地证实”比现有可复核资料更强：源码和门禁脚本有该意图，已归档输入不足以独立复验全部三层。

## 非阻断但需保留的范围结论

* `262144` 是到 parser 的失败（不是成功边界），`262145` 是 coordinator aggregate constructor 的 `MR0Error(12)`；摘要没有把二者误称为成功。
* reordered case 只要求 package root 不同；没有错误地要求其 machine root 与原顺序相同。
* `verify_receipts.js` 自己明确 scope 为 canonical ABI/event/checkpoint/counter/read-range，且“not full Session acceptance”；不应扩大为完整 Session/transport 验收。
* 本审查未读取或推断任何 original29 后续执行结果；本结论仅针对已提交的 cap29 source 与 generated evidence。

## 最小返工条件

归档每个成功 world 的 verifier 输入（或一个被哈希 pin 的完整 tar 加独立 extractor/verifier）、三层 refusal 的可核对 pre/post-state 证据，并把 build/gate 所需 node 工具固定在当前 worktree 内或作为被 pin 的归档依赖；同时修复 parent evidence 的 checksum/tar 完整性链。完成后可在不改变已确认窄源码 delta 的前提下重新审查。

## 只读核对

* `python3 evidence/java-evm/minecraft-entry/classcount29-preflight/tools/verify_source.py`：通过。
* `sha256sum -c evidence/java-evm/minecraft-entry/classcount29-preflight/artifacts/SHA256SUMS`（在 artifacts 目录）：通过。
* `sha256sum -c evidence/java-evm/minecraft-entry/parent-b985a6add/SHA256SUMS`：失败，仅缺上述 pyc；从当前 worktree 内的 `parent-evidence.tar.gz` 抽取该 member 的 SHA 与清单一致。
* 对四个 source 输入执行 parent→cap29 unified diff，并核对 artifacts JSON 中 source hash、init/runtime SHA、Keccak 与 `pins.json`：一致。
* 仅读取当前 worktree；未构建、未改动受跟踪文件、未提交，未访问原始 JAR、world、网络或其他 worktree。
