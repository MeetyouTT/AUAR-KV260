# 视觉追踪：手动转轴调节

用户要求在“视觉追踪”里增加转轴转向按钮，自己调整到中点后再通知Ubuntu做中位校准。本轮新增可选GTK入口，不修改原身份、相机、语音打断或GTK主文件。

操作入口为“视觉追踪 → 转轴调节”：左转、右转、停止；普通每次20µs、细调每次5µs，左右按钮方向可互换。显示实际寄存器脉宽，范围保持已测1400～1600µs；每次点动最长2秒，100ms独立硬件租约，忙时不排队，返回时停止。当前位置和临时REFERENCE不是已经校准的机械中位。调到正前方后，用户提供位置数值，再单独记录有效参考。

已安装到KV260并通过启动和原生调节窗口打开验收。上线时GUI195564 active，手动接口READY、读数1430µs，flags0/lease0/epoch8/ACK46；安装与打开窗口没有发送点动，history为空、自动跟随关闭、中位未校准。相机106060前后同进程、约9.93Hz、identity=true、无错误，原230项组件SHA保持。

339项完整框架回归通过，其中15项为新增手动控制测试；同15项在KV260也通过。首次默认Python因缺NumPy导致2项环境错误，改用已有host-env后全部通过，没有安装依赖。真实GTK/Xvfb按钮测试通过，调节窗口576×370，三个按钮均172×64；预览使用模拟硬件，不包含真人照片。用户后续触摸点动和实际左右方向由现场验收，不能把模拟按钮测试写作实体转动通过。

板端基线实读是voice-barge-in候选667b70d586ca，主GTK SHA a4b64d02…，当前共享GTK比它旧，不回灌共享旧版本。新启动入口引用该现有runtime，仅附加5个源码/测试文件和1个本板接口配置；原230项组件SHA保留，采用独立systemd drop-in，失败可恢复原入口。已完成一次受控界面重启，相机未重启、未切固件、未自动点动或校准中位。共享打包器另增--manual-pan可选入口，并验证972个运行载荷的收集包含所需模块，不包含本板许可配置。

板上该新版启动配置继承的HDMI关闭时间为1秒，新入口恢复用户此前要求的2秒；保留原同boot显示恢复标记，不因本次界面重启反复关屏。保留27B、OmniVoice16、连续对话、语音打断和身份服务配置。

- [源码](source/tools/board_avatar_pan.py)、[界面扩展](source/tools/pan_controls.py)、[有限控制器](source/board/motion/manual.py)、[板端适配](source/board/motion/manual_vsrv.py)、[测试](source/tests/framework/test_manual_pan.py)
- [GTK按钮检查](host-gtk-check.json)、[模拟调节窗口](host-manual-dialog.png)、[部署计划](deployment-plan.json)
- [板端安装结果](evidence/results/deployment-result.json)、[KV260的15项软件测试](evidence/results/board-policy-tests.txt)、[原生调节窗口打开回执](evidence/open/response.json)
- [Windows后续保留与回退](Windows_接入说明.md)、[文件核验清单](verification.json)

本接口按当前boot和已核验联合平台配置开放，错误平台或新boot不自动ARM；正式跟随仍关闭。调整期间GUI持有唯一Native锁，不应同时运行旧台架脚本。窗口左右互换是手动按钮的含义，不能直接当图像跟随polarity。Windows后续更新运行版本须合入这5份附加文件并保留可选入口，双方回执分开填写。
