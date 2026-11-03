# 2026-10-08 项目进度复核

本次响应用户“看看我的进展到哪一步”，仅核对本地资料和既有原始证据；没有连接板卡、重测或发送运动指令。

## 结论

按 ZIP 当前四关划分，硬件与视觉主线已进入第二关（运动与基本交互），真实视觉命令短测通过，持续左右机械跟随仍待验收。不能据此认定三人共同第一关全部通过：USB 音频和主机问答小链本次未找到对应验收依据。

## 已有实测证据

- 10 月 8 日同一源平台的 DPU B4096 与 VSRV 单轴逻辑已上板；固定图 ResNet18 与基线一致；有限 PWM 命令、租约到期、拒绝及 STOP 已有板测记录。
- 镜像摄像头、HDMI、人脸检测与基本跟踪已有板端记录；当前人脸检测为 CPU YuNet，不能记为 DPU 检测或身份业务完成。
- 用户已报告脉宽增加时逆时针；映射采用左侧逆时针、右侧顺时针。最新短测只记录 CENTER/COUNTERCLOCKWISE 命令，不能宣称左右两侧均通过。
- 原始 20 秒时效测试：3422 个样本，年龄中位 100.0 ms、P95 132.6 ms、最大 194.1 ms，超过 250 ms 为 0。
- 最新视觉命令短测：12 条全部接受，有效宽度读回 1500..1506 µs；1.153 秒后 FACE_QUALITY 停止，continuous_control_passed=false。
- 独立收尾读取 flags=0、lease=0、active/armed=false，预览继续增长。此为记录时状态，不是本次实时查询。

## 下一步及未验证事项

先调整机位/距离，使整张脸入镜，再进行有限左右移动与目标丢失测试，补齐连续随动和现场机械方向反馈。机械参考脉宽、左右指向锚点、完整机构标定仍未完成；速度调配按用户已有决定留到 3D 打印机构完成后。

板端身份登记/识别业务、DPU 视觉模型、MCP01 录放音与问答、Light-ASD 及整机长稳验收，本次没有核验到完成证据。

## 核对来源

- `/home/ghmd/下载/项目.zip` 内 `项目/README.md`、`项目/方案/AURA_当前现状三人分工_2026-10-02.md`
- 当天 `VISUAL-SERVO-SOURCE-PLATFORM`、`VISUAL-SERVO-POWERED-BOARDTEST`、`CAMERA-MIRROR`、`SERVO-DIRECTION` 日志
- `/home/ghmd/kv260-realtime-vision-20261007/CURRENT_RUNTIME.json`
- `/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T145623.194004Z-visual_freshness_probe/result.txt`
- `/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T145728.382694Z-timing_visual_direction_start/result.txt`
- `/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T150007.702243Z-vsrv_final/result.txt`

验证方式：对照方案、最新日志、运行状态和三份原始结果；未新增硬件或软件测试。只新增本日志，未修改工程。
