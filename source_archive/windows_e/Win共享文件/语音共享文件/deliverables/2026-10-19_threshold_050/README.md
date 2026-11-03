# 身份匹配门槛0.50已加载

用户明确要求“现在那就调成0.5”。板卡实际活动配置与本地`aura/config/board_identity.json`已由0.80改为0.50，`threshold_origin`标注为用户授权、尚未现场标定的试用值。此授权更新此前保留0.80/0.85的约定。

## 变更范围和验证

- 只修改`threshold`和说明字段`threshold_origin`。同一门槛用于实时身份比较、登记新帧验证及换轨原始锚点核对；0.1身份分差、模型、质量条件、单模板策略、15秒采样、连续5份独立验证和明确更新确认保持。
- 原生产匹配器在隔离内存库的0.4999拒绝、0.50/0.5001通过；0.1分差不足仍判歧义，登记判定使用相同0.50。这是参数语义检查，不是真人准确率验收。
- 仅为加载参数停止并启动一次相机服务。相机活动源161份和模型SHA不变，人体DPU/ByteTrack配置保持；界面PID与systemd配置保持，电脑ASR/27B/OmniVoice16/SFace服务未重启。重载后人脸检测、特征服务及界面READY重连通过。
- 正式库仍1身份/1模板/修订15、SHA不变；25张已保存登记图及会话保持，没有重新登记、导出模板或保存普通识别人脸。
- 后续只读状态为1张脸、UNKNOWN；当时人员与姿态未由用户确认，不当作本人受控测试，也不能将配置加载称为识别修复或误认标定完成。无需为此次参数变更重新登记。

## 活动位置和证据

板卡身份配置：`/home/root/aura-enrollment-photos-20261019/candidate-6f1aa1842d53/camera_live_config/board_identity.json`。

相机重载后PID为93153，仅是本轮快照，后续动态读取。界面PID41716保持。

- `activation.json`：授权、变更、边界和分差检查、源/模型/库保留验证。
- `current_verification.json`：参数持续生效和界面重新连接核查。
- `board_identity.effective.json`：本轮板卡有效配置。
- `board_identity.local.before.json`：本地变更前0.80配置。
- `activate.py`：本轮执行器，只接受原0.80，不应在已生效0.50时重复执行。

板卡旧配置只备份至`/home/root/aura-enrollment-photos-20261019/candidate-6f1aa1842d53/camera_live_config/threshold-050-backup-c10b52d08d/board_identity.before.json`，未备份身份库。回退时在对话/登记空闲后，仅恢复该身份配置并重载相机，同时同步本地0.80；不要恢复旧身份记录或旧界面。
