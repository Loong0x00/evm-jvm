# 廉价隔离只读预审：java/lang/Enum bootstrap 82

预审人：隔离 read-only worker（DeepSeek 角色）。
范围：仅当前 worktree `/home/user/evm-jvm/mc-enum-bootstrap-review-ds`（分支
`mc-enum-bootstrap-review-ds`，HEAD `94757de1b`，`git status --short` 为空、无改动）。
本预审**未构建、未编译、未运行 solc/node/go、未提交**，只读读取仓库内文件与
`grep`/`diff`。未访问父目录其他 worktree、网络、原始 JAR、`classes/`、world。

约束提醒（沿用父级口径）：`MCEntryInterpreter.sol` 中
`bytes32[81]`/`inputCount + 75` 是 bootstrap 计数权威点；generic runtime
`jvmevm/runtime/JVMSubsetInterpreter.sol`（保留 `0xe000` 策略）**不在本阶段**。
**本报告不预测 original29 在加入 Enum 之后的下一个阻塞**；只给最小真实方案、
精确改动点、raw 替换保留规则与门禁清单。

---

## 1. 当前坐标系（已核对）

- 接受父本（Enum flag admission）：`evidence/java-evm/minecraft-entry/parent-9453ebd08/artifacts/engine/MCEntryInterpreter.sol`
  - domain `MC-ENUM-FLAG-PARENT2`，address `0x4d432d454e554d2d504152454e54320000000001`
  - engine `388963B`，runtimeSHA256 `50c5cd6ffefd559658b7c879bf4763b70b6336d1eaf7f6702fc13b609f5698da`，
    runtimeKeccak `db5607160a3e035397de19a287fef688e7c34c92d0f5e2d2ee834201815f0f1a`
  - `bootstrapCount = 81`，`rawLimits = [29,262144]`，`globalNativeBindings = 11`，
    `stringLocalBinding = 10`，`exceptionKinds = 14`，`maxFrames = 128`，
    `checkpointCap = 1048576`，`headCap = 32768`，`runtimeCap = 393216`，
    `externalLocalGas = 1000000000`，`reserve = 25000000`
- worker 阶段源 `evidence/java-evm/minecraft-entry/enum-flag-preflight/engine/MCEntryInterpreter.sol`
  与父本**逐字节差异仅 9 处 domain 串**（`PARENT1` ↔ `PARENT2`），行号/结构完全一致。
  下面行号以父本/阶段共同结构为准（两者行号相同）。
- 已确认无任何 `java/lang/Enum` 字面量、无 `_bootstrapEnum`、无 Enum reserved 谓词。
- 已确认 `Acc_ENUM` 准入：L3003 `if ((c.accessFlags & 0x0200) == 0 && (c.accessFlags & 0xa000) != 0) c.unsupportedSemantics = true;`
- 现状证明：genuine StandardLevel 在 `_validateHierarchy` 的 `_findClass(child.superName...)`（L6329-6333）
  解析超类 `java/lang/Enum` 失败 → `HierarchyError(1, 28)`。**Enum 缺失是唯一直接原因。**

### 现有 81 image 机制（必读）

- `_bootstrapRoot()`（L609-702）：`bytes32[] memory h = new bytes32[](81);`（L610），
  `h[0..80]` 逐个 `keccak256(_bootstrapXxx())`；已 append-only 到 tail：
  `h[79]=Queue`（L699）、`h[80]=ConcurrentLinkedQueue`（L700），`return keccak256(abi.encode(DBOOT, h));`（L701）。
