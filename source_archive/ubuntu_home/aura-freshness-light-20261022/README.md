# 轻量 YuNet 时效统计候选

默认关闭，**未上板、未证明板端开销通过、未常驻生产**。原完整统计 full23 的板端额外 CPU 均值约0.739ms超过预设0.5ms，主任务据此暂停接入，改为本候选；本目录不修改完整候选或提高门槛。

本候选只保留固定计数、原服务 source clock 的输入/发布年龄、连续拒绝、16条事件和相邻发布空窗上下界。`mark()` 返回 None，统计模块没有独立 wall/thread CPU 读取，不提供每次尝试的 wall/CPU 耗时；原14源的 native wall/CPU 诊断保持。未采集的数据不填0。

两份来源：face_targets.py 沿用已审查完整版接线，SHA `2f68d7ae75f67b2b1c67e7513296d6a6e907e02bcc0a5867d0f09c8fd1075577`；轻量 FaceFreshnessMetrics SHA `206f565044a94a7f3f8369d25a1f98e587107b5f025d16f3c2cab6c19fe4a160`。后者schema为 `aura-face-freshness-light-1`，mode为 `COUNTS_AND_SOURCE_AGE_ONLY`。

软件验证32项通过：12项轻量特性＋20项由原full23适用用例改写的service行为。没有宣称原full23整套重新通过；删除的3项依赖独立wall/CPU端点或跨时钟比较，本模式不支持。保留default off与原d03e版本时钟/回调/SlotUnavailable/200ms节拍一致、TTL、latest、缺值、业务异常、观察异常隔离、close、饱和和并发快照。反向stamp/check在发布与输入摘要分别产生无效读数，两次计数为2，已修正原草稿的错误测试预期。

source时钟假定为原服务 monotonic millis，**无法用独立时钟鉴别前跳**；倒退或不可比较的相邻发布不纳入空窗摘要。只有输入/发布的原检查和提交后观察给出上下界，不向首次之前或最后之后外推；提交后观测过TTL不等于原准入门接受了过期输入。未采用每attempt总耗时或模型硬件耗时推论。

原接线在观察器不可用时仍返回旧full schema的 `observer_unavailable` 占位，不包含有效样本；严格轻量验收会拒绝该状态，业务继续运行。默认关闭及其他源码行为没有因修这个占位而另改动。

可携带板端无设备前置与本机唯一一次微基准在相邻目录 `/home/ghmd/aura-freshness-light-validation-20261022`。32功能和18验收/禁止操作检查通过；x86_64各200次完整样本的最大新增均值约wall0.00862ms、线程CPU0.00863ms，小于原0.5ms门槛。此为合成hook成本，**不是KV260成本通过、不是时效改善或推理收益**。

本任务未访问板卡/UART、相机、音频、网络业务、真实模型、身份库或生产配置，也未更新共享/项目日志。板端验证、主任务审查和接入由root继续负责。
