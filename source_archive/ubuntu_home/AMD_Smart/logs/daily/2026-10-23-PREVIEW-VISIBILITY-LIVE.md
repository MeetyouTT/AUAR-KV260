# 隐藏预览生命周期修复已上线

用户继续并明确允许两个终端。主任务独占UART/板卡，第二任务仅本机源码/测试与发布流程审查；未开启第三任务。开工已读ZIP README、项目规则、共享入口和上一轮GUI CPU记录。

原版实测：视觉页5秒63帧，切回主页面后隐藏预览仍5秒63帧；queue1:src仍约36.7%单核。现役源码缺少vision unmap解绑。修复仅2源：board_avatar_gtk.py添加map代次/unmap退休；board_camera_preview.py在无输出时不读取服务/帧，以输出身份和生命周期锁处理旧推流/回调，清理handler/probe。原像素/缩放管线、角色8fps、音频及模型不改。

15生命周期＋16发布协议离线检查通过，交付内31项复跑通过；5项真实GTK/Gst/X11离屏合成帧检查通过。第一次GUI切换前被已有YuNet保护拦住。第二轮实测GUI CPU下降36.80%，但整体camera gap0→1，因此拒绝并真实恢复前GUI528120；guard退出，相机499773保持。唯一gap下/上界8ms，单调时间早于候选run标记68.112秒，证据保留，不追认为接受。

最终66cde810…受保护GUI-only验收：保留已有gap1/fault2，均不增不减。每组约16秒：原主页面GUI组149.8818%单核→94.8821%，下降36.6954%；隐藏帧201→0。视觉页CPU148.84→147.36%、预览12.49→12.73Hz；重新进入12.68Hz。角色主页面8.049→8.058Hz，P95间隔152.33→134.04ms。仅对隐藏预览页面的GUI进程组成立，不是整板CPU或模型加速比；原输入非逐帧配对，不降低可见帧率。

当前boot7924ac9f…，camera499773/GUI535987/Xserver1077；camera unit29786434…不变，本轮相机未重启。GUI runtime `/home/root/aura-video-cpu-20261023/66cde810eb059dce/runtime`，新增13z自有override，旧12z及其它配置保留。175份Python回读仅2源变化，原native库/不可用身份处理/新旧DB及偏好保持；只读GUI回退入口通过，controller与timer均退出。前一轮实际恢复已留证；本轮共有3次GUI启动转换，不能以NRestarts0称未重启GUI。

模型当前状态必须区分：YOLO DPU；SFace DPU后端ready、累计52完成/0超限，接受窗新增0；YuNet CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN。当前相机已有32.704/37.069ms两次硬超限，后一guard越界约1.536ms，均native完成status0/owner未fence，策略锁定。另上一进程450495的3次故障已归档；本轮没有清计数、改30ms/5ms/TTL或重启相机让它恢复。验收新fault/gap/主周期超限/USB告警均0，根因仍未解决。

完整源码、失败、当前入口与回退：[已交付包](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_preview_visibility_live/README.md)。59文件SHA封存、18 Python AST、20 JSON解析和候选SHA匹配通过。原始串口/身份原库/模型权重/真人图音向量不进入共享。Windows回执未修改、同步接收未代确认。

下一步仍是YuNet提交/返回的墙钟长尾与guard越界、SFace有界恢复、异人/多人、冷启动和整机长稳。此轮只完成GUI可见性修复。
