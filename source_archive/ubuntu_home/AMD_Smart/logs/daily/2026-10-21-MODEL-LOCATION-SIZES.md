# 各模型实际处理位置与大小核查

2026-10-21 America/Los_Angeles，采集为 UTC 2026-10-22。用户要求检查现在各模型处理位置与大小。已重读 ZIP README、整体方案和当前分工、共享入口及最新日志；实际状态以本轮只读串口与文件证据为准。

实读活动配置发现 SFace 已改为 `windows_sface`，源代码标记 `WINDOWS_CPU_SFACE_ORT`，目标 Windows 8792；它不在当前 DPU 生产链执行。YOLO 仍为 KV260 B4096 DPU，YuNet 为板端 CPU。实际板端文件大小：YOLO 2,127,303 B、YuNet 345,478 B、SFace 参考 ONNX 38,696,353 B；SFace DPU 已测候选本地 10,796,371 B，当前未选用。

本地共享权重实查：Paraformer INT8 243,371,218 B；OmniVoice 主网络 2,450,344,112 B、audio_tokenizer 805,665,628 B，权重合计 3,256,009,740 B。27B 位于 Windows 项目外 D:\AIModels，采用 10-18 保存的 Ollama size 13,885,180,476 B、27.3B/IQ4_XS；没有实读 D 盘。语音三模型 Windows CPU/GPU 分工依据服务源码及已接受的运行记录，本轮板卡访问8791/8792均超时，不能宣称 Windows 在线或远程身份已成功。

三次 UART 事务响应校验通过并恢复回显。当前相机1017/界面监督1078 active、零重启；真正相机健康接口8790/health读到检测9.91Hz、相机/检测错误为空、身份功能启用。最初两个本地探测路径错误已纠正。板卡时钟为2021年，采集以主机UTC标记；没有改时钟。初次沙箱串口不可见，获提权后可访问，未当作板卡掉线。

本轮无业务源码/配置/服务/位流/显示/运动改动，未执行新推理、下载、部署或峰值内存测试。ONNX依赖接口不兼容，未统计其参数量；不影响 stat 文件大小。过滤报告及证据已写入[共享交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_model_inventory/README.md)，原始 UART 留私有。Windows 同步与实时模型驻留、真人精度仍未验证。
