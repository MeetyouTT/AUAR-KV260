# 雪妃物理与手臂动画 R2

本轮按用户补充要求，重点增强部件物理反馈和手臂摆动幅度。R2 已发布并由原 GTK/EGL 界面实际加载；380 项绑定一致、角色可见、运行故障 0。已检查板端原生录制，用户现场观感反馈尚未回传，故实屏人类验收仍标为待确认。

可以直接查看 [前后 GIF（左原版、右新版）](previews/final_R2/before_after.gif)、[16fps MP4](previews/final_R2/before_after_16fps.mp4) 和 [抽帧总览](previews/final_R2/contact_sheet.png)。GIF 为 8fps 便于预览，MP4 保留 16fps 时间轴；两者均由 KV260 原生 GLES2 离屏画面生成，不是物理面板录像，也没有现场音频、人物或摄像头画面。

## 已实现的变化

- 原 A/B 两套姿态、四条手臂分支加入连续转动。以原图袖口顶部的肩部附着点为支点，做位置补偿；中立首帧与原版逐像素相同。
- 左右臂使用各自的阻尼弹簧状态，保留角速度；开始、回摆和状态切换不重置相位或动量。强弱随待机、思考、回答平滑变化。
- 增加小幅头部/躯干驱动，在现有 60Hz author tick 内让原锚点带动原物理链；头发输出倍率 1.35，附属部件 1.40。原物理求解器、角色图、纹理、构图和原身体呼吸保留。
- 原口型、PCM 所属、150ms 过期保护、取消/暂停闭口、原眼部策略通过实际 ARM 回归。眼部平滑探索未纳入本次发布。

16 秒待机参数检查（除去前 3 秒预热）中，新增左臂关节角 -7.10°～7.81°，右臂 -5.10°～4.94°。这是局部关节驱动角，不是实体转轴角，也不是整条手臂在屏幕上的总轨迹。

## 验证与性能

| 同负载真实 KV260 离屏 A/B/B/A，合计 40 秒 | 原版 | R2 |
|---|---:|---:|
| 完成帧率，各两轮中位 | 16.000 fps | 15.997 fps |
| 完成一帧 P50，各两轮中位 | 16.96 ms | 17.14 ms |
| 完成一帧 P95，各两轮中位 | 18.47 ms | 18.57 ms |

该对照使用同一相机实例、同一模型/纹理、423×516 尺寸、同种子及时间轴。计时包含 glFinish，计时环无截图读回；GUI 停止，不等同物理面板呈现帧率。没有宣称提速。

原主界面 20 秒样本约 15.34 fps，新版加载后 20 秒约 15.61 fps，均来自真实 swap 计数。两窗口之间恢复了退出的 Windows 模型接口并重启 GUI，环境不同，只作各自运行观测，不作为因果提速 A/B。

ARM 两版各 1536 帧、2 姿态×3 状态参数回归通过，并运行原口型/眼部/owner/过期测试。192 帧×原版/R2 的主姿态对照、96 帧×原版/R2 的 B 姿态对照已留存。原素材中立首帧在两套姿态均为 0 个差异像素。已抽查两套姿态的肩部、袖口和手臂连接；这不扩展为多小时稳定或新真人声画验收。

## 发布、依赖恢复与范围

当前 startup `3faab0eb9616a7509ec8f2d72d2b95a7709a830bce1e143cbe8d2d73d385f222`，原生库 `0c73b9389c11def8e93aab540f73f2c011abdf93f47d2a16f9a0bbadabf9f199`。只替换原生库及其三份绑定文件，另 376 项组件保留。[发布清单](release/MANIFEST.json) 给出逐项前后 SHA；[运行就绪](validation/R2_READY_RECOVERED_WAIT2.json) 与 [后测](validation/LIVE_AFTER_R2.json) 给出实际进程指纹。

首次正常 GUI 启动在原模型接口 Date 校验的 socket connect 阶段失败，未进入动画初始化。新鲜检查确认 8797 无监听、原模型 owner 已退出，维护方确认没有停用安排。沿原 start_inference.ps1 -Action Start 恢复同配置 aura-qwen3.8-27b-abliterated:iq4_xs / OmniVoice 16 步；恢复健康后另留一次明确的新 GUI 启动事务并通过 READY。没有循环重启或降低原时钟校验。[依赖恢复回执](validation/MODEL_RECOVERY_RESULT.json)。

当前监听偏好保持本轮接手实读的 false，麦克风关闭；相机原 owner 不变，未运行转轴、DFX、R7 或相机重启。业务、身份、声纹门槛、音色及记忆机制保留；没有读取或导出私库、登记模板、现场录音。

E:/AUAR_工程交付_20261102 的原包和 SHA 清单保持，现逐项核对仍匹配。[原交付校验](validation/ENGINEERING_BASELINE_PRESERVED.json)。本轮新版本单独归档：[动画覆盖包](release/animation_overlay_R2.zip)、[原生源码及二进制](release/native_physics_arm_R2.zip)、[回退说明](ROLLBACK.md)。

## 留存的失败与未采用材料

第一版围绕图片中心转动，出现袖口脱离，已拒绝；证据保留于 previews/contact_sheet.png、board_results/previews/candidate_v1。R2 改为原始图集中测得的肩部顶部支点并重新编译/录制。首次 R2 暂存脚本生成错误及缺少暂存源导致的编译拒绝，保留于 board_results/revision2/steps.json；最终实际工件为 revision2b，来源逐项与 candidate_physics_v2/native 匹配。

早期 baseline/native 的 e2 连续微动并非现役 b243 库，已用原编译回执校正，正确基线在 baseline/actual_native 与 baseline/ACTUAL_LIBRARY_SOURCE_LINEAGE.json。candidate/ 的眼部探索未加载。首次缺 Origin 的页面请求未通过校验；确认页面未变后按原接口补齐 Origin/Host，再取得有效主页面基线。以上失败未套用为通过记录。
