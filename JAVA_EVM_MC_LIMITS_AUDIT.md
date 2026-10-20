# 当前 Minecraft LOCAL 主线自定义限制盘点

## 口径与结论

基准是最后通过原版回放的 **P28**，不是全仓历史实验版本：`evidence/java-evm/minecraft-entry/parent-raw75-byte531965/artifacts/engine/MCEntryInterpreter.sol`。源码 SHA256 `005bb1d6d2e1355956cbaff5ea5fd3c5838b7f328fee030c88836444951ceb70`。

**至少46项可区分的数值配额/预算，其中31项在核心解释器。** 同一用途跨Solidity/Go的重复检查不重复计数；派生handle/page数、JVM/EVM/DEFLATE本身的格式范围、没有被执行路径使用的旧gas标签不计。核心中若干无引用常量对应的同值字面量守卫仍有效，已标明。上层更小限制可能覆盖下层限额；这个46不是对所有限制的穷尽计数，额外API输入守卫、协议形状和未实现功能另列。

用户新授权的 **LOCAL1M runtime上限1048576bytes** 尚待新档执行验收；已接受P28及旧LOCAL384构建器仍是393216。1MiB代码上限与现有1MiB checkpoint上限是两件事，本次未修改任何旧执行配额。

## 数值清单（按用途去重）

| # | 层 | 用途 | 当前值 |
|---:|---|---|---:|
| 1 | engine | 每个class常量池槽位 | 4,096 |
| 2 | engine | 每个Java帧操作数栈容量 | 1,024 |
| 3 | engine | 每个Java帧局部变量容量 | 1,024 |
| 4 | engine | Java帧/初始化续帧总深度 | 128 |
| 5 | engine | 普通数组累计配额 | 4,096 |
| 6 | engine | 单数组长度 | 65,536 |
| 7 | engine | 普通数组元素总配额 | 262,144 |
| 8 | engine | 普通对象累计配额 | 4,096 |
| 9 | engine | 字段/单对象继承字段槽上限 | 1,024 |
| 10 | engine | 普通对象字段槽总配额 | 65,536 |
| 11 | engine | 异常arena对象配额 | 256 |
| 12 | engine | 异常arena字段槽总配额 | 262,144 |
| 13 | engine | 方法异常表条目 | 256 |
| 14 | engine | intern字符串记录配额 | 1,024 |
| 15 | engine | 每包声明原始类数 | 75 |
| 16 | engine | 声明类字节总量 | 531,965 |
| 17 | engine | 完整checkpoint字节数 | 1,048,576 |
| 18 | engine | 引擎启动seed文件数 | 16 |
| 19 | engine | 引擎启动seed数据合计 | 65,536 |
| 20 | engine | VFS节点数 | 64 |
| 21 | engine | VFS描述符数 | 32 |
| 22 | engine | VFS单文件数据 | 65,536 |
| 23 | engine | VFS全部文件数据合计 | 65,536 |
| 24 | engine | VFS单路径段字节数 | 64 |
| 25 | engine | VFS路径层级 | 16 |
| 26 | engine | VFS路径总字节数 | 256 |
| 27 | engine | VFS/inspectFile单次传输字节数 | 4,096 |
| 28 | engine | 单slice JVM步骤 | 65,536 |
| 29 | engine | 单slice内部步骤 | 4,096 |
| 30 | engine | gas下界/提交预留检查 | 25,000,000 |
| 31 | engine | 资源存在查询回调固定gas预算 | 1,000,000 |
| 32 | coordinator | 协调器绑定非class资源数 | 1 |
| 33 | coordinator | 协调器绑定非class资源字节 | 4,096 |
| 34 | artifact | 本地解释器runtime验收 | 393,216 |
| 35 | driver | 单次EVM调用取消watchdog | 30 |
| 36 | tests | 普通生成测试单call gas | 1,000,000,000 |
| 37 | tests | 普通生成门总时长 | 1,200 |
| 38 | AS0/ZI0 | 原始ZIP/JAR大小 | 33,554,432 |
| 39 | ZI0 | ZIP条目数 | 32,768 |
| 40 | ZI0 | ZIP中央目录字节数 | 4,194,304 |
| 41 | ZI0/DI0 | ZIP资源名长度 | 256 |
| 42 | ZI0 | ZIP extra字段长度 | 1,024 |
| 43 | ZI0 | ZIP中央目录单条目comment字段长度 | 1,024 |
| 44 | DI0 | 单资源解压输出/单class传输 | 262,144 |
| 45 | DI0 | 单次解压step工作预算 | 128 |
| 46 | AS0/DI0/coordinator | 认证资源单次read片段 | 4,096 |

