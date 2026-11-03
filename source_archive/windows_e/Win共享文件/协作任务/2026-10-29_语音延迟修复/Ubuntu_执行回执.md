# Ubuntu：语音延迟单项修复

UTC12:46:07、12:47:17只读更新：Windows已是voice-chat-memory-20261029-r9/5a4fa28e…，ready/非busy、compact_grammar=false，其余五项和模型保持，原boot/GUI114923/camera21824保持。现有最近两轮提交到软件起答3.865955/3.588321秒，服务端首PCM3469/3234ms、准备均0.00ms、TTS缓存均未命中，完整完成。两轮上下文不同，不作为严格A/B；尚无Windows本人回执。上述是现场已有记录的只读核验，不是本轮重启或新跑两轮。07:56的待加载结论按时间保留为历史。

用户已授权执行先前说明的语音延迟修复。范围为关闭失败的原生通道探测、核对已有预热/保活、取得同条件延迟证据；保持现有27B、OmniVoice16、音色、记忆、视觉、FPGA、转轴及界面。

本机业务配置改动限定为 `语音共享文件/aura/config/voice_latency.json` 中的 `compact_grammar`，已保留备份和指纹；其他五项保持。Windows端请勿同时改此配置，接续前核对同步指纹。

初始检查：本机Linux，没有Windows PowerShell或已配置Windows SSH通道；无线接口为172.23网段，直接访问192.168.50.1:8792在提升权限后仍连接超时。串口设备在沙箱外可见。

已完成：UTC07:52和07:56两次独占UART只读探测成功，回显恢复。当前boot55152f95、GUI114923、相机21824保持，板端空闲、监听/跟随关闭。Windows实际为较新的voice-timeline-20261028-r2/bc9b8aad…，ready且非busy、原27B/Paraformer/OmniVoice16保持，compact_grammar运行时仍true；timeline_memory等新能力保留，不覆盖新版源码。

UTC07:53:40对共享实际语音配置执行已有单项脚本，compact_grammar从true改为false。修改前bc1202bf…，修改后72f3cf43…，原字节备份保留；独立JSON比较确认只有这一项变化，其他五项保持。再次预览不写入，见evidence/config-change.json。

本机环境缺pytest，改用标准库unittest执行既有13个不同测试：9通过、4个因Python3.8不支持shutdown(cancel_futures=...)报错；未改产品代码迁就旧解释器，原日志保留。Windows实际语音Python环境需补真实回归。

最后UTC07:56:05实时health仍compact_grammar=true，证实运行加载尚未完成，不能将共享配置修改称为已生效。没有Windows远程命令入口；README已写清当前版本保护、仅8792归属重载、同输入本机/网线对照、预热与保活核验及回退。已向用户询问Windows侧执行接续方式。

本轮未重启任何服务、未推理/录音/播放/运动、未改模型/音色/数据库或板端源码；未代填Windows回执。下一项为Windows同步收件及当前版本空闲重载，随后取得新鲜A/B结果。

Windows加载、同步接收和实测结果由Windows自己的回执记录，不由Ubuntu代填。