- `_configRoot()`（L596-607）内嵌 `_bootstrapRoot()`，故 bootstrap 根影响 config root。
- `_prepare()`（L706+）：
  - `inputCount = rawClasses.length`，`MAX_RAW_CLASSES = 29`（不变）。
  - 6 个**可被 raw 替换**的 image：`suppliedObject/Cloneable/Serializable/Float/Double/Runnable`（L712-717、L735-740）。
  - 计数公式（L747-749）：
    `uint256 count = inputCount + 75 + (suppliedObject?0:1) + ... + (suppliedRunnable?0:1);`
    —— 81 image 中有 6 个是条件 image，故常量 `75 = 81-6`。
  - 条件 image 依次写入（L753-758），随后 `throwableBootstrapAt = at`（L759），
    再 `_appendThrowableBootstraps / _appendStringBootstraps / _appendIOBootstraps / _appendVFSBootstraps`。
  - `classSlot = at + (suppliedRunnable ? 33 : 34)`（L765）。
  - 尾部固定 append：`classSlot+0..+41`，最后两个是
    `p.classes[classSlot + 40].data = _bootstrapQueue();`（L805）、
    `p.classes[classSlot + 41].data = _bootstrapConcurrentLinkedQueue();`（L806），
    紧接 `p.classClass = classSlot;`（L807）。
- 保留（append-only，raw 不可替换）谓词位于 L3075-3159，OR 链接在
  `_prepare` 的 L723-731，失败即 `revert BootstrapProfileError(1, i)`（L730）。
- 解析器行为（对 Enum 有利）：
  - class 级属性（含 `Signature`）在 `_skipAttributes`（L10759）**整段跳过**，不做名字解析 → 泛型自引用无缺类风险。
  - field 级非 `ConstantValue` 属性也 `_skip`（L10744）。
  - final 字段只允许**声明类自身**在构造路径写：L7534
    `if (writeAccess && (resolved.accessFlags & 0x0010) != 0 && !(privilegedWrite && callerClass == owner)) revert FieldError(4, pc);`
    → Enum 构造函数写自己的 `private final` 字段合法。
  - `_validateHierarchy`（L6310）：父类不可为 `ACC_FINAL(0x0010)`（L6336），可为 `ACC_ABSTRACT(0x0400)`；
    非 public 父类需同包（L6337-6339）。
  - 接口闭包 `_validateInterfaceClosure`（L6345）会沿超类链收集并校验各 owner 的 interfaces；
    `_validateInterfaceHeaderAndMethods`（L6433）要求 interface 方法 public、abstract 时 `codeCount==0`。
  - `_typeAssignable`（L8137）→ `_classImplements`（L8121）沿 `parentLinks` + interfaces 判断 assignable。
  - Object image（`_bootstrapObject`，父本 L10984）**只有 `<init>()V` 和 `equals(Ljava/lang/Object;)Z`**，
    **没有 `hashCode()`/`toString()`/`getClass()`**。这点直接决定 Enum 的 `hashCode()` 边界（见 §3）。
  - 泛型 `Comparable`/`Serializable` 目标 image 已存在：`Comparable` 位于 h[24]（L635），
    `Serializable` 位于 h[2]（L613），`String` 位于 h[26]（L637）。

---

## 2. 建议的最小真实 `java/lang/Enum` bootstrap

### 2.1 源码（建议放入 `bootstrap/java/lang/Enum.java`）

```java
package java.lang;

public abstract class Enum<E extends Enum<E>>
        implements Comparable<E>, java.io.Serializable {

    private final String name;
    private final int ordinal;

    protected Enum(String name, int ordinal) {
        this.name = name;
        this.ordinal = ordinal;
    }

    public final String name() { return name; }

    public final int ordinal() { return ordinal; }

    public String toString() { return name; }

    public final int compareTo(E o) { return ordinal - o.ordinal; }
}
```

- 该源是**真实 Java8 语义子集**：`public abstract`，`implements Comparable<E>, java.io.Serializable`，
  `private final` 双字段，`protected (String,int)` 构造器，`name/ordinal/toString`；
  `compareTo` 为有界 ordinal 差。
- 不写 `hashCode()`、`clone()`、`getDeclaringClass()`、`valueOf()`、`finalize()`（见 §2.2/§3）。
- 无 static field/`static {}` → **不产生 `<clinit>`**（对 active-init 门禁友好）。

### 2.2 字段/构造器/方法边界

