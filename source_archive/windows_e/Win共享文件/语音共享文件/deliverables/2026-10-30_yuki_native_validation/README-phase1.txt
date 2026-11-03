首轮雪妃板端验证，2026-10-30

最新修正：用户指出的鼻部白块已在独立离屏渲染器中修复。此前透明颜色保护预处理把GL_ONE_MINUS_DST_ALPHA误写成GL_ONE_MINUS_DST_COLOR；这是诊断渲染器的参数错误，未修改模型或纹理。板端三个真实GLES2回归用例均复现旧版错误并通过修正版检查，原43帧重绘完成。最新图片见evidence/nose-fix-captures/和evidence/nose-fix-static/，修复证据见nose_fix/verification.json。原evidence/candidate-captures/保留为修复前历史，整体模型兼容与实时帧率仍未验收。

结论：板端原生求值及GLES2离屏绘制的技术链路已跑通，但固定版本的NekoMote不能直接作为雪妃的正式运行时。当前候选没有部署到现役GTK界面，未通过画面还原、自然待机或实际显示帧率验收。

固定上游提交：4fbf55aa6009df76ac40dc5f18e3781914bc464f。
独立板端目录：/home/root/aura-yuki-validation-20261030。
从原项目现存的yuk_0.ems.psb重新导出EMS JSON/resx/RGBA图集，没有修改原游戏或原模型。

原版结果：ARM编译及结构导入通过；初态和20条时间轴均在第0步被UnsupportedMask拒绝。失败节点260既属于mask11的来源，又受mask11约束。来源标签解析正常，不是缺文件或跨scope名称配置问题。完整证据见evidence/cpu-audit.json和agent_audit/mask_failure_analysis.json。

隔离候选：仅在mask来源绘制副本上解除同号的自遮罩，保留跨mask拒绝和所有物理。该实验通过初态180步及20条时间轴各180步求值。此修正可能掩盖来源集合过宽，不能当作正确遮罩语义已实现。固定上游源码保留未改，候选另在probe_build/geometry_selfmask_candidate.cpp。

板端输出：C++在ARM上导出固定作者步长的帧数据，板端Python ctypes调用Mali-400/GLES2绘制，生成41张动态场景诊断帧和2张静态参数对照帧，均423x438。覆盖两种姿势、六表情、眨眼和嘴部开合。这里不是持续实时GTK宿主，截图/读回耗时不能解释为显示FPS，也没有接入真实PCM播放时钟。

仍待验证：43个非空meshCombinator（122项控制）尚无固定核心的对应消费路径，影响身体、头部和头发变形。平静静态对照的37项可见变量一致；害羞对照在第0步的face_mouth仍延迟提交，原引擎与候选的内部物理状态也未对齐，因此没有像素等价结论。对照和候选均保留，不以“能出图”判定还原通过。

保护核对：466份固定源码、依赖和输入文件哈希保持，原项目EMS PSB哈希保持；现役UI进程和启动入口保持。没有生产部署、开麦、音频播放、机械动作或语言模型推理。板端验证进程已退出，本机只读参考服务已关闭，浏览器尺寸已恢复。

关键入口：verification.json；evidence/cpu-audit.json；evidence/candidate-cpu-audit.json；evidence/candidate-captures/；evidence/static-reference-captures/；reference-normal-matched.png；reference-shy-matched.png。失败的构建、导出和着色器尝试也保留，未计为通过。

下一步应先确定正确的mask来源边界，并补齐或核验组合网格求值，再写最终GLES2/GTK宿主和验证实际帧间隔。现有诊断脚本、固定依赖及独立CMake工程均在本目录，可用于复现；不要运行历史生产恢复或切换脚本来启动本候选。
