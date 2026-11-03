# 雪妃资源组合变形候选

此实现位于独立 candidate_core，冻结上游 source 未修改，不代表 SDK 等价性。
原字段是 43 个非空 meshCombinator、122 条变量控制器；不能用已有 meshCombine
或帧内 bp 的支持替代这些字段。

导入边界：

- 仅 meshType=1、entryType 缺省或 0。未知组合字段明确拒绝。
- 解析 #resource@N / #resource#N，来自 resx ExtraFlattenArrays/FlattenArrays，
  或 ExtraResources/Resources 指向的显式相对二进制文件，不能双重定义。
- 二进制长度精确等于 meshCount×128，逐 float32LE 解码、拒绝非有限数。
  扁平数组精确为 meshCount×32，转换为有限 float32。
- neutralIndex 必须在 [-1,meshCount-1]；范围有限且非退化，支持反向范围。
- 单控制器最多8MiB解码数据，单资产最多64MiB、4096控制器，乘法先检查。
- 类型资产保存已解码的32分量网格和来源，不保留JSON到运行时；资产schema更新为7，
  旧二进制资产需从源JSON/resx重新导入，不静默补默认字段。

候选求值：

变量经范围归一化并钳制到 [0,1]，相邻网格线性插值，各控制器结果按分量累加；
源序列通常第一条为绝对网格、后续为位移网格。neutralIndex 不用于减去网格。
所有控制器恰在声明中性整数样本（小数部分小于2^-23）时撤销有效曲面，
但组合器仍拥有字段：不会改用帧内 bp。非中性组合网格同样优先于 bp。
场景编译把变量绑定为 ParamId；每次 geometry evaluate 在栈上计算固定32分量，
复用既有曲面/继承/geometry流程，不解析JSON、不读文件、不查变量名、不按帧分配。
额外曲面密度也参与预分配容量上界。

该数值候选依据独立 artemis-compat 固定版本的可读实现建立：
[资源和数值核心](https://github.com/Weiss-UltimateSavior/artemis-compat/blob/647135edebcc1b745231d6b95a1de6ae55c003a9/src/render/emote_combinator.cpp)。
其插值、求和及中性撤销是对照假设，不能声称已经从原 SDK 逐点验证。
已有 NekoMote 的 meshCombine/同步/物理/遮罩语义继续分别受原检查约束，
没有为了此功能关闭它们或增加忽略失败的回退路径。

诊断：

- nekomote_mesh_combinator_probe --self-test TMP OUTPUT：数学端点/分数/反向范围、
  绝对+位移相加、bp优先权、类型拒绝、类型资产往返、二进制LE、截断/NaN、
  扁平长度/资源缺失/路径穿越/预算/未知字段，以及稳态分配与耗时。
- --model JSON RESX RESOURCE_ROOT OUTPUT：真实模型导入计数，逐变量±15检验
  组合器拥有的网格发生变化，保留所有失败与来源路径；不会删除组合器当作成功。
- GeometryNodeObservation 的 combinator_owned/effective/control_count 和
  combinator_patch 仅供离线观察，后一项是祖先 meshCombine 之前的自身采样网格。

测试证据与最终边界由交付清单记录。CPU差分通过不代表像素、全动作或板端长稳通过。