| Java8 Enum 成员 | 是否实现 | 依据 / 边界 |
|---|---|---|
| `private final String name` | 是 | 构造器与 `name()/toString()` 的唯一存储 |
| `private final int ordinal` | 是 | 构造器与 `ordinal()/compareTo()` 的唯一存储 |
| `protected Enum(String,int)` | 是 | StandardLevel 编译出的 `<init>` 以 `(Ljava/lang/String;I)V` 调 `Enum.<init>` |
| `name()` | 是 | StandardLevel/log4j 惯例读取枚举名 |
| `ordinal()` | 是 | 同上 |
| `toString()` | 是 | 直接返回 `name`；不调 Object.toString（Object image 无此方法） |
| `equals(Object)` | 可选 | Object image 的 `equals` 即身份比较，语义等价；为 JDK 保真可加 `final` 身份版 |
| `compareTo(E)` + 编译器 bridge `compareTo(Object)` | 若声明 Comparable 则必须 | 有界 ordinal 差；**不含** `getDeclaringClass()`/`ClassCastException` 语义 |
| `hashCode()` | **不实现** | 真实 JDK 为 `super.hashCode()`，而 Object image 无 `hashCode`；不要伪造 XOR/常量哈希 |
| `clone()` | 不实现 | protected + `CloneNotSupportedException`，非必要 |
| `getDeclaringClass()` | 不实现 | 反射；preparation 明确排除 |
| `valueOf(Class,String)` | 不实现 | 反射 `enumConstantDirectory`；preparation 明确排除（应诚实失败，不得伪造） |
| `finalize()` | 不实现 | 废弃运行期钩子 |

### 2.3 编译/嵌入配方（与既有 stage 一致，供父级执行）

1. 复制 `rt.jar` 为 `stripped-rt.jar`，删除被替换类（本次新增）：
   `zip -q -d stripped-rt.jar java/lang/Enum.class`
   （既有 strip 集仍含 String/System/Class/Number/NumberFormatException/Integer 与
   Iterator/Collection/.../Queue/CopyOnWriteArrayList/locks/ConcurrentLinkedQueue）。
2. `javac -source 8 -target 8 -g:none -bootclasspath stripped-rt.jar -d out bootstrap/java/lang/Enum.java`
   （JDK 固定 `/usr/lib/jvm/java-8-openjdk`）。
3. 取 `out/java/lang/Enum.class`，写 `Enum.class.hex`，记录 `bytes`/`sha256` 进
   `bootstrap/pins.json` 与 stage `pins.json` 的 `bootstrapSHA256`。
4. 在 engine 生成 `function _bootstrapEnum() private pure returns (bytes memory) { return hex"..."; }`
   （**单行形式**，以匹配既有 reverse-verifier 正则：
   `function (_bootstrap\w+)\(\) private pure returns \(bytes memory\) \{\s*return hex"([0-9a-f]+)";`）。

> 注：本预审按只读约束**未实际编译**，故不给 Enum 的 bytes/sha256。父级须实测并以此为准。

---

## 3. Comparable / Serializable 与缺类风险分析

**结论：建议保留 `implements Comparable<E>, java.io.Serializable`。**

理由与风险：

1. **零新增缺类**：`java/lang/Comparable`（h[24]）与 `java/io/Serializable`（h[2]）已是既有 image，
   `_findClass` 可解析；`_validateInterfaceHeaderAndMethods` 对二者在既有 String 阶段已通过。
2. **声明后**：`_validateInterfaceClosure` 会把 Enum 的这两个 interface 边纳入校验；
   `_classImplements` 使 `StandardLevel → Comparable/Serializable` 可赋值。
   若原始/生成代码执行 `checkcast`/`invokeinterface Comparable`（如 `Comparable c = enumValue; c.compareTo(...)`）
   或 `instanceof Serializable`，只有声明了 interface 才成立。
3. **`compareTo` bridge**：`Comparable<E>` 擦除后 interface 方法为 `compareTo(Object)`，
   javac 会在 Enum 内**自动生成** `ACC_PUBLIC|ACC_FINAL|ACC_BRIDGE|ACC_SYNTHETIC` bridge；
   engine 的 `_resolveVirtual/_loadVirtualCallee` 对 bridge（`0x1040`）不拒绝（它只拒
   private/static/abstract/native 等），`_findInterfaceMethod` 亦能定位到 Enum 的 bridge。可安全包含。