每行可追溯源码和行号见 `evidence/java-evm/minecraft-entry/limits-audit/current-numeric-policies.json`。大小默认bytes；步骤、对象数、条目数等按用途说明。

## 当前最值得注意的瓶颈

- **VFS全部文件数据合计64KiB，单文件64KiB，节点64/描述符32。** 这是小型预检/原型规模，不是正常Minecraft世界数据容量规划。VFS不是宿主磁盘透传。
- **对象4096、数组4096、元素合计262144；没有通用GC。** 分配计数随分配累计，checkpoint序列化所有已分配handle，不是像成熟JVM按堆内存+GC回收。此前1024/2048上限已经造成真实guestOOM。
- **checkpoint1MiB，当前原版前沿1019131bytes，已约97.2%。** 这与代码runtime上限无关。
- **声明类75/总字节531965，而整个JAR已约28.8MiB。** EVM能索引原始JAR，但当前协调器只暴露预先绑定的类，未提供通用自动类加载；每加一类仍需构建新包。JAR大小是压缩归档口径、类预算是所选条目解压后合计，不能直接据此算覆盖率。
- **构造器只允许一个选定的非class资源，最多4KiB。** 引擎内部seed接口的16文件/64KiB限制并不意味着当前协调器已提供多文件启动配置。
- **外层max-gas不会消除内层所有预算。** 例如资源查询staticcall仍固定1Mgas，提交gas阈值25M；30s watchdog仍会取消长call。

## 功能边界：不能靠调大数字解决

- 当前是有限JVM/JDK原型，不是完整OpenJDK。P28只有97个bootstrap镜像，很多类也只有一小段API。ArrayList仍未通过执行验收；现有Random是构造/link-only；Thread是单guest currentThread，没有完整调度器。
- 通用反射、JNI、线程/同步、网络及完整java.io/java.nio没有成体系覆盖。字节码集也不完整，例如invokedynamic不是已实现执行指令。
- String.split仅接受`-|\.`，Locale.ROOT转小写仅ASCII；Math.sin/cos只支持有限abs<=2pi，asin有限abs<=1，部分特殊输入明确拒绝，不是完整Math语义覆盖。
- main入口固定空String[]；没有通用命令行/classpath/任意JAR动态加载。重放环境固定block1/time1，不等同普通Java进程的宿主时间环境。
- VFS路径仅可打印ASCII；ZIP/JAR使用受限STORED/DEFLATE解析档，非任意ZIP特性支持。
- 协调器classCount/classBinding索引是uint8，checkpoint还有u16计数等自定义线格式。超过255类或65535计数不是只改一个MAX值就能正确支持，需要有版本化的协议调整。

## 硬编码/技术债

`MAX_FILE_BYTES`、`MAX_ALL_FILE_BYTES`、`MAX_PATH_COMPONENT`、`MAX_PATH_DEPTH`、`MAX_PATH_BYTES`在该引擎只有声明，没有引用；实际守卫直接写65536/64/16/256，Go驱动还有重复校验。代码体积阈值在JS构建器，类包限制又在引擎、协调器、Go三层。它们并非统一可配置profile；逐个撞墙再改会导致多次编译/重放，也存在漏改风险。

## 不应混同为可随意删除的限制

- JVM方法Code长度65535、数组rank255、classfile字段位宽，以及EVM原生规则，不算上面的自定义配额。标准链EIP170的24576-byte代码/EIP3860的49152-byte initcode与LOCAL大解释器档必须区分，不能声称放宽LOCAL就兼容标准链。
- 身份/owner、包和codehash承诺、认证资源读取、CRC/root验证、原子拒绝、只从成功checkpoint续跑是正确性/信任边界，不是应为提速删除的容量预算。

## 未穷尽项与下一步

API专属名字长度、入口名ASCII/256、args codec8等额外守卫不计入46；每个未实现方法也未虚报成一个准确总数。历史4GiB测试内存目标是否被当前每条脚本统一强制，尚未验证，因此不作为已生效限制报告。

本次是只读盘点，不是偷偷一键放宽全部限制。合理后续是：把容量/吞吐预算与格式约束/API缺口分别管理；按Minecraft测试规模统一规划LOCAL profile，减少一类一改；保留旧档与证据，不删除认证/原子性保护。扩大配额不能替代标准库和线程等功能实现。
