> 历史P39停机快照：用户随后已明确授权继续，且重启核验通过。当前进度与active worker见 `JAVA_EVM_MC_RESUME_STATUS.md`；不要把下文旧暂停指令当作当前要求。

# 按用户要求停机交接：P39 HashMap.put 已完成

用户要求：**完成当前 HashMap.put 阻塞后就停，准备重启电脑。** 本轮不继续下一个阻塞；必须等用户重启后明确要求再恢复。

## 已保存的验收点

- 仓库：`/home/user/evm-jvm/geth`，分支 `java-on-evm`。最终同步提交以 `git log -1` 和 `evidence/java-evm/minecraft-entry/parent-hash-map-put/artifacts/github-sync-accepted-p39.json` 为准。
- P39解释器418986字节，SHA256 `694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6`。
- 105个bootstrap镜像，根 `ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd`；native21/String12不变。
- 原版仍为90类/658601字节；**1974606 JVM指令、98内部步、36份验证成功收据**。
- 实际HashMap5980已完成22次put：22个真实Node，Node[32]，size/modCount22，threshold24；原始枚举初始化器已返回。
- 下一处是原子q1缺少`bdc`，**没有测量/加入其资源，也没有启动P40**。

## 不可丢失的本地路径

```text
成功世界：
/home/user/evm-jvm/geth/build/java-diff-mc-hash-map-put-original90-parent-p39/official

最后成功检查点：
/home/user/evm-jvm/geth/build/java-diff-mc-hash-map-put-original90-parent-p39/official/checkpoints/865ec98871892c0d359acada9719a261e7b23cd7f3c3d1d96c0dc093b1dc78dc.bin

独立构建：
/home/user/evm-jvm/geth/build/java-diff-mc-hash-map-put-build-parent-p39

原版专用授权驱动：
/home/user/evm-jvm/geth/build/java-diff-mc-hash-map-put-original-authorized-parent-p39

原版精确回放记录：
/home/user/evm-jvm/geth/build/java-diff-mc-hash-map-put-original90-precise-parent-p39

已归档验收证据：
/home/user/evm-jvm/geth/evidence/java-evm/minecraft-entry/parent-hash-map-put/artifacts

原始JAR（绝不改写）：
/home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar
```

检查点：epoch36/lifecycle1，1133360字节，SHA256 `865ec98871892c0d359acada9719a261e7b23cd7f3c3d1d96c0dc093b1dc78dc`。
原始JAR SHA256：`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`。

Git保存源码和选定验收记录，**不代表全部本地build世界或原始JAR已上传**。重启不需要删除任何目录。不要执行clean/reset，不要覆盖旧世界/失败记录。

## 重启后先验证，不要直接推进

```sh
cd /home/user/evm-jvm/geth
git status --short --untracked-files=no
git log -3 --oneline
git diff --exit-code 95665d570 HEAD -- core/vm core/state params
export NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules
node evidence/java-evm/minecraft-entry/parent-hash-map-put/verify_original.js \
  build/java-diff-mc-hash-map-put-original-authorized-parent-p39 \
  build/java-diff-mc-hash-map-put-original90-parent-p39 1 official
sha256sum build/java-diff-mc-hash-map-put-original90-parent-p39/official/checkpoints/865ec98871892c0d359acada9719a261e7b23cd7f3c3d1d96c0dc093b1dc78dc.bin
```

需要验证持久化世界时，可使用同一授权驱动的`verify`模式；它不推进guest：

```sh
build/java-diff-mc-hash-map-put-original-authorized-parent-p39/driver verify \
  "$PWD/build/java-diff-mc-hash-map-put-original90-parent-p39/official" \
  "$PWD/build/java-diff-mc-hash-map-put-original-authorized-parent-p39/coordinator/MCEntryCoordinator.json" \
  "$PWD/build/java-diff-mc-hash-map-put-original-authorized-parent-p39/engine/MCEntryInterpreter.json" \
  /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar 1
```

只有用户再次允许推进后，才处理`bdc`：原始资源仍须经EVM AS0/ZI0/DI0验证、显式加入绑定。**包或代码变化必须全新启动；不可把当前90类检查点迁到91类/新代码。** 失败状态和诊断输出也不是继续执行的授权。

## 停止状态和边界

- 两个语义worker已取消并保留全部文件；只读复核worker已完成，无修改。
- 最终相关进程检查记录在`evidence/java-evm/minecraft-entry/parent-hash-map-put/artifacts/reboot-process-check.json`；若存在不认识的进程，先核查，不要误杀用户无关任务。
- 底层geth EVM/gas/state/共识规则未改。解释器仍是超大LOCAL预装代码，不是标准CREATE部署；检查点不是真实挖块。
- 尚未到世界准备、EULA/配置启动、监听或Done。
- GitHub仅允许非force推送`origin/java-on-evm`（Loong0x00/evm-jvm），不推upstream或其他分支。