4. **`Signature` 安全**：`<E extends Enum<E>>` 与 `Comparable<E>` 的泛型签名在 class/field 属性中被整段跳过，
   不会引入对额外类的解析。
5. **不声明的风险（供权衡）**：更小的 “no-interface” 版本可省掉 `compareTo`，
   但会让 `StandardLevel` 对 `Comparable`/`Serializable` 不可赋值；一旦原路径做相应 cast 就会
   `TypeError/ClassCastException`（诚实失败，但可能需要后续补 image）。由于目标 interface 已是既有 image，
   **声明它们不增加任何缺类风险**，故推荐声明。
6. **`hashCode` 风险（关键）**：Object image 缺 `hashCode`。真实 Enum 的 `hashCode()` 调 `super.hashCode()`，
   会解析失败（`CallError(3)` 或 interface fallback 失败）。**必须不实现 `hashCode`**；
   如未来代码将枚举放入 HashSet/CHM 需要 hashCode，应作为**后续独立阻塞**单独处理，不能在本阶段伪造。
7. **未实现的 Enum API 是诚实失败**：例如 `Enum.valueOf`/`getDeclaringClass`/`clone` 被调用时应
   按普通 missing-method 失败，**不得**用反射或硬编码常量伪造。
8. **缺类风险清单**：
   - 已消除：标准 JDK java.lang.Enum 不存在但本阶段提供。
   - 不受影响：`Comparable`/`Serializable`/`String`/`Object` 均已存在。
   - 显式留给后续：`getDeclaringClass` 返回的 `Class` 语义、`valueOf` 的 `Class` 查找、数组 `clone()`（属于 raw StandardLevel 的 `values()` 生成代码，不在本 bootstrap 范围）。

> 说明：`values()`/`valueOf(String)` 是 **raw StandardLevel 自身**的编译器生成方法，不属于本 bootstrap；
> 本报告不对其是否被解析/何时触达下结论（见 §7）。

---

## 4. 精确 source 点：81→82 与 inputCount+75→+76

行号以父本 `parent-9453ebd08/artifacts/engine/MCEntryInterpreter.sol`（= worker 阶段结构）为准。

### 4.1 Engine `MCEntryInterpreter.sol`

| # | 位置 | 现状（精确文本） | 改为 |
|---|---|---|---|
| E1 | `_bootstrapRoot` L610 | `bytes32[] memory h = new bytes32[](81);` | `new bytes32[](82);` |
| E2 | `_bootstrapRoot` L700 之后（`return` 之前） | `h[80] = keccak256(_bootstrapConcurrentLinkedQueue());` | 追加一行：`h[81] = keccak256(_bootstrapEnum());`（附注释：在完整 81-image queue tail 之后 append-only） |
| E3 | `_prepare` L747 | `uint256 count = inputCount + 75 + (suppliedObject ? 0 : 1)` | `uint256 count = inputCount + 76 + (suppliedObject ? 0 : 1)` |
| E4 | `_prepare` L806 之后（`p.classClass = classSlot;` L807 之前） | `p.classes[classSlot + 41].data = _bootstrapConcurrentLinkedQueue();` | 追加：`p.classes[classSlot + 42].data = _bootstrapEnum();` |
| E5 | `_prepare` 保留 OR 链 L729 | `|| _isReservedQueueClass(users[i])) {` | `|| _isReservedQueueClass(users[i])\n                || _isReservedEnumClass(users[i])) {` |
| E6 | 保留谓词区（建议紧随 `_isReservedQueueClass`，L3158 后） | `function _isReservedQueueClass(...)` 块末 | 新增 `function _isReservedEnumClass(ClassInfo memory c) private pure returns (bool) { return _isNamedClass(c, bytes("java/lang/Enum")); }` |
| E7 | bootstrap image 定义区（L11093/11094 附近） | 末尾 image 函数 | 新增 `_bootstrapEnum()`：**单行** `function _bootstrapEnum() private pure returns (bytes memory) { return hex"..."; }` |

