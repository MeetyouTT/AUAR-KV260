# 板端运行候选、ASR 与前端实测

2026-10-30。按用户最新“板端业务主控、Windows 仅现有 27B/OmniVoice 推理”边界工作，先读两端 AGENTS、ZIP README、最新日志和统一时间轴方案。本文件只记录本代理实际工作，根代理的真实库/最终集成另行记账。

已新增可注入 BoardDialogueController、严格模型 HTTP client、同模型 Paraformer PCM 适配与本地 GTCRN/Silero 候选。请求代次、原总期限、取消和完整 playback_token/SHA256/samples ACK 留在板端。当前 36 项控制/ASR/HTTP 回归通过；实际 ARM 合成 SQLite+回环 HTTP 控制器烟测通过，模型输出是 fixture，未冒称实模型/实体播放。

只读实测板：Python3.9.9/aarch64/glibc2.34、4×Cortex-A53、NumPy1.21.2、总RAM4023988kB/可用约2.9GB、无swap，/home/root空闲约9.03GiB。原系统无sherpa/torch/torchaudio/speechbrain/scipy/sounddevice。现有 Python ORT 路径在独立子进程尝试建原GTCRN session时退出-6（Can't add new modules after the interpreter has been initialized），不能视为可用，也不能据此断定是opset不兼容；原服务不受影响。

官方同版sherpa/core1.13.8 cp39/aarch64 wheel仅解包至独立候选deps；既有Paraformer243371218B、tokens75756B、公开WAV179712B经SHA沿网线到独立ASR候选。实际公开5.6146s WAV两次识别6.9205/6.9106s（RTF1.2326/1.2308），加载12.9439s，峰RSS429572kB。识别可运行，但未通过实时/整机效果门槛。

原GTCRN535638B和SileroV5 2313101B也只进入独立frontend候选。281帧/185 speech与现役Windows Pipeline决策逐帧同hash，原PCM不改；ARM平均32.3532ms/P9561.8012/max108.9906，238/281超20ms。分段显示combined1/1平均30.403ms（GTCRN26.313/VAD3.103/转换0.659/list0.329）；2/1反更慢34.933ms。GTCRN-only1线程均19.671ms/P9532.821/CPU94.46%单核基准，2线程24.353ms/P9544.505/CPU156.36%。VAD-only1线程均4.138ms/P9511.257，2线程4.927ms/P9515.966。四核读取均1.333333GHz，thermal sysfs未提供温度；未调频/电源/affinity/服务，相机PID1333持续计数。

官方v1.13.8 streaming STFT实现使用O(N²) StreamingDft，已开始独立 NumPy rfft/irfft 同权重候选，保留periodic sqrt-Hann512/hop256、float32复数布局、三个隐状态、首hop丢弃、OLA、reset和flush。Windows公开89,834个输出（含flush490）与SDK逐样本完全相同，PCM16全等；281帧VAD、固定700ms/500ms pre-roll端点91,840samples和SHA、原PCM与降噪PCM的ASR分别一致；另10项真实资源边界/flush/reset测试通过。此FFT候选尚等ARM验证，不把独立FFT微基准当SDK实际耗时。

生产保持r3-ubuntu/286pins、boot605eaf50-c66a-4559-bfc9-5ae177e0f305、UI918139/camera1333、IDLE、监听/麦克风/跟随关闭、机械FAULT/null。未改生产配置/组件/启动器/相机、boot/FDT/FPGA/VART、身份模板或真实库，未开麦/有声播放/运动。实板GUI SHA874f0075…与Windows1dcb21b7…不同，已告知根代理必须用fresh actual r3树集成，不能覆盖旧GUI。

证据在 /home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-30_board_owner/ubuntu/evidence/；详细索引见同目录README。早期扩展依赖探针触发3800字节UART行长度门槛、性能探针一次误把SDK list当ndarray均已修正，失败证据保留。所有执行后的UART已释放并恢复echo；与根代理/声纹代理按预约串行使用UART。临时资源HTTP仅白名单板IP GET、SHA校验、TTL自动退出，无常驻服务、自启或新模型下载；LLM权重/Ollama仍D盘未动。

## 后续 FFT ARM 实证（同一任务）

根代理完成其语义记忆板测并释放UART后，本代理运行FFT实板候选，结果见evidence/20261030T130034670747Z-board_gtcrn_fft_probe。独立ORT1.17.3实际可加载原模型；同SDK逐段89,920samples（公开WAV末帧补齐20ms，含flush320）最大float误差5.96e-8/RMS7.17e-9、样本数一致；两线程设置的281帧VAD均与SDK逐帧相同。

1线程整帧均值18.1359ms/P9529.5556/max49.8216，77/281帧仍超20ms，进程CPU92.57%单核基准，峰RSS93,772kB。实际新路径阶段均值FFT0.2177/ORT13.8639/IFFT+OLA0.6143ms；主要剩余开销为模型ORT。2线程反慢至20.3006ms/P9534.0295。均值短样本吞吐有进展，但严格20ms/长稳仍未通过，继续保持候选，未接生产采集，也没有异步排队、调频或丢帧掩盖问题。

Windows合并46项控制器/ASR/HTTP/FFT边界回归通过。新候选目录/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451，ORT deps明确只读交给ECAPA代理复用；串口随后明确释放/echo恢复，已直接通知board_memory开始其root安排的独立ECAPA验收。本代理未触动用户最新暂缓的portrait_offload、动画素材、GUI/渲染入口，也未修改现役业务、真实库、身份模板、机械或固件。
