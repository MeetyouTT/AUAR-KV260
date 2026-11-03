# 合并light2观察成本：独立无设备工具

本包为 `/home/ghmd/aura-yunet-retry-light-20261022` 的准确合并源码重新准备，**不套用light1成本结果，未上板，未部署**。基线仍为原d03e服务；四个合并源码（face_targets、light2 metrics、runtime、dpu_yunet）及两份32项测试均使用prepare_sources.PINS固定SHA。

在解包后的独立目录直接运行，纯stdlib，无需Docker或模型依赖：

```bash
python3 -B run_preflight.py --output evidence/NEW_UNIQUE_DIRECTORY
python3 -B evaluate_preflight.py evidence/NEW_UNIQUE_DIRECTORY/report.json
python3 -B -m unittest test_evaluator -v
```

不要在板端执行prepare_sources.py；它只用于本机准备，来源为本机绝对目录，包内已包含七个针脚文件。禁止-O/PYTHONOPTIMIZE；测试与真clock微基准为两个顺序子进程，使用各自PID，禁止虚拟时钟污染测量。

成本问题只测观察器，不混入重试：normal、SlotUnavailable、满16事件health外层RLock各组original/off/on×200次；两个merged实例都显式 `slot_retry=False`，on仅为 `freshness_metrics=True`。报告记录每组retry状态，评估器拒绝启用或未知值。本轮不会执行重试worker、native、相机、音频、网络或服务操作。

原runtime与adapter只做SHA核验，**不会被加载或实例化**；依赖由准确leaf fakes提供，包括SlotUnavailable及三个新异常，AdmissionCancelled带reason、SlotAdmissionDenied带rejected_at。import blocker和audit hook拒绝真实VART/XIR/numpy/cv2/gi、设备/dev open、socket创建、ctypes及嵌套进程；unittest.mock预加载兼容Python3.9，实际操作仍被audit拒绝。

schema为 `aura-synthetic-freshness-light2-preflight-1`，观察schema必须为 `aura-face-freshness-light-2`。严格检查32项适用light/service功能全部通过；该32是合并候选的12项light＋20项service测试，非合并82整套、非旧full23整套。原源码无改，因此此次不重复82/67/66。取消字段是独立观察语义，不算process_errors；本成本测量未启用guard，要求所有取消计数为0。合并取消功能本身已有候选82项证据。

测量只用外层time.monotonic_ns/time.thread_time_ns真时钟；观察内部wall/CPU未采集标False，off/original无observer字段为None，不填零伪造。检查attempts/finished/active、原source年龄完整样本、原发布/拒绝及连续边界、0观察失败/无效源/饱和/业务错误、满事件和干净close。任一新增墙钟或线程CPU均值超过原固定0.5ms即失败。

仅一次本机x86_64微基准 `evidence/local-initial` 完整通过，最大新增均值墙钟约0.008949ms、线程CPU约0.008960ms；32功能与19验收反例通过。顺序original/off/on合成块不是随机同输入性能A/B，也不代表板端成本、实际推理或时效收益。physical_board_verified仍False，root需在目标板另跑前置后才能决定实时接入。

包和manifest只有代码、合成测试、数字证据，无真实图像、声音、向量、身份库、模型或原始UART。父目录、共享入口和板卡均未由本任务改动。
