# Windows现有服务恢复与板卡环境核对

现有r9服务已恢复并完成本轮核对，源码指纹仍为 `5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3`。七类服务就绪，两轮真实板端语音请求完整返回。转轴因重启后的四项平台不匹配继续保护停用，未解除保护或执行运动；本次不是整机最终验收或板端功能迁移。

## 服务恢复

恢复前Windows语音、前端、动画、视觉和记忆端口没有监听，Windows本次启动时间为 `2026-10-30T01:25:41.5000000Z`，晚于r9交付。通过原有 `start_voice.ps1` 恢复后台进程；既有Ollama端口复用，没有停止其他模型、修改源码或移动LLM数据。

| 服务 | 端口 | 结果 |
| --- | --- | --- |
| ASR | 8791 | 原协议就绪 |
| 对话/OmniVoice/对话记忆 | 8792 | r9精确源码、依赖就绪 |
| GTCRN/Silero前端 | 8795 | 二进制健康协议通过 |
| Windows CPU画面合成 | 8796 | 二进制健康、原资源版本通过 |
| CPU视觉模型 | 8810，本机 | health正常 |
| 外设/视觉时间轴/声纹 | 8812，本机 | device-timeline-v2、ECAPA就绪 |
| 项目Ollama | 11435，本机 | 原服务复用、模型在线 |

完整检查见[endpoints](endpoints.json)。板端已自动重新选中远端画面合成，目标16fps、回退8fps，错误字段为空；短时画面统计仅为观察，不能算说话或严格16fps验收。

使用当前板端既有ARM客户端发送两份公开16kHz录音，经过真实ASR/27B/OmniVoice16，网络PCM样本和哈希均核对通过，首PCM 2.254秒 / 1.750秒。本次共有0次TTS缓存命中，不作为新的优化A/B或稳定延迟保证。没有开麦、实体播放、成功播放ACK或持久测试对话。见[语音探针](voice_probe.json)。没有修改业务源码，因此复用r9此前355项回归，本轮新增的是恢复后的健康和实机链路核验，没有把旧数量再累加。

## 板端实际入口与并行更新

运行中的UI仍为PID `1296`，从 `/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/startup/config.json` 启动，实际根 `/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime`；相机PID `1333`，279项组件哈希匹配。本次没有重启UI或相机。

启动器执行结束时，首次收尾校验发现systemd配置变更，拒绝按旧配置继续确认，原结果保留在[recovery](recovery.json)。随后核对 `/proc/<MainPID>/cmdline`，确认并行更新只是把下次启动入口改到 `/home/root/aura-avatar-startup-speed-20261029/config.json`；当前运行进程、实际根及279组件没有变化。该更新完整保留，解决记录见[recovery_resolution](recovery_resolution.json)。今后须分别核对当前进程和下次启动unit，不能把daemon-reload后的unit配置直接当作当前运行入口。

## 转轴保护原因

| 校验项 | 当前 | 驱动要求 |
| --- | --- | --- |
| boot | `605eaf50-c66a-4559-bfc9-5ae177e0f305` | `55152f95-ea3a-4c6c-82e6-51bd553d96fd` |
| FDT SHA256 | `c8a30da016ff7ab9ad46b3aaa7a2b4f753d5fd3fbaa835d5bd26c36a637c28b9` | `a42fca38fffcf87db0cb2e51b354127ef0959b54eb864792285f8cead552c294` |
| FPGA镜像 | `kv260-benchmark-b4096.bit.bin` | `aura-visual-servo-b4096-wide-v1.bit.bin` |
| VART | benchmark-b4096.xclbin | aura-visual-servo-b4096-wide-v1.xclbin |

架构、板卡身份、FPGA operating和发布清单校验通过，所需已安装固件/驱动文件哈希保持；但上述四项不匹配，因此转轴显示FAULT / no MMIO。当前要求是 **wide-v1** 联合固件，不能沿用早期窄范围v1的恢复方案。

本次只读取驱动源码、配置和内核元数据，没有导入驱动、访问寄存器、重编程FPGA、更新绑定、填写标定或发送运动指令。当前脉宽读回为null，不能恢复历史1604µs或把名义1500µs当实测位置。最初读取fpga_manager的firmware属性被内核拒绝，已记录；最终镜像以驱动实际读取的 `/proc/device-tree/fpga-full/firmware-name` 核对，未写入任何sysfs属性。见[motion_binding_audit](motion_binding_audit.json)、[motion_platform](motion_platform.json)。

后续恢复转轴须与正在使用DPU的相机/并行任务协调，成套恢复匹配的wide固件、设备树和VART，重新核对本次boot及原发布/观察证据，再做现场受控位置、STOP与机械验收。不能只改boot/FDT字符串绕过校验；本次请求的环境核对不等于机械复机授权。

## 数据与最终状态

独立隐藏WMI从真实私有文件视图备份当前数据库，没有回滚旧数据。原144会话/276轮及相关事实/权限/来源表逐表SHA保持，183条视觉历史及其修订/游标、声纹源表同样保持。实时观察缓存从188降为187：唯一移除行已超过原86400秒保留期，其余187行逐行完全相同。这是原缓存策略在召回时自动清理，与长期视觉历史分离。

全表严格相等检查因这1条过期缓存变化而失败，原[database_verification](database_verification.json)结果保留；随后独立证明了只有过期行移除、保留行完全相同及所有历史源表不变，见[cache_retention_verification](cache_retention_verification.json)。没有人工删除、放宽机械校验或恢复旧快照，私有数据库/模板/备份未导出到共享目录。

最终监听、麦克风、跟随关闭，音频IDLE_READY，转轴保护停用。原有模型进程全部保持，LLM路径配置未变，数据仍在D盘。本次没有创建计划任务、自启动或心跳。当前可由用户在原界面开启语音现场复测；连续说话间隙、稳定延迟、短词唤醒、声画归属、声纹现场标定与整机长稳仍待后续。核验见[verification](verification.json)，状态见[PROGRESS](PROGRESS.json)。
