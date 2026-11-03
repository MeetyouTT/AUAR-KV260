# MCP01 USB告警：已核验机制、恢复边界和最小诊断

本文件属于独立音频终端的本地审查，不接板、不改现役/内核、不重置USB、不公开提issue。板端操作与回执由主端串行执行。以下源代码是Xilinx官方2022.2发布标签，Makefile为5.15.36，与现板版本文字一致；尚未据此证明板端内核二进制没有额外补丁。

## 错误分层

[Xilinx 2022.2 xHCI处理](https://github.com/Xilinx/linux-xlnx/blob/19984dd147fa7fbb7cb14b17400263ad0925c189/drivers/usb/host/xhci-ring.c#L2807)中，当前文本属于`COMP_DATA_BUFFER_ERROR`，映射`-ENOSR`。同一switch把带宽溢出、split transaction失败、等时ring underrun分别处理；不能把这些不同completion code混为一个原因。Linux对[USB错误码的说明](https://docs.kernel.org/5.17/driver-api/usb/error-codes.html)将OUT的ENOSR定义为主控从系统内存取数未及时跟上USB数据率；该定义不直接给出供电、线材、TT带宽或器件损坏的结论。

full-speed MCP01经过HS hub需要TT；[同版本xHCI代码](https://github.com/Xilinx/linux-xlnx/blob/19984dd147fa7fbb7cb14b17400263ad0925c189/drivers/usb/host/xhci.c#L2353)具有TT带宽核算。与摄像头共享HS hub是应核对的拓扑事实，不等于带宽已超限。共享上行/TT/主控DMA/调度各层必须通过实际对照或对应完成码区分。

## 为什么RUNNING、指针推进和Gst无ERROR仍可能伴随告警

[同版本snd_complete_urb](https://github.com/Xilinx/linux-xlnx/blob/19984dd147fa7fbb7cb14b17400263ad0925c189/sound/usb/endpoint.c#L510)对OUT流并非见到任何包错误就停止；它先处理退出类状态，常规路径继续retire/prepare并提交URB。提交失败才走XRUN通知等错误流程。[播放retire回调](https://github.com/Xilinx/linux-xlnx/blob/19984dd147fa7fbb7cb14b17400263ad0925c189/sound/usb/pcm.c#L1503)也没有逐项检查iso_frame_desc的包状态。Linux[USB错误码说明](https://docs.kernel.org/5.17/driver-api/usb/error-codes.html)区分整个等时URB状态与每帧描述符错误。

因此，ALSA能继续RUNNING、指针能推进，而某些USB等时包已经有错误；仅靠appsrc队列、sink position或IDLE_READY不能作为USB外部健康验收。这是源码支持的机制解释，不是此次现场已经捕获每包错误分布。

队列保护候选只修复另一层：GStreamer内部appsrc在block=False时的无界积队。它不会改变USB完成码、TT排程、DMA或忽略日志，不能用队列对照通过宣称告警根治。两类问题需分别记录。

## 最小诊断顺序

1. 核对当前设备身份与拓扑：17ef:a03b、MCP01、实际card/1-1.2/slot04和端点0x02是否仍对应；核对当前输出确为48kHz双声道S16LE ADAPTIVE，捕获端16kHz mono ASYNC不能冒充播放格式。无依据不降成设备不支持的低采样率/mono输出。
2. 同一3秒窗口采样PCM status/hw_params/sw_params及精确slot4ep3告警计数，保留owner PID、hw_ptr/appl_ptr原始差、delay/avail。`pcm_progress_readonly.py`提供该只读采样。主端已报告一次重连后样例：hw_ptr+144240、appl_ptr+144480帧，约48040/48120帧每秒，窗口0告警；这证明当窗在推进，不证明全部USB包成功或长期无复发。
3. 若告警复发，先保留同窗口CPU/IRQ计数、设备power/runtime_status、hub TT单/多TT信息、xHCI slot/endpoint context及完成码频率。不要先清日志、改printk或周期性重启来抹掉诊断条件。
4. 仅在以上不足时，由主端考虑至多数秒的usbmon/已有tracepoint元数据采样；先核对内核是否提供对应接口，避免捕获或共享音频payload。不要全局开启重型trace、构建新内核或创建第二个音频owner。内核日志已经能确认的事实不必用额外跟踪重复证明。
5. 正常空闲时关闭并重建**已有**PCM管线可作为受控恢复；保留前后错误计数/身份/位置/音频状态。已有一次约1小时55分钟后复发，说明一次恢复不是根治。现役没有单独维护IPC时，不假造命令或在业务播放中重建。

## 能软件纠错与仍需物理对照的边界

可确定的软件缺口：本候选修复appsrc队列上限与有限等待；现役健康表达缺少USB外部完成码，不能把IDLE_READY当外部健康。受控PCM恢复不需要改采样格式或清故障历史，但也不能保证不复发。

暂未找到可直接适用于17ef:a03b的官方修复或型号quirk证据。[snd-usb-audio配置文档](https://docs.kernel.org/6.9/sound/alsa-configuration.html)中的nrpacks是每URB包数；ignore_ctl_error针对mixer访问，implicit_fb针对反馈模式，均不应凭此文本盲启。下列措施缺少当前证据：修改内核、增加PS/DDR优先级、调USB quirk、关闭autosuspend、降低不支持的格式或关闭语音。

如果同格式、同业务下仍反复出错，应在用户返场后做可复原的物理单变量对照：MCP01换同规格线/端口、使用合适的供电hub、让摄像头暂离同一上行路径。每次核对拓扑与语音/视频影响，保留同窗告警率和PCM状态；这些是待验证实验，不是已经判定供电或带宽故障。用户不在场时不擅自断开设备或机械电源。

## 资料指纹

官方标签`refs/tags/xlnx_rebase_v5.15_LTS_2022.2`的annotated tag对象`054489d81f9c8dde1a7ba99d9a8daed405a25153`，peeled commit为`19984dd147fa7fbb7cb14b17400263ad0925c189`。`USB_OFFICIAL_SOURCE_PINS.json`只保存源SHA/符号行号，不复制整份内核源码。官方AMD[USB驱动页面](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841729/)列有历史device/UVC变更；未找到与本次MCP01 host OUT数据缓冲错误直接匹配、可据此立即实施的修复，不套用gadget模式修复。

## 最后一轮定向核查与返场最短步骤

按主端要求追加且仅追加一轮4条定向检索，范围是AMD官方支持/wiki与Xilinx linux-xlnx原件：DATA_BUFFER_ERROR、当前精确告警文本、isochronous host OUT修复。返回的ZynqMP/UVC/gadget历史说明、AMD SNPS suspend相关代码，以及其他平台同文本案例，都没有满足“本设备/主控/错误码/触发条件匹配”的依据。**未找到能对本案直接采用的已知勘误或补丁；本项结束，不继续泛搜或盲调。** 这不等于声称所有公开资料均不存在修复。

主端已报告KV260 Gst1.18.5真实无设备成对试验通过，106560→7680B；f5d队列保护已启用，GUI772087/camera720342、259pins、STOP1402，约185秒4个内核窗口0告警。这些板端数值由主端提供，最终取其正式回执；旧管线曾约1小时55分钟才复发，当前短窗仍不足以验收长期USB健康。

返场先用2分钟确认视频、语音功能和同窗PCM/告警，转轴保持停止。若需一个最小物理变量对照，优先在**同一端口、同一48kHz双声道格式、同一业务与供电**下，仅替换MCP01可拆数据线为已知正常的同规格线；若线不可拆或无备线，该步骤不能执行。A/B两次都采用相同的正常PCM关闭/重开步骤，避免将“换线”和“重连恢复”混为原因。随后正常使用中有界观察，记录达到旧复发时长前后的情况；2分钟0告警只算功能检查，不宣称换线根治。无备线时保留现状与日志，后续再安排独立上行/供电hub对照，不把它们一次全换。
