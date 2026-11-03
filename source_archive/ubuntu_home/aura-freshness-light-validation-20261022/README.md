# 轻量时效统计：可携带无设备前置

状态：本机软件/单次微基准通过，**板端尚未执行**。固定新增均值门槛0.5ms保持，不包含实际模型/DPU、相机或音频工作，也不证明时效改善。

代码来源为相邻 `/home/ghmd/aura-freshness-light-20261022`；prepare_sources.py 的5个SHA针脚覆盖原d03e基线、两份轻量源码、两份32项测试。`source_sha256` 必须精确匹配，不能用完整统计full23报告替代。32项由12轻量＋20原service适用用例改写组成。

在任意有Python3.8+的独立目录解包后执行：

```bash
python3 -B run_preflight.py --output evidence/NEW_UNIQUE_DIRECTORY
python3 -B evaluate_preflight.py evidence/NEW_UNIQUE_DIRECTORY/report.json
python3 -B -m unittest test_evaluator -v
```

无需在板卡运行prepare_sources.py，它仅供本机按来源准备包；包内已有5个针脚文件。不能使用 `-O` 或PYTHONOPTIMIZE，断言关闭时会拒绝执行。没有部署或服务重启代码。主进程仅用两个顺序子进程隔离测试虚拟时钟与基准真时钟，不是两个并发终端。

测试worker和基准worker都先加载Python3.9 unittest.mock所需标准库，再启用import blocker及audit hook：拒绝模型/设备/网络依赖、真实socket创建、/dev文件打开、嵌套进程和ctypes动态库。验收器18项测试含这些操作在触及设备/创建进程前被拒绝的验证；不连接网络或设备。

基准只有外层 `time.monotonic_ns` 和 `time.thread_time_ns` 真时钟；验证二者为time模块内置函数，轻量observer没有独立wall/CPU时钟属性。各normal/slot拒绝/满16事件health外层RLock三组，original/off/on各200次，分别保存完整分布和真实功能计数校验。observer内部未收集wall/CPU字段保持False，original/off无observer的样本字段为None，不用0伪装已经测量。

严格完整性还包括attempts/finished/active、输入年龄样本、成功发布/拒绝数、发布年龄与相邻边界样本数、0观察异常/无效年龄/时钟对拒绝/TTL丢弃/饱和/业务错误、满事件队列与干净close。时钟和计数前置失败即拒绝，不将缺值补0。新增wall或线程CPU均值任一超过0.5ms即失败。

唯一一次本机合成结果为 `evidence/local-initial`：32功能通过、单组各200、完整无device；最大新增wall0.008620ms/线程CPU0.008626ms。顺序original/off/on块会受执行环境影响，不是随机同输入性能A/B。assessment的physical_board_verified始终False，不能自动部署；主任务可在真实KV260重新执行，并用外部板端证据记录执行位置，仍不称真实视觉收益。

包仅含源码、合成测试和数字证据，无图像、声音、向量、身份库、模型权重或原始UART。root独占后续板卡和日志操作。
