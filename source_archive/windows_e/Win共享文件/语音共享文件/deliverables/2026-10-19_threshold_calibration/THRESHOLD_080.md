# 0.80人脸匹配试用已加载

2026-10-19用户同意下一轮试0.80并要求继续。活动匹配阈值已由0.85改为0.80，本地开发配置同步；旧保留0.85的要求在此次明确授权范围内被更新。0.1身份间隔、至少15秒自然视频选样、最多24份RAM候选、一个实际代表特征、5份连续独立新帧验证、原始锚点核对和明确姓名/登记确认均保持。

## 已核实结果

- 新门槛的真实匹配器边界：0.7999拒绝、0.80及0.8001通过；分差不足0.1仍拒绝/歧义。采样usable门槛与匹配器同用0.80。
- 使用固定公开Lena图片，板卡YuNet/对齐→Windows同一SFace CPU→板端临时库，完整开头确认、自动取样验证/保存、重新识别及失脸清除通过。逻辑时钟顺序驱动，不注入姿态/质量，不接触用户身份库；这不是新真人登记成功。
- 最初对话未停止时，闲置保护拒绝切换且没有改配置；对话停止后切换完成。仅相机身份服务为加载门槛重启，22份活动源与人体DPU/ByteTrack配置保持，原身份库0条/模板0份、修订13及哈希不变。
- 随后设备重新启动，已重新核对活动配置仍0.80/0.1，身份库仍空、权限0o600，活动22份源码一致。当前相机PID 987，boot `91b0d659-6959-43f1-83f2-4b24c6c81c5d`；这些是当前快照，后续应动态读取。
- 设备重启后电脑8791/8792未运行，已按原启动器恢复Paraformer、原27B/IQ4_XS及OmniVoice16与SFace CPU。界面先于电脑服务启动，首次获取提示资源失败，故在对话停止状态下重载原界面，恢复feedback_ready和开始对话按钮；未修改业务源码或音频/模型参数。
- 当前开始对话可用，自动对话仍未开启。未代替用户录音/发起真人登记，未在玩偶播放测试音。

## 使用步骤

点击开始对话，说“帮我登记身份，我叫……”；听到复述后说“确认登记”。从空库登记新身份，不需要“确认更新登记”。慢慢自然转头，听到“看向镜头，稍停几秒”后看回镜头等待结果，末尾不用再次确认。

0.80在前次保留24帧上可通过分数条件，但不同人对照及新真人登记、离场重返尚未验收。不能称为最终校准阈值或稳定识别完成。用户下一次反馈应结合新会话实际COMMITTED、分数与库修订判断。

## 活动路径、证据与回退

活动UI/相机源码仍 `/home/root/aura-windows-face-features-20261019/candidate-8ad60843f9d1/runtime`，身份配置 `/home/root/aura-windows-face-features-20261019/candidate-8ad60843f9d1/camera_live_config/board_identity.json`；有效配置副本 `effective_config_080/board_identity.json`，本地配置 `aura/config/board_identity.json`。同一配置内的threshold同时用于库内识别、登记新帧验证及换轨原始锚点核对，原0.1分差保持。

本次回退只需在对话停止时恢复配置备份 `/home/root/aura-windows-face-features-20261019/candidate-8ad60843f9d1/camera_live_config/threshold-080-backup-da37e23698/board_identity.before.json` 并重新加载相机服务，即回到0.85。备份只含配置，不含用户数据库/模板；不得恢复已删除身份。原较早阈值提案脚本仍属历史，不能运行其中的0.363提案代替本次0.80。

证据：`threshold_080_activation.json`、`threshold_080_preflight.log`、`threshold_080_current_verification.json`、`threshold_080_ui_recovery.json`、`threshold_080_verification_summary.json`。以前0.85失败/离线比较、全部删除记录分别保留，未修改为成功。未保存现场照片/视频或导出姓名/模板，大语言模型数据仍D盘。
