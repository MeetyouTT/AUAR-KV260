# 技能 C · 本地大模型语音性能与播放交付验证

当模型回复慢、缓存命中被误计为生成提速，或回复已写进记忆但未完整播放时，可用本目录的脚本分别核对计时和交付记录。脚本读取公开 CSV / JSON，只需 Python 3.8+ 标准库。适用于只有少量 CPU 核心的 Ubuntu 20.04。

## 复现

从本目录执行：

    python3 -B scripts/check.py

成功时有五行 PASS；其中最后一行表示错误样例按预期被拒绝。若需查看逐项时延或错误位置，可单独运行：

    python3 -B scripts/verify_measured_run.py examples/measured
    python3 -B scripts/analyze_benchmarks.py --input examples/benchmarks.json
    python3 -B scripts/validate_delivery_trace.py --input examples/delivery_pass.json
    python3 -B scripts/validate_delivery_trace.py --input examples/delivery_fail.json

最后一条命令故意返回 1。两个通用分析器返回 0 表示合同通过，1 表示存在明确错误，2 表示未知、输入不全或不能解释。实测核对器返回 0 表示原始行与汇总一致，1 表示数据无效或不一致。Windows 可用 python 代替 python3。所有入口均无需安装依赖、模型、GPU、声卡和板卡。

## 来自实际运行的样本

examples/measured 保存 2026-11-02 暖态实测的逐次 LLM / TTS 和每秒 GPU 表，以及同一运行编号的汇总回执。KV260 提交公开的测试请求；Windows RTX 5090 Laptop GPU 保持原 27B IQ4_XS（上下文 2048、输出上限 120、关闭思考）和 OmniVoice 16 步驻留。主窗口 180.004 秒；六组计划中第 4 组在发请求前因已有活动请求跳过。其余五组各成功执行一次 LLM 和 TTS，TTS 全部未命中缓存。LLM 保留正常运行时的前缀缓存。

| 软件指标 | 本次复算结果 | 读数含义 |
|---|---:|---|
| LLM 完整 RPC 中位数 | 1837.416 ms | 板端请求到完整返回，含准入、推理和网络 |
| 首个非空 JSON 内容中位数 | 469 ms | 主机生成流的软件事件 |
| 解码速率中位数 | 40.853 token/s | 含结构化输出字符 |
| TTS 完整 RPC 中位数 | 718.002 ms | 完整 PCM 返回到板端 |
| RPC RTF 中位数 | 0.12763 | 逐条用 RPC 秒数除以 PCM 秒数，再取中位 |
| 设备显存占用中位 / 最低空闲 | 18951 / 5002 MiB | 全设备 180 个一秒采样，可能错过瞬时峰值 |

该窗口 GUI 监听暂停、麦克风关闭且转轴停止；样本没有真实 ASR、记忆上下文读取、扬声器首声或整机联动指标。LLM 和 TTS 使用各自固定的公共输入，不能将两列中位数相加作为真人等待。n=5 时最近秩 P95 等于最大值，不能据此推断长尾保障。

verify_measured_run.py 读取四个文件，核对计划与实际 case 编号、重复或漏项、未命中缓存、采样率与样本数、逐条 RTF 和解码速率，重新计算汇总与设备显存样本。examples/measured/reference.json 保留来源回执，其中 sources 是原采集目录的引用。使用本技能只需随包的四个文件。

## 迁移到另一个工程

1. 固定模型版本和量化、上下文、输出预算、音色和步数，给每组公开输入与软件版本编号。分别记录暖态与冷启、TTS 命中与未命中、任务种类与共存负载。
2. 按 examples/benchmarks.json 声明 platform_id、variant、case_group、model_sha256、backend、warm_state、tts_cache_hit、answer_valid、trial_id。计时字段按同名软件事件填写，缺失留 null。把参数组、共存负载与语义审核规则编码到 variant / case_group，避免不同条件被分到同组。先保留失败、跳过及理由，再比较有效样本中位数和范围。analyze_benchmarks 按既有质量标签筛选；标签需要另行审核。输入的五个阶段均未涵盖声学首声。
3. 按 examples/delivery_pass.json 编码归一化事件。检查请求、代次、作用域、段号、PCM 哈希、样本数和时限；完整 ACK 之后才允许提交助手已播记忆。撤销来源后，迟到结果和未经校验的摘要不得恢复旧内容。脚本只核对记录中已经声明的决定和依赖，语义正确性、真实扬声器播放及长期记忆要另测。
4. 更换实测 CSV 时，为单一固定条件给出独立采集的 reference.json。逐次表和汇总字段见 examples/measured。混合 TTS 缓存、带未表示失败的尝试、跨条件或缺失计数均不能用当前实测核对器合并；保留原记录，拆成可比组后分析。

## 两次真实取舍

- 2026-10-18 固定 seed 的内部短字段实验，current / compact 各四次模型阶段台词就绪中位数分别为 2762.875 / 2287.705 ms。逐条数值和输出字数见 examples/short_fields_history.csv，回答长度也有变化。该旧平台实验只支持继续评估短字段方案，不能外推到当前 RTX 5090 Laptop 的端到端提速。
- 同日独立流式 TTS 候选 CUDA 25-token 的四次首 PCM 中位数低至 0.289 秒，但六条内容筛查的字错误率达 82.8%–96.6%，当时排除这项默认配置。基准分析器的合成小样保留了快而无效的回答，验证其不会混入有效样本统计。

## 证据

evidence/source_index.json 记录原技能、历史记录和本次运行的相对出处与 SHA256。examples/benchmarks.json 与 delivery_*.json 均为公开合成用例；examples/measured 为独立的真实运行记录。evidence/unit_tests.log 记录 Windows Python 3.10.11 上的 33 个回归。evidence/ubuntu20_single_core.json 记录 Ubuntu 20.04.4 / Python 3.8.10 上将进程限制为一个 CPU 核心的复算，传入发布源码和小样，在内存中执行三个分析器的四个用例。它测的是离线工具复用能力。模型所有权、实时推理、私有会话、用户现场听感均未纳入这次复跑。
