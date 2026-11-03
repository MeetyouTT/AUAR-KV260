# 来电恢复与转轴验证 r2

**最新：用户问下一步后，手动控制已恢复READY，实体保持停止。** [新启动绑定、6项回归与现场拒绝验证](MANUAL_REBIND.md)。中位按用户报告为1420µs，最后实际指令仍1445µs、flags0/lease0，本轮没有试转或回中。手动仅开放本次实际观察的1445～1465µs；人脸随动按钮明确锁定，待本次方向确认及r2实体接入。完整人脸随动尚未验收。

此前“约100°”被用户澄清为回到原中位校准位置的总角度，并非20µs增量产生100°；撤回此前异常归因，保留原始反馈和更正。1420µs是用户报告的中位参数，不是本轮外部仪器测得的角度/波形标定，也没有在本轮发1420µs指令。不能把本轮最后1445µs误记为机械中位。

## 新启动与业务恢复

- boot `16a07283-9e14-45e6-816d-3bda4cf333a7`。首次检查为官方DPU固件；本轮按当前新启动的正常停机/fresh checkpoint、pending0/ZOCL0及固件配对恢复联合VSRV/2固件，没有改旧boot字段绕过。
- fresh checkpoint SHA `ad33a40bf60451c2834133143e1b04b9bf7104716cf09ae3192f5efd7e2ca5f8`；原生runtime unit仍`7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32`。新FDT合并与ID/STOP通过；固件初始1500只是寄存器复位值，不是机械归零。
- camera13537、GUI监督13573、editor14694运行，258个GUI组件pins通过。SFace/YuNet RUNNING，identity ready；这不等于本人的跨天/发型变化识别准确率通过。
- 新boot首次primary1，后续复查2；可选模型超限均0。旧boot primary26及可选3/7是独立历史，不以断电后计数下降宣称问题解决；本轮受控重启承接当前boot历史，没有删预算。
- 实际屏幕12次采样均匹配相机、12个不同画面；左绿线55/55样本通过。左线仍实际画面10%/脸框左边，右线80.647%/脸中心。

## r2修复及真实输入影子验证

r1把“发布时有效、收到时检测锚刚好超过500ms”也记为INVALID_FACE_ANCHOR，首轮真实影子因此退出。r2将正常锚超时归为可恢复SOURCE_EXPIRED，未来时间戳/类型异常仍拒绝，不延长250ms图像期限、500ms检测锚或20ms提交余量。

纯内存执行器影子manifest `51265395999f650b9e00465a5a56f7000d447113c0ff6d53de66db33cefd63ec`：

| 窗口 | 真实包 | READY | 虚拟提交 | 虚拟目标变化 | 实体ARM/COMMIT |
|---|---:|---:|---:|---:|---:|
| 10.054秒 | 283 | 281 | 8 | 3 | 0/0 |
| 30.048秒 | 849 | 750 | 29 | 12 | 0/0 |

两轮无fatal、不加载实体驱动、不打开MMIO，并持有运动锁隔离实体写入。30秒仍有82个UNCONFIRMED和17个EXPIRED，所以输入连续性/实体平滑不能称已彻底解决。r2只上板影子目录；实体自动consumer仍未部署为r2。3µs/每次持续越界、10µs/s仍是诊断限制，不能冒充完整长距离跟随。

## 本次实体测试与用户更正

1. 用户在场后首次初始化1448→1445µs，再做1445→1465→1445µs往返；往返43ACK，最终flags0/lease0。初次包含恢复位置过程，不能把全部机械位移称作20µs增量效果。
2. 用户澄清100°为回原中位后，取消额外初始化，仅从当前指令做1445→1465→1445µs；42ACK、epoch3/ack42，最后width/target1445、flags0/lease0。用户确认小幅往返并停住。
3. 用户进一步明确1420为中位并要求“等一下”。板端已记录用户中位、观察回执及暂停；没有发回1420的命令，也没有启动自动随动。后续运动必须承接本次暂停，不能自行重跑试转。

本轮最后状态：板端`/home/root/aura-pan-current-20261024/16a07283/state.json`为`USER_PAUSED_OUTPUT_STOPPED_20US_OBSERVED_CENTER_1420`；新`center-reference.json`保存用户中位1420与尚未应用的事实。手动GUI仍保留旧boot保护，不能仅改boot字段恢复。

## 代码、复验与证据

- [过滤后的恢复/影子/实体/用户回执证据](VERIFICATION.json)，不包含原图、录音、身份库正文或私有UART原文。
- `package/continuous_v10r2_candidate/`为PS候选源码；`package/shadow_v10r2/`为真实人脸＋纯内存执行器入口。配套common、主机数学库和FakeDevice保留在包内；[源码指纹](PACKAGE_SHA256.json)。
- 本轮共享副本独立运行49项回归＋13组成对合成回放通过，影子执行器7项检查通过。软件不等于电气或机械验收；没有Windows接收/同步代确认。

Linux x86_64本机复验（输出文件需不存在，不接板卡）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B package/continuous_v10r2_candidate/verify_offline.py --output /tmp/aura-pan-r2-verification.json
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s package/shadow_v10r2 -p 'test_*.py'
```

原停电包与r1归档保持；本目录不直接覆盖板端运行目录。后续先按用户中位参数对齐当前启动的合法运动绑定，再做用户在场的边界动作验证；当前暂停期间不执行该计划。
