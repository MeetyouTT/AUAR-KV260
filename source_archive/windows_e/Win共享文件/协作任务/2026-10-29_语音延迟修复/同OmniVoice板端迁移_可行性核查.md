# 保留OmniVoice特性并迁往KV260：候选路线与验证边界

2026-10-29，用户明确希望保留现有语音特性，同时把文字转语音放到板卡。当前目标按同模型移植评估，不默认替换声线/模型，也不把演示音频缓存当作任意文本本地合成。

## 对此前结论的修正

现有AURA加载器在检测不到CUDA时主动报错，并固定device_map=cuda:0。这只能证明当前这份实现不能原样上板，不能推导“OmniVoice一定不能在CPU运行”或“上板必须换另一种TTS模型”。当前已找到OmniVoice的C++/GGML和ONNX社区移植，应先评估同模型路线。

本轮只核查公开代码和现有实现，未下载模型权重、导出/量化模型、安装依赖、编译或执行TTS。未动正式Windows服务/板端GUI/相机/FPGA/运动，未获取用户参考录音或真实库。

## 候选一：优先C++/GGML，同一OmniVoice模型

项目：[ServeurpersoCom/omnivoice.cpp](https://github.com/ServeurpersoCom/omnivoice.cpp)，本次固定提交`1a468d8b9d65b3544ca1004d2d7c05dfc65d1f3e`。

已读README、CMakeLists、buildcpu.sh与ARCHITECTURE：有CPU backend、C++17公共ABI、同OmniVoice参考音频克隆、步数配置、原权重转换和Q8_0主干。它仍是社区实现，不是AURA已验证部署。

- 文档列主干Q8_0约626MB、音频codec保留F32约702MB；合计约1.33GB是权重文件大小，不是运行RSS/峰值内存。需加工作图、激活、内存分配及当前视觉/GUI业务，不能由4GB物理内存直接判定可用。
- 参考WAV可先编码为RVQ，在每轮合成中复用，避免重复参考编码。必须用同一模型修订、codec精度和预处理生成RVQ；其他codec生成的代码不能混用。现有AURA已经在进程启动时创建prompt，因此“缓存参考”不是正式Windows链路新增收益，而是移植时保留已有行为。
- 同一参考可保留克隆目标，但Q8、GGML算子/随机数和后处理差异仍可能改变音色/自然度/输出；不能称与现有float16/SDPA/seed8701逐样本完全一致。作者的等价测试也不能替代我们当前中文、原参考和16步的对照。
- CPU构建脚本含删除build目录的命令，后续不直接执行；使用独立构建目录和明确aarch64工具链、ARMv8-A/NEON能力配置，不为提速误启Cortex-A53不具备的指令。仅凭CMake注释支持aarch64不等于完整KV260构建/推理通过。
- 所用GGML子模块有codec所需的SNAKE和COL2IM_1D CPU算子，需按固定子模块审计和构建，不能任意替换其他GGML版本。既有B4096 DPU没有该模型可直接加载的xmodel，本轮没有把C++后端称为FPGA加速。

## 候选二：ONNX高质量INT8，保留关键输出精度

项目：[AFun9/Omnivoice-onnx](https://github.com/AFun9/Omnivoice-onnx)，本次固定提交`bf7b87eda0198f45bf46198a029f86a214181576`。

项目有导出、量化、16步参数、参考音频克隆和数值检查，INT8-HQ保护audio output head的FP32精度，LM约611MB。该大小同样不含全部codec和运行内存，也不是整网都使用INT8计算。

源码infer_onnx.py的load_pytorch_model默认加载完整FP32 OmniVoice和audio_tokenizer，再用ORT monkey-patch三个入口；未看到同时释放原模型权重。因此当前示例不能仅凭611MB直接搬到4GB板卡，需先改成不重复持有完整PyTorch权重的推理架构，再验证所有前后处理。

作者i9-14900KF、32步的特定voice_clone RTF约6.69，不是KV260或我们16步的成绩，不能机械减半或外推ARM速度。“高质量INT8几乎无损”是作者实验结论，仍需原声线试听和独立文本验证。当前C++路线依赖较轻，优先用于板端可行性试验；ONNX作备选及数值对照。

## 原特性怎样逐项保留

| 特性 | 初始约束与验收 |
| --- | --- |
| 汐蓝原声线 | 同一已选择“柔亮俏皮”参考及准确转写，核对文件SHA，不自行裁剪参考或更换说话人 |
| 自然语音/中文内容 | 固定中文短句、长句、姓名、数字和标点，与现OmniVoice对照全文/听感，不仅检查非零波形或自动ASR |
| 现有生成策略 | 首轮保留16步、speed1.0/guidance2.0及已有采样和后处理含义；后端无法等价映射的项明确列出，不默默更改 |
| 音频与口型 | 24kHz单声道PCM16、原采样/取消代次/播放ACK与口型时钟合同保持 |
| 内存与业务并发 | 先独立短句加载/合成测峰值RSS和时延，再与视觉/身份/GUI共存；不以当前51.7%非满载CPU外推容量 |
| 响应速度 | 测初始化、首段合成、整段RTF、冷/热态和重复窗口；尚无证据保证板端与现Windows同速 |

当前合理目标是“同模型、同参考、保留所需行为，先验证可运行和听感，再评估速度”。如果最终必须同时满足完全独立KV260、与当前音质一致、当前低延迟，现阶段没有已验证方案可承诺三者同时达到；需要据实测决定量化/算子优化是否足够，而非仅改device或IP。

模型数据若进入后续试验，沿项目约定放共享树外的专用模型目录；转换来源、修订和实际路径写配置及manifest，模型文件/虚拟环境/真人参考不通过微力复制。Windows原模型保留对照。

## 来源与本轮结果

- [官方模型与克隆prompt复用](https://github.com/k2-fsa/OmniVoice)、[作者对CPU较慢的说明](https://huggingface.co/k2-fsa/OmniVoice/discussions/2)。
- [C++架构/大小/量化](https://github.com/ServeurpersoCom/omnivoice.cpp/blob/1a468d8b9d65b3544ca1004d2d7c05dfc65d1f3e/docs/ARCHITECTURE.md)。
- [ONNX量化与性能](https://github.com/AFun9/Omnivoice-onnx/blob/bf7b87eda0198f45bf46198a029f86a214181576/README.md)、[完整PyTorch加载路径](https://github.com/AFun9/Omnivoice-onnx/blob/bf7b87eda0198f45bf46198a029f86a214181576/infer_onnx.py)。

状态：`SAME_MODEL_CPU_ROUTES_IDENTIFIED / ARM_BUILD_AND_INFERENCE_NOT_TESTED`。本轮完成的是两条路线代码核查，不是板端语音迁移或音质/性能通过。
