# 原生DPU执行路径修复（进行中）

<!-- single-terminal-r2-20261024 -->
**最新单终端结果：已冻结并在板上预备222份Python＋5份C/C++的r2候选，尚未启用生产。** 代码见[source/native-v2-d7256b06808509c9](source/native-v2-d7256b06808509c9)，[单终端迁移实现与限制](validation/business-newboot-r2/README.md)。其他任务已停止，后续由root串行完成。

当前实际仍为：**只有YOLO正常DPU约9.95Hz；YuNet 5fault/4恢复后LATCHED走CPU；SFace 3fault/2恢复后预算耗尽停用，身份ready=false。** camera29563/GUI29588/X1077、worker存活、gap0、primary超限累计3，原unit/源/身份配置与库保持；没有靠重启清计数。当前数字见[current-board.json](current-board.json)。下方“SFace仍DPU/391完成”是此前时点。

已通过：20组原生恢复/交接、8组仲裁、5组C ABI及SAN；62项业务/新boot/legacy迁移检查；原237项235通过/2私有ELF跳过；12项真实CDLL→C++/fake模型接口检查。板上0.795秒链接通过，随后仅加载库读取ABI常量，未创建模型。源码和拟用配置已在板独立目录准备，当前真实boot的preflight正确拒绝legacy seed，前后故障计数不变，候选推理0。见[目标链接](v2-target-link-result.json)、[常量接口](v2-target-constant-abi-result.json)、[板上预备/拒启证据](r2-board-preparation-result.json)。不同检查有重叠，不相加成独立业务场景数。

首次迁移入口已补：只有真实不同kernel、双显式opt-in、完整hash固定legacy数字归档及已知完成证据，才建立新boot计数域；旧故障保留为历史下界/unknown tail。marker按当前boot唯一，换seed不能重开预算；归档先持久化，失败拒启。同boot旧health仍不冒充精确checkpoint、不解除当前LATCHED。**实际重启、真模型INT8同输入等价、三模型业务吞吐/CPU/DPU收益和长稳尚未验证。** 没有安装新systemd覆盖、没有服务切换或重启；不能称全部修好。
<!-- /single-terminal-r2-20261024 -->

以下为本轮早期阶段记录。

UTC2026-10-24，洛杉矶2026-10-23。本目录记录正在实施的候选，不是可部署release；完整源码/同版回归待整合后封存。用户最新允许多终端，root单路访问板卡，三路只本机开发/审查。

**最新运行状态：YuNet第5次超限后guard LATCHED，已退CPU保护；YOLO/SFace仍DPU。** camera29563/GUI29588/X1077，boot008f3e1b…，三服务active/NRestarts0、YOLO约9.96Hz、worker存活、gap累计0、primary超限累计3。SFace累计391完成/0超限，不等于精度验收。原4源/持久覆盖/原unit/身份配置与INT8库SHA保持，未重启或清零解除保护。数字证据见[current-board.json](current-board.json)和[production-preservation.json](production-preservation.json)。

根因修复方向为把取得执行权→execute/wait→确认→保护/释放放在同次原生调用内，释放不再等Python重新取得GIL。当前已实现固定模型接口、原生统一仲裁、unknown保活、自有缓冲、YOLO受控移交和不跨推理持有的Python生命周期锁；原30ms/5ms、TTL、身份空间/阈值保持。

首阶段8组原生仲裁/6组布局、10组独立桥接与SAN、21项绑定及5项真实ctypes→C++/fake模型接口检查通过。最新源用板载21份实际头文件完成本机AArch64对象交叉编译；并非最新目标链接或真实推理验收。历史首版目标编译链接过，但生产故障3→4、观察不干净；35秒UART前台超时后只读取回成功报告，因果归因未知。见[first-target-compile-assessment.json](first-target-compile-assessment.json)。

恢复policy已完成独立13组/3840步对照/ASAN与零分配检查，正在接原生gate。原交接parser不能直接承接当前mixed保护历史，健康快照又不含精确attempt_times；正在做严格完整导出/seed，不制造零预算或把LATCHED改RUNNING。三模型正常业务调用、SFace释放执行权后的新鲜度确认、状态累计和等价基准分路实现中。

尚未执行：新路径真实三模型接线、原始INT8同输入输出等价、收益/长稳/真人身份精度与冷启。普通Linux仍可能在native内被调度走，不能承诺任意负载永不越30ms。候选尚不能替换生产或称根治。Windows接收/执行回执未代填，不共享权重/ELF/板载第三方头文件正文/UART/人脸/向量/库内容。