注意：
- `classSlot = at + (suppliedRunnable ? 33 : 34)`（L765）**不改**：Enum 在尾部，不影响已固定偏移。
- 6 个条件 image 的检测（L712-717、L735-740）与 `count` 的 6 个条件项**不改**。
- `p.selected/referenceCaches/fieldCaches` 均按 `count` 自动扩容（L834-836），无需改动。
- `throwableBootstrapAt`/`_append*Bootstraps` 偏移**不改**（Enum 不插队）。
- 无其他 `81`/`+ 75`/bootstrap 计数硬编码：已全量 grep 确认（engine 内 `81` 仅 L610；`+ 75` 仅 L747）。

### 4.2 Stage pins / 验证工具（新 preflight 目录，建议 `enum-bootstrap-preflight`）

| # | 文件 | 改动 |
|---|---|---|
| P1 | stage `pins.json` | `bootstrapCount: 81 -> 82`；新增 `bootstrapSHA256.Enum`；更新 `engine`/`coordinator` bytes+hash、`domain/address/owner`；其余 pin 保持不变 |
| P2 | stage `bootstrap/pins.json`（或等价） | 记录 Enum `bytes`/`sha256`、strip 列表新增 `java/lang/Enum.class` |
| P3 | stage `tools/verify_source.py` | 反向重建：`new bytes32[](82)->(81)`、`inputCount + 76 -> + 75`、移除 E2/E4/E5/E6/E7；`assert == 父本(domain 归一后)`；image 正则计数 `82`；前 81 image 逐字节相等；`'function _bootstrapEnum()' in engine`；bootstrap SHA 校验 |
| P4 | stage `tools/checkpoint_diagnostic.py` L19 | `assert classes<=110` -> `assert classes<=111`（总 class 上限 29+76+6=111） |
| P5 | stage `coordinator/MCEntryCoordinator.sol`、`tools/Go.txt` | 仅 domain/address/owner/engine-hash/coordinator-hash pin 替换；raw 上限 `address[29]`/`n > 29`/`len(m.Decoders)>29`/`262144` **不变** |
| P6 | stage `tools/build.py` / `tools/build_bootstraps.py` | 加入 Enum 编译与 hex 嵌入；engine `node build.js`、coordinator、driver 按既有流程 |
| P7 | stage `tools/verify_receipts.js` | canonical receipt 校验调用列表加入新 world（沿用既有接口） |

> 说明：`evidence/.../enum-flag-preflight/tools/checkpoint_diagnostic.py` 目前是
> `assert classes<=110`；`parent-9453ebd08/checkpoint_frames.py` 同为 110。新 stage 必须 +1。

---

## 5. raw replacement 保留规则（必须逐条保持）

现状（L735-740）允许 raw bundle **替换**且仅替换这 6 个 image：

- `java/lang/Object`（`_isObjectClass`）
- `java/lang/Cloneable`
- `java/io/Serializable`
- `java/lang/Float`
- `java/lang/Double`
- `java/lang/Runnable`

其余全部 image 为 append-only：raw class 若与受保留名同名，在 `_prepare` 的
L723-731 OR 链命中并 `revert BootstrapProfileError(1, i)`（selector `0x6a23ad80`，
words 为 `[1, i]`；i 为该 raw binding 下标），`rootBefore == rootAfter`。

本阶段规则：

1. **不改** 6 个条件替换语义与 `suppliedObject..suppliedRunnable` 六个布尔（L712-717、L735-740）。
2. Enum 必须加入**受保留**侧（append-only）：新增 `_isReservedEnumClass` 并接入 L729 OR 链（E5/E6）。
   即 raw bundle 提供 `java/lang/Enum` 必须被拒绝，**不得**让 raw 覆盖 interpreter-owned Enum。
3. 新增拒绝门禁 fixture：`RawEnumReplacementMain.class` + 伪 `java/lang/Enum.class` 两个 binding，
   期望 `selector == 0x6a23ad80`、`uint256Words == ['1','1']`、`rootBefore == rootAfter`
   （沿用 `parent-661331e3d/integer_smoke.py` / `smoke_fast.py` 模式）。
4. `Comparable`/`CharSequence`/`String` 的保留（`_isReservedStringProfileClass`，L3075）**不变**；
   Enum 声明 `Comparable` 不会使其可被 raw 替换。
