# 原板端人脸随动实测收尾（2026-11-01）

已按用户要求恢复原板端跟随，并将人脸跟随方向从 -1 改为 +1。用户本轮反馈“差不多额”，据此保留设置并停止。最终保存观测为 2026-11-01T10:04:40Z（America/Los_Angeles 当地 02:04:40 PST），不代替下次新鲜读回。

## 实际结果

- 使用原控制器25个文件和原GUI跟随入口；源码逐字节未改。R2仅在独立测试目录试过，未选作生产版本。
- 最后一轮原版控制器报告时长26.389秒，接受112条命令、10个运动段，报告7次视觉中心完成。此数值属于软件报告，不是机械角度标定。
- 已执行原GUI停止：follow=false、READY，输出关闭，flags=0、lease=0、active=false、armed=false。脉宽读回1632µs，无机械中点或正前方角度声明。
- GUI运行故障0；原生累计period_overruns=6，最终短测6→6；未发生owner fence。
- 视觉页保留；语音仍PAUSED、enabled=false、mic=false、无播放。人脸识别后端可用，末轮身份UNKNOWN。

## 当前接续指纹

- 生产根：`/home/root/aura-board-business-20261030/production-5259eab11e42af13`，runtime为其`runtime/aura`。
- startup：`226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15`。
- manifest：`8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8`；380项组件全部实际核对。
- GUI配置：`a695d620ddad3216de2d0447ec91d0e983a67343c2282179adece8014fccc063`。
- spec：`8ef2aa320d9ca2cf5a05e6b8b74458dfa7cf8c56be4efbebca69eed1102e2428`。
- 相机430894 / birth4011213；supervisor496785 / birth4302772；GTK496789 / birth4302880；boot `bebd3e7d-e984-4517-8cbb-211df7f1c6dc`。完整命令指纹见结构化交接。
- 原wide固件和VART已恢复；FDT `aed6f0cbe5184a6eed38449731e92106b923573cb324fa4c68079fdb5bbfd53e`。原相机以最后实际checkpoint恢复，旧readback的22项保留并追加本次runtime，未导出模板或私库。

相较原v24仅更新4项配置：GUI的现役相机readback、手动运行绑定、人脸跟随运行绑定、方向绑定；其余376项保持。记忆d6e策略、人格/动画和语音实现继续沿用。原相机实验阈值0.50与GUI身份阈值0.85属于不同设置，本轮均未更改。

## 证据与历史范围

- [最终实板读回](evidence/final_original_inventory_1793527480550065200.json)，SHA `cd4c6cd72d7a960a8baa47e0ef26bf30484328181b2bfb3fd26f96f82204fcae`。
- [最终原版跟随试验](evidence/test_original_gui_follow_1793527294434976800.json)，SHA `b7474d1dfee05fffbba1103055ff6db11d746332dce5777e7946e1f06b419ad6`。
- 板端原报告：`/home/root/aura-pan-wide-20261028/control-10282601/runs/ui-43122991403122/trial.json`，SHA `811f92d4801118d819b21e7b762afa9bf0652adac70ef27c09d8e43c9f95f9c0`。
- [完整交接](HANDOFF.json)、[源码/配置冻结包](package/original_direction_fix/publisher_bundle_manifest.json)、[本地入口更新前原字节](docs_state_final/before_manifest.json)。所有早期失败、方向事务修复、独立候选试验及旧发布历史均保留。

最初未转动后用户明确说明未给舵机上电，不将该轮误记为已确诊机械故障。上电后人类反馈用于方向确认；反向反馈后才修改极性。没有测量机械零点、实际±90°范围、识别准确率或长期稳定性。

## 后续使用

可在视觉页用原“人脸跟随”入口开启。当前所有本轮设备命令已结束；按用户分工设备串行权暂留本窗口，主窗口继续只读，未自动转交操作权。后续自动操作先现读boot、进程完整指纹、380项源码闭包、固件/VART、暂停偏好和输出状态。旧v24发布器及旧平台探针的startup/相机PID属于历史，不能直接沿用。
