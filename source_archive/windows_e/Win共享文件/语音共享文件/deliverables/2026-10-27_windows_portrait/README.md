# Windows画面合成部署与验收（2026-10-27）

**已部署：Windows CPU合成，板卡现有单一native sink送显，目标16fps；断线自动回退板卡8fps。** 最终仅修复设置页按钮布局的版本也已提交，实测 15.925fps，帧间隔P95中位70.91ms、P99中位91.68ms。24fps未达到原门槛，未保留为生产配置。

用户明确授权“允许停止跟随并继续部署”后，通过既有UI停止入口安全退出持续跟随；最终跟随关闭、转轴读回1422、无活动运动、监听/麦克风关闭、访客模式、IDLE_READY，音量恢复原70%且未静音。只读等待心跳已通过工具删除。整个玩偶项目仍未全部验收，范围与限制见下。

## 当前入口与架构

正式根：`/home/root/aura-windows-portrait-20261027/layout-4fca8de03dc84c989f84d7814a984bd3`；启动器：`/home/root/aura-windows-portrait-20261027/layout-4fca8de03dc84c989f84d7814a984bd3/startup/launcher.py`。本任务只管理32个z前缀的独立systemd覆盖，全部旧覆盖与原UI保留。最终入口、boot、组件哈希与状态见[最终核验](final_verification.json)。不要用历史路径/PID覆盖并行机械更新。

Windows使用有线192.168.50.1:8796，CPU合成423×438 RGB。板卡保留FSM、PCM时钟、口型增益、动作、取消和对话控制。一个进行中请求、一份最新待处理请求，校验会话/代次/状态/音频样本/修订/CRC，接收与送显前均执行150ms期限；仅复用原native sink。断网本地绘制，恢复后切回电脑。设置页“电脑/板卡画面”按钮已调整至可见范围，未覆盖原个人记忆或机械入口。

676份现有视觉资源（188362769字节）两端哈希一致，没有复制素材或模型。所有LLM权重、缓存及Ollama数据保持D盘；未卸载或停止其他模型。`start_portrait.ps1`可独立启动；`start_voice.ps1`在原语音服务就绪后启动画面服务，`-WithoutPortrait`可跳过。未设置Windows登录自启动。

## 实际送显与功能验收

| 检查 | 实测与结论 | 证据 |
| --- | --- | --- |
| 原板端8fps基线 | 8.002fps；P95 165.74ms；UI CPU约139.2% | [原生部署](deployment.json) |
| 首次12fps | 11.922fps；P95 92.83ms；P99 118.48ms；UI CPU约55.55%；COMMITTED | [原生部署](deployment.json) |
| 16fps分级 | 15.868fps；P95 73.86ms；P99 101.96ms；通过 | [分级结果](fps_steps.json) |
| 24fps分级 | 23.414fps；P95 52.17ms > 52.083ms；P99 84.84ms > 83.333ms；未通过并恢复16fps | [分级结果](fps_steps.json) |
| 最终布局版16fps | 15.925fps；P95 70.91ms；P99 91.68ms；COMMITTED | [最终部署](layout_deployment.json) |
| 实际UI断线 | 停止本任务持有的Windows画面进程，原UI持续本地8.005fps、16份变化预览；恢复远端16fps，最大显示帧龄124.92ms | [真实断线](live_ui_outage.json)、[主机恢复](host_recovery.json) |
| 静音真实PCM/口型 | 真实MCP01播放时钟，硬件静音直接核实；11.53秒SPEAKING约15.525fps、19份变化预览、口型随PCM变化；恢复原音量 | [静音语音](muted_speech_probe.json) |
| 原生截图与布局 | 主画面/角色完整；设置页按钮可见；隐藏GTK检查控件无越界/重叠，选档取消正常 | [主屏](native_screen.png)、[设置页](native_settings.png)、[布局检查](full_gtk_layout.json) |
| 服务与状态 | 8791/8792 HTTP、8795/8796帧协议均可达；跟随/监听关闭、访客、音频就绪 | [Windows健康](windows_health_final.json)、[最终核验](final_verification.json) |

帧率来自实际native提交计数，P95/P99为采样中滚动帧间隔分位数的中位数，**不是面板光学扫描测量，也不是把所有窗口合并后的全程分位数**。CPU百分比按进程多核口径，不是整机利用率。短时基线比较不能证明所有收益均来自单一改动。

静音SPEAKING的P95/P99中位约99.57/132.04ms，尚不满足待机16fps门槛；本轮只证明真实PCM时钟、口型和远端显示连续。未开麦、未播放可听测试音、未恢复运动，不能代替真人听音/插话或持续实聊验收。设置页截图底部旧“屏幕3.9fps”来自GTK界面刷新采样，不能代表独立native sink的角色送显速率；实际值以avatar_display计数为准。旧`render_performance.py`日志的`target_fps=8`是固定历史字段，远端模式目标应看API/config，实际速率用提交时间戳/计数；该字段未在本轮扩大修改。

## 回归、失败与证据范围

初次ARM完整362通过/1平台跳过；最终核心Windows48通过、ARM专项67通过，互有重叠不能相加。最终GUI仅改两个布局位置/尺寸，核心Python逐文件与通过版本一致；GUI独立通过隐藏GTK布局、截图和实际16fps再验收。包清单明确区分这两种验证，不把旧GUI哈希冒充新GUI回归结果。

真实素材/静音虚拟PCM/网线的动作、口型、暂停、取消和模式切换见[live_headless.json](live_headless.json)；这些隔离测试不等于真人验收。实际断线期间的预期连接失败保留，不能声称全程零网络错误。

历史USB掉线及原音频恢复、远端额外等待导致150ms过期回退、等待持续跟随、首次布局启动检查过早误读旧API等失败均保留。布局首次失败已恢复原通过版本，重试增加新进程及实际启动路径核对，并重新通过完整原门槛；不放宽性能阈值。布局失败日志为`layout_deployment.log`，通过重试为`layout_deployment_retry.log`。

## 回退与后续

接续操作见[CONTINUE.md](CONTINUE.md)。日常可用设置页切回板卡绘制；Windows失联自动回退。完整UI回退脚本[rollback_ui.py](rollback_ui.py)默认只读核验，`--apply`仅在空闲、音频就绪、监听与跟随关闭、原源码/机械绑定一致时移除本任务自己的覆盖；原路径保留，其只读核验见[rollback_check.json](rollback_check.json)。不要为回退放宽硬件校验。

本次Windows画面部署的自动验收已完成。仍需人在场的新版听音、插话、选档、多人噪声、持续实聊，以及声纹/声画归属、视觉问答和机械现场验收；这些不应标为全部完成。其他模型继续运行，板端迁移另按既定方案推进。

[源码及小型证据包](source_and_evidence.zip)由显式白名单[脚本](package_release.py)生成，[逐文件SHA清单](SOURCE_MANIFEST.json)可复核；不含模型权重、视觉素材字节、虚拟环境、私钥、录音或数据库。