5. 既有 6 个条件替换的正例（raw 提供 Object/Float/... 时条件计数变化）**必须继续通过**。

---

## 6. Java8 host/guest 测试与 quota/OOM/active-init 门禁

### 6.1 Java8 host oracle（generated-only）

- `javac -source 8 -target 8 -g:none -bootclasspath /usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar`，
  再用 host `java` 运行未打补丁的 fixture（沿用 `generate_enum_fixtures.py` 的 host oracle 约束）。
- 正例 fixture 建议（**仅 host oracle 与 EVM 对照；不预判 original29 结果**）：
  - 带 `(String,int)` 隐式 super 的 enum + 额外字段；
  - 断言 `name()`、`ordinal()`、`toString()`；
  - 若含 `Comparable`，断言 `compareTo` 与 `Comparable c = e;` 路径；
  - 用 `values().length` 触达数组/`clone` 的情形应作为**独立 fixture**（与 `java8-enum` 现有 fixture 一致）。
- 打补丁类（annotation/module/E+A/E+M 等）只由 EVM 解析/链接，host JVM 只跑未打补丁源（既有规则）。

### 6.2 Guest EVM 门禁（与既有 stage 同构）

- 三量子：q1、q7、direct(4096)，`driver setup-chain/finish/verify`，canonical terminal
  `machineRoot`/`opaquePayloadSHA256` 必须量子不变；checkpoint 文件 sha256 自洽。
- reopen/新进程 continuation。
- `verify_receipts.js` canonical receipt 验证（新 world 加入调用列表）。
- 既有 `enum_gate.py` 矩阵：`ordinary`、`enum-marker`、`interface-ordinary` 正例保持；
  `annotation/module/annotation-enum/module-enum`（`0x427cfac5` = `[5,i]`）、
  `interface-enum/interface-annotation/java8-annotation`（`0x069163bc` = `[1,i]`）保持。
  **`java8-enum` 的期望值必须由新 stage 实测重导**：现状是 `HierarchyError(1,1)` selector `0xa52e829f`；
  加入 Enum 后该生成 fixture 的终态改变，须重新测量并把新 selector/words 写入 gate，
  **不得**凭猜测硬编码（本报告不预测其值）。

### 6.3 保留 cap / quota / OOM / active-init

- 保留 cap gate（`retained_cap_gate.py` 模式）在**新 pins** 上重跑：
  - 28/29 类包正例、`29-reordered`（packageRoot 必须与 29-direct 不同）；
  - `30/driver`（driver 前置拒绝，world 不存在）、`30/coordinator`（`0xab23ed08`，words `['2']`）、
    `30/engine`（`0x427cfac5`，words `['1','30']`）；
  - `29/262144-infeasible`（`0x71540d20`，words `['1','0']`）、`29/262145`（`0xab23ed08`，words `['12']`）。
  - 这些 selector 是**错误 selector（常量）**，不随 bootstrap 根变化；`rootUnchanged` 是 pre-call 根，亦不变。
- quota：`externalLocalGas = 1e9`、`reserve = 25e6`、resource lookup gas、`MAX_RAW_CLASSES = 29`、
  `MAX_RAW_BYTES = 262144`、coordinator 聚合上限 262144、`MAX_CHECKPOINT_BYTES = 1048576` **全部不变**。
- OOM：既有 OOM/EIIE 门（如 split OOM probe、ExceptionInInitializerError 相关）**原样重跑**；
  本阶段不引入新的对象/字符串 quota 语义。
- active-init：
  - checkpoint 诊断 `inspect` 的 raw-class 初始化断言
    `set(range(n)).issubset(active)`（`state==2`）**不变**；
  - `classes<=110 -> 111`（P4）是唯一诊断上界随总 class 数 +1 的改动；
  - 断言 Enum **没有 `<clinit>`**、不被伪造初始化：在不引用 Enum 的 fixture 中，
    Enum 不应出现在 active 初始化集合（`state==2`）；
  - 若 fixture 引用 Enum（如构造 StandardLevel 子类实例），Enum 应作为超类在子类 `<clinit>` 前被正常调度。

