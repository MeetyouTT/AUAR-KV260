# 同owner旧VART/新原生执行等价基准候选

**当前只有本地fake验证，没有运行任何真实模型或连接板卡。** 这是供root在独立维护窗口启动的候选工具，不是生产部署器。它不会停启服务、打开相机、访问身份DB、操作GUI、音频、固件或重启设备。

实现：`equivalence_benchmark.py`；只读pin计划生成器：`build_plan.py`。模块导入不加载DSO或模型。使用v2 `NativeContext.restore_seed→adopt_yolo→NativeRunner`、原始bytes输出和`confirm_result`。v2来源为当前 `schedule-integration/native_bridge.h`、业务候选的 `native_binding.py/native_protection.py`；最终调用前必须按实际冻结版本重新pin。缺少v2方法/ABI/结构大小会在模型创建前明确BLOCKED，绝不当作成功。

## 执行前置

root在外层完成维护和可靠回退安排，并保存生产保护状态快照；本工具只读验证指定kernel boot、原camera unit已loaded/inactive/dead且MainPID=0。原 `DpuYoloX` 继续通过 `/run/aura-person-dpu.lock`取得唯一project owner；不创建第二个DPU owner或测试daemon抢生产。若服务仍active、boot改变、任何pin/完整源码闭包不一致，拒绝启动。

旧源应来自主任务回收的214文件实际生产闭包 `coherent-baseline/aura`，对应 `actual-production-python-manifest.json`，不要混用共享主目录中另一个GUI版本。新源为在该底座上的完整v2候选。工具验证两个root的完整 `.py` 文件集合和逐文件SHA，并固定legacy yolo/runtime及candidate binding/protection四个入口；model、manifest、原YOLO库/prototxt、新bridge、生产快照也都逐SHA核对。

`build_plan.py`输入两份小JSON：

- `--yolo-owner-config`：仅原DpuYoloX构造字段，model/model_sha256/model_config_sha256/native_library/native_sha256/classes/score_threshold/person_nms_iou/arch_fingerprint；不传完整身份配置。
- `--optional-models`：按yunet、sface顺序的列表，每项为task、model、manifest、source_ttl_ns；TTL由root从现役配置提取，不能为通过测试放宽。生成器计算两个模型及manifest的实际SHA。

还需 `--legacy-root`、`--candidate-root`、`--bridge`、`--production-snapshot`、`--expected-boot-id`、`--new-output-directory`。它只读/哈希这些文件，在全新输出目录创建plan和两个源码manifest，不加载DSO/模型，不执行systemctl。

基准先用默认模式检查pins和服务条件：

```bash
python3 -B equivalence_benchmark.py --plan /prepared/plan.json --output-directory /new-result-directory
```

默认模式不创建结果目录、不加载candidate DSO、不运行模型；只报告前置检查通过，**不称执行已验收**。root确认外层维护/回退就绪后才在同一fresh Python进程使用：

```bash
python3 -B equivalence_benchmark.py --plan /prepared/plan.json --output-directory /new-result-directory --execute-maintenance
```

实际模式在原owner/模型创建前只加载candidate DSO查询v2常量ABI/结构大小，不调用其factory；随后进入真实比较。不要同时启动多个基准，不要把计划中的隔离maintenance seed交给生产loader。`isolated_maintenance_seed`建立单独测试counter域，关联生产快照SHA，永远不用于解除生产LATCHED；正常生产恢复由root外层按原记录处理。

## 比较和停止规则

输入仅为公开合成数据：全零、`random.Random(260)`生成的确定性随机bytes。YOLO用640×480 BGR，YuNet/SFace用各自实际manifest大小的相同编码INT8。无真实图像、人员模板或录音。

1. 同一个原YOLO detector先完成两种输入的原C ABI调用，第一例也作为原库启动自检。确认status0并保存内存结果后才adopt；**adopt后不再使用借用raw detector handle调用旧ABI**。
2. 新原生YOLO对同两例比较原始float32行/数量（仅输出相等与数量，不输出坐标/分数）。空结果会如实报告compared_output_bytes=0，不假装验证了完整非空解码。
3. 可选模型构造旧 `PinnedRunner`，直接使用它固定的VART runner执行原始execute_async/wait，保留INT8数组；不先反量化再比较。新NativeRunner使用同一份编码输入、同一owner顺序执行，按tensor名字比较所有原始输出bytes，允许VART端口顺序不同。
4. 每个optional输入对前执行一次有记录的新原生YOLO primary anchor，建立实际100ms周期deadline；不伪造无限准入窗口。两例/两个optional一共固定4次anchor，随报告单独计数。

完整通过时是6对比较、16次项目执行API调用：旧YOLO2、新YOLO6（含4 anchor）、旧optional4、新optional4。这不是硬件job profiler或利用率结果，不计算准确率、加速比或CPU收益。旧execute/wait计时与新lease端点不同，顺序比较也非严格性能A/B。

新路径保持30ms hardcap/5ms guard，任何cap、guard、普通准入拒绝、结果过期、primary周期超限或字节不等立即停止后续case；无自动恢复、fallback、额外warmup或循环刷空推理。已确认完成时才关闭runner，再关闭Context及原owner FD。

## 未确认完成时的保留

每个native调用前写原子`checkpoint.json`，先标记completion_unconfirmed；只有明确返回后才清除。旧execute抛异常/wait非0、新native unknown/中断或cleanup结果未知，保留runner、graph、输入/输出、Context、module和owner引用，写unsafe标记，不做正常cleanup。即使磁盘写unsafe标记失败，内存保留先建立，不丢owner。

真实CLI在unsafe后**保持进程存活**；SIGTERM/SIGINT不会自动释放该owner，不能用普通timeout/RuntimeMaxSec到期就kill并恢复另一个DPU owner。root外层必须把缺少confirmed-idle、unsafe或超时未返回都当作完成未知，检查/隔离后再决定处理；不要自动重启生产或删除锁文件。正常完成/已知拒绝时，只有`cleanup_confirmed=true`才表示本基准资源已安全释放。

所有JSON只含scope、pin/boot来源、tensor名/字节数/差异计数、调用数量和时钟，不输出raw向量、图像、YOLO行或身份数据。`result.json`只在本次新建目录中创建，不覆盖历史；checkpoint仅更新本次自己的文件。

## 本轮实际验证

`test_equivalence_benchmark.py`：20项纯fake检查，覆盖按名字处理新端口逆序且全部INT8相等、单字节差异停止、active service/boot拒绝、cap/guard/普通拒绝无重试、旧wait或execute未知、新native中断/unknown、旧YOLO自检未知、cleanup未知、标记磁盘故障仍保活、结果写盘失败仍进入CLI hold、真实LegacyRaw控制流配fake numpy/VART保留buffer、缺少v2 API时不加载DSO、计划生成器只读哈希且无模型/服务操作。

首次16项中的1项因测试变量名`render/rendered`笔误失败，实际实现已完成数据/cleanup路径；已修并保留`test-first-result.json`。16项中间通过证据另存`test-16-result.json`。19项通过证据另存`test-19-result.json`；补模块导入缺失的明确BLOCKED检查后，最终20项结果和源码SHA见`test-result.json`/`manifest.json`。宿主无numpy，本轮LegacyRaw测试使用显式fake numpy/VART surface，不冒充真实numpy/VART运行。

**尚未验证：** 实际AArch64 DSO/头文件/模型执行、原始输出真实字节相等、真实板上的guard/TTL行为和unsafe保活运维。只有root在上述维护条件下执行后，才能添加板测结论；当前不能据此称迁移完成、长尾根治或板卡利用率提升。
