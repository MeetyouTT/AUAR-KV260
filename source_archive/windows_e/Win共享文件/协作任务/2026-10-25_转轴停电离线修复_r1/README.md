# 转轴停电期间离线修复 r1

**状态：离线已验证，未部署、未做新板测或实体随动验收。板卡仍按用户报告为断电。** 现役最后版本为continuous-v9/face-source-v11；来电必须检查新boot，不复用旧运动许可。原停电封存包保持不变。

候选及复验说明见[package/continuous_v10r1_candidate/README.md](package/continuous_v10r1_candidate/README.md)，冻结指纹见OFFLINE_PACKAGE_MANIFEST.json。

本轮处理：

1. 回区立即停止，稳定回区250ms且至少三张不同新图才开放新纠偏；单帧/未确认/跳变不能累加额度。
2. 合法新图在旧许可将到期时到达，不等待下一20ms tick，立即用它续交当前角度；不额外转动，旧帧不能续交。
3. 轨迹与实际提交均取图像250ms和真实检测锚500ms的更早截止，再保留原20ms提交余量；真失效和错上下文仍停。

48项本机回归＋13组成对合成回放通过，30文件SHA核对通过；ZIP在独立临时目录解压后重新执行同一复验，全部通过。没有连接串口、相机或MMIO，没有调用板端服务。源码、FakeDevice与真实Ruckig数学结果不能当作电气或机械证明。

| 同一合成输入 | 旧v9 | r1候选 |
|---|---:|---:|
| 六轮越界穿插单帧回区，左右分别测 | 累计18us | 累计3us |
| 四轮稳定回区后再越界 | 4次ARM/12us | 1次ARM/12us |
| 检测锚仅剩50ms时仍提交较新图像 | 许可可越过锚界120ms | 不越过检测锚截止 |

临时3us/轮、10us/s诊断限制仍在，未扩大行程/速度或放宽期限。它解决重复放行和一种可避免的丢ARM，不能据此宣称完整随人行走已经完成。

## 独立复验

在Ubuntu/Linux x86_64解压ZIP后运行（输出路径需不存在）：

```sh
python3 continuous_v10r1_candidate/verify_offline.py --output /tmp/aura-pan-offline-result.json
```

包内包含最小Python依赖和主机数学库；不是Windows原生运行包，也不是完整固件/模型发布包。目标板AArch64库只封存，不在本轮主机执行。

## 来电后

转轴动力先断开，按[原停电恢复清单](../2026-10-25_停电交接_转轴与来电恢复/README.md)恢复新启动。`package/continuous_v10r1_candidate/recovery/read_only_resume_after_outage.py`只是可审查的只读检查器，未在目标板运行；它不改服务/配置、不启运动，不替代新boot位置确认或部署审批。

完成无动力核验后，先影子对照，再小幅实体测试；不将此ZIP解压覆盖当前板端运行目录。Windows同步/接收及新冷启动状态尚未确认。
