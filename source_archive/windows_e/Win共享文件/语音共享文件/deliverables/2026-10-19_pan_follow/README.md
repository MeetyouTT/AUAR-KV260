# 转轴跟随第一版

**本页是软件阶段历史记录。UTC2026-10-20已在最新handsfree相机目录接入实况motion接口和DPU+VSRV联合平台，PWM保持关闭，持续跟随/机械标定未通过。当前实际状态、回退过程和实体测试计划见[10月20日接入交付](../2026-10-20_pan_axis_integration/README.md)。** 下文“未加载/待确认”只适用于其记录时点。

**转轴接线后检查（UTC2026-10-20 06:56）：** 用户报告已连接转轴。本轮只读检查板卡/相机正常，约9.93Hz；当前仍加载官方DPU固件，VSRV驱动固件门槛未满足。板上联合版8个程序文件、4个固件文件哈希匹配，尚未加载；ZOCL引用计数3，视觉服务正在运行。本轮没有MMIO/ARM/PWM或服务重启。线序、独立供电/共地和摄像头安装方式仍待现场确认，不能据此宣称实物接线验证通过。见[连接检查清单](connection-inspection-20261019.json)、[当前板卡](evidence/pan-axis-connected-inspect/response.json)和[联合固件完整性](evidence/axis-joint-readiness/response.json)。下方为软件阶段结果。

2026-10-19用户安排：Ubuntu负责转轴跟随，Windows负责身份识别开发。UTC2026-10-20实施。

**已完成跟随控制、只读坐标接口、独立启动/旁路工具，以及主机和板端软件验证。真实相机跟随与舵机转动尚未启用。** 当前板卡官方 `kv260-benchmark-b4096.bit.bin` 不含VSRV；机构安装状态也尚未取得本轮确认。当前身份相机和界面是Windows较新的候选，未覆盖或重启。

## 改动文件

- [跟随控制器](../../aura/board/motion/follow.py)：低通/死区、源帧确认、速度/步长/范围限制，失联/过期/换人/重启锁定停止；支持随轴相机与实测固定视角锚点。
- [坐标合同](../../aura/common/motion_observation.py)、[只读相机扩展](../../aura/board/motion/camera_feed.py)：250ms源期限，绑定源帧、boot、相机/服务/轨迹代次，不输出照片或身份数据。
- [相机可选入口](../../aura/tools/board_camera_motion.py)、[旁路/回放工具](../../aura/tools/board_pan_follow.py)、[默认旁路配置](../../aura/config/pan_follow.shadow.json)。物理输出默认关闭，无隐式ARM或默认机械零点。
- [35项测试](../../aura/tests/framework/test_pan_follow.py)、[实现与运行说明](../../aura/docs/PAN_FOLLOW.md)。原身份、GTK、相机服务源码及已有VSRV驱动未改。

冻结包还包含原 `board/motion/__init__.py` 和 `vsrv_driver.py` 作为依赖，不表示本轮修改过这两份文件。源码、包和证据长度/SHA见[核验清单](verification.json)。

## 实际验证

- Ubuntu完整框架回归324项通过；35项为新增转轴/坐标测试。默认Python首轮缺NumPy且沙箱禁止本机套接字，改用已有host-env并开放回环套接字后通过，未为此安装依赖。
- [板端结果](evidence/board-results/result.json)、[板端测试日志](evidence/board-results/board-tests.log)：实际加载当前 `aura-enrollment-photos-20261019/candidate-6f1aa1842d53` 的CameraState，35项软件测试通过。
- [90帧合成输入](evidence/board-results/replay.jsonl)、[旁路轨迹](evidence/board-results/shadow.jsonl)、[回放总结](evidence/board-results/shadow.jsonl.summary.json)：输入均明确标为fixture，86次软件接受，最终REPLAY_ENDED/DISARMED。不是采集真人、角度测量或实时物理跟随。
- [临时HTTP端口验证](evidence/pan-follow-http-fixture/response.json)：新坐标路由与原/health兼容，未占用生产8790。
- [实板前置检查](evidence/pan-follow-precheck/response.json)：当前官方DPU位流活动，不读取未知VSRV地址；[最终板测](evidence/pan-follow-board-final/response.json)确认测试前后boot、位流、相机/GUI PID保持。

首次板端测试加载器不支持NamespacePath.insert，失败记录保留；改为显式路径列表后重跑成功。合成回放的最终工件已显式标记fixture，较早回放仅留Ubuntu私有历史证据。原始UART、实际相机图像和身份库不进入本交付。

## 下一步

1. Windows完成当前登记测试后，按[接入说明](Windows_接入说明.md)把三个新文件合入最新相机运行目录，协调一次相机入口更新；不拿旧运行目录或本包覆盖整套身份版本。
2. 运行10秒实况旁路，核对选中目标、方向、源年龄和丢失停止，仍不输出PWM。
3. 确认机构/相机安装、当前参考脉宽和允许范围；准备与现有DPU配套的VSRV联合平台后，再做受控转动、显式启动/停止接入和机械验收。不能向当前官方位流的未知地址写寄存器。

首版控制针对选中人体框的横向位置，不是头部朝向yaw，也不依赖姓名识别或LLM直接生成舵机指令。
