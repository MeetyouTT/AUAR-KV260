# DPU身份相机后端与连续对话合并

2026-10-18 Ubuntu实施，UTC2026-10-19实测。

**最新状态（UTC 2026-10-19 04:42）：已恢复原相机与连续对话版本；实体花屏是否恢复仍待现场确认。** 新DPU候选未通过上线验收：切换期间两次观察到boot变化、结果未写出，重启来源未确定；候选活相机身份一次20.11ms触发20ms保护暂停。已停止继续部署并实际还原原两服务，运行目录及健康验收通过，相机约9.82Hz、无错误、帧龄98ms，原27B/OmniVoice16服务ready。实体屏幕此前花屏，系统截图完整、EDID实读为空；对原1024×600输出重新初始化的软件回读通过，但不代表物理修复。Windows登记接口仍未加载，语音登记关闭，未登记真人。

## 本轮完成

- [DPU SFace适配器](../../aura/board/identity/dpu_sface.py)：校验模型SHA、DPU指纹、张量/量化点，复用相机进程中的DPU；使用板端真实VART单参数元组wait签名。
- [检测优先调度](../../aura/board/vision/dpu_schedule.py)：检测优先，身份只用足够大的空闲时隙；身份超预算后暂停后续提交。已提交的硬件任务不能抢占。
- [同源人脸提取](../../aura/board/identity/camera_faces.py)、[身份服务](../../aura/board/identity/live.py)：DPU特征、独立模型模板库、3帧确认姓名及原5帧登记事务；CPU继续YuNet、对齐、匹配和数据库。
- [相机接线](../../aura/board/vision/ui_camera_service.py)、[DPU工程配置](../../aura/config/board_identity.dpu_engineering.json)。没有更换FPGA或语音模型。
- 回收实机较新的连续对话源码，与身份改动三方合并，保留自动端点、连续听说和worker方法。旧ec77目录只是历史副本，实际基线是 `aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b`。
- 两份接口JSON补齐多帧登记/取消动作，与Python校验一致。源码、改动前快照与恢复脚本保留，未同步私有人脸/身份库或原始UART。

## 验证

- [框架回归](framework-unittest.log)：289项通过，新增16项DPU/多帧一致性测试和2项跨接口schema测试。
- [实板固定输入](evidence/runtime-fixed-input/response.json)：4组输出逐字节匹配；80次YOLO+16次SFace无周期超时，SFace中位7.85995ms；公开人脸五帧聚合在内存中提交成功。不是实际用户登记或准确率验收。
- [暂存结果](evidence/runtime-stage/response.json)、[启动预检](evidence/runtime-ui-preflight-retry/response.json)。传输包72,604字节，SHA `858950aebbc11e1fd44f87f31b212455be6c519b3ee581ea249d81af107457c3`，板端已核对。
- [首次切换与回退](evidence/runtime-activate/response.json)、[回退后界面恢复](evidence/runtime-startup-detail/response.json)。启动器原有控制端口等待70秒，38秒就绪期限导致过早回退；回退后原界面/相机正常。
- [第二次空闲检查拒绝](evidence/runtime-activate-retry-detail/response.json)：当时正在处理/播放回答，未修改服务；随后已询问用户结束对话，未把等待时间当作许可。
- [用户结束后启动切换](evidence/runtime-activate-final-start/response.json)、[切换进展](evidence/runtime-activate-final-progress/response.json)、[重启后候选与预算保护](evidence/reboot-screen-diagnose/response.json)。随后再次观察到新boot；[重启证据](evidence/reboot-cause-evidence/response.json)无pstore、无持久化上一boot日志，原因未确定，未发送整板重启命令。
- [显示输出重置](evidence/screen-retrain/response.json)、[原服务恢复完成](evidence/restore-baseline-final/response.json)、[恢复后健康](evidence/restored-baseline-health/response.json)。系统截图与原始UART仅存Ubuntu私有目录，不进入共享交付。
- [最终核验与限制](verification.json)、[源码清单](source_manifest.json)。PowerShell脚本仅做源码审查，Ubuntu没有PowerShell，尚未在Windows实际执行。

## 下一步操作

用户随后要求每次开机重建HDMI输出，已在原活动开机配置设置关闭2秒再恢复，详见[设置与证据](../2026-10-18_hdmi_boot_reset/README.md)。后续候选部署必须继承此当前配置；本目录冻结的旧候选仍为历史工件，不要直接覆盖活动startup。

1. 原稳定基线已恢复。先确认实体花屏是否在输出重新初始化后消失；若仍花屏，保持板卡供电，仅重新插拔HDMI后复核EDID和面板。再定位活相机身份预算超限并重新验收。当前不能把两服务active写成身份已上线。
2. 屏幕与板端稳定后，Windows关闭当前对话，在 `Win共享文件/语音共享文件` 打开PowerShell运行：

```powershell
.\deliverables\2026-10-18_identity_dpu_runtime\update_windows_voice_identity.ps1
```

脚本核验冻结的3份语音源码与允许的原版本，先备份；如果发现其他本机改动则停止，避免覆盖。仅识别并重启8792对应的本项目语音进程及其子进程；保留ASR、Ollama、27B权重、16步参数和参考音色。目标是 `/health` 返回 `voice_text_channel=true`。本轮未替Windows执行或代填回执。

3. Windows接口就绪后，Ubuntu再启用板端语音登记开关并验证状态。当前开关仍false，不能仅凭重启电脑服务就宣称登记可用。
4. 最后真人验证：“记住我是谁”→“我叫…”→“确认登记”，检查事务、播报、离开重返、陌生人UNKNOWN、取消、删除和重启。真人校准与阈值评估独立记录。

候选位于板端 `/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93/candidate`，当前运行目录以实板复核为准。不要直接用该源码包覆盖其他较新语音版本。[实现与限制说明](../../aura/docs/DPU_IDENTITY_RUNTIME.md)。