### 6.4 反向 source 验证与 generic runtime

- stage `verify_source.py` 反向重建必须能**逐字**还原为父本 engine（仅 domain 归一），
  并断言: `new bytes32[](82)`、`inputCount + 76 +`、`_isReservedEnumClass(users[i])`、
  `_bootstrapEnum()`、image 正则计数 `82`、前 81 image 逐字节相等。
- generic runtime `jvmevm/runtime/JVMSubsetInterpreter.sol` **不得改动**（保持 `0xe000` 策略）；
  沿用 `git diff --quiet <basis> -- jvmevm/runtime/JVMSubsetInterpreter.sol` 断言。
- 所有旧 cap/gate（enum-flag、classcount29、queue、integer 等）在**新 engine hash** 下重跑。

---

## 7. 非目标与不做预测

- 本报告**不预测** original29 在 Enum 到位后的下一个阻塞（不写 “接下来会是 X”）。
- 不运行/不伪造 Minecraft main-body、world、EULA、listener、Done。
- 不访问原始 JAR/classes/world；不改 generic runtime；不改 accepted caps；不提交、不 push。
- `values()`/`valueOf(String)`/数组 `clone()`、`getDeclaringClass`、反射型 `valueOf` 均不在本 bootstrap 范围；
  它们被触达时应诚实失败，由后续阶段单独测量处理。

---

## 8. 开放风险（供父级实测时关注，非结论）

1. **bridge 与 interface 校验**：Enum 的 `compareTo(Object)` bridge 与 `Comparable` interface 边在
   hierarchy/interface 闭包中是否被完全接受，需实测（本预审按只读未编译/未跑）。
2. **`hashCode` 缺口**：Object image 无 `hashCode` 属既有边界；Enum 不实现它是刻意选择。
   若原路径经 HashSet/CHM 触达枚举 hashCode，会暴露为后续阻塞（不在本阶段修复）。
3. **`toString()` 归属**：Minimal Enum 的 `toString()` 直接返回字段；若原 StandardLevel 覆盖 `toString()`，
   行为由 raw 类决定，与本 image 无冲突。
4. **raw StandardLevel 的生成方法**：`values()/valueOf(String)` 属 raw 类；其是否/何时被解析取决于
   engine 的惰性解析路径，本报告不下结论（避免越界预测）。
5. **诊断上界**：`classes<=110 -> 111` 是唯一随总 class 数变化的工具常量；若父级采用不同诊断实现，
   需等价更新，否则 checkpoint 解码会拒绝。

---

## 9. 交付清单（精确改动一览）

Engine（`MCEntryInterpreter.sol`）：
1. L610 `new bytes32[](81)` -> `new bytes32[](82)`
2. L700 后追加 `h[81] = keccak256(_bootstrapEnum());`
3. L747 `inputCount + 75` -> `inputCount + 76`
4. L806 后追加 `p.classes[classSlot + 42].data = _bootstrapEnum();`
5. L729 OR 链追加 `|| _isReservedEnumClass(users[i])`
6. 新增 `_isReservedEnumClass`
7. 新增 `_bootstrapEnum()`（单行 hex）

工具/配置（新 stage）：
8. `pins.json`: `bootstrapCount 81->82` + `bootstrapSHA256.Enum` + engine/coordinator hashes + domain/address/owner
9. `tools/checkpoint_diagnostic.py`: `classes<=110 -> <=111`
10. `tools/verify_source.py`: 反向重建 82/76 + image 逐字节 + 前 81 不变
11. `bootstrap/`（或等价）: `Enum.java` + 编译/strip/hex/sha 脚本
12. `coordinator/MCEntryCoordinator.sol`、`tools/Go.txt`: 仅 pin 串替换
13. 新 fixtures/raw-replacement/gate 与世界生成脚本

不动：
- `jvmevm/runtime/JVMSubsetInterpreter.sol`（generic，保留 `0xe000`）
- 所有 accepted caps、raw 上限、gas/reserve、frames、checkpoint/head 上限
- 既有 81 image 字节/顺序、6 个条件替换语义、所有 retained gates
