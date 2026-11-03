# 持久启动修订提案：尚未安装或冷启动验证

## 已确认的重启回benchmark原因

本boot实读的 `/etc/dfx-mgrd/daemon.conf`：

```json
{"firmware_location":["/lib/firmware/xilinx"],"default_accel":"/etc/dfx-mgrd/default_firmware"}
```

`default_firmware` 是符号链接，目标 `/etc/dfx-mgrd/kv260-benchmark-b4096`，文件内容是 `kv260-benchmark-b4096\n`。`dfx-mgr.service` 在启动前执行 `/usr/bin/xlnx-firmware-detect`；这个脚本发现默认文件与应用目录有效就直接保留。本boot日志明确记录 `Default firmware detected: kv260-benchmark-b4096`。wide虽已安装，其目录存在不会改变默认选择。运行时 `xmutil loadapp wide` 不会替用户改这条持久默认链接。

实际daemon为保留的状态生命周期修复版：`/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd`，SHA `369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`。原unit通过两个既有drop-in保留了对 `kv260-repaired-zocl.service` 的依赖。不要为这次持久化覆盖vendor unit或删掉这些已工作的修复。

当前相机有效After没有dfx-mgr或wide就绪依赖；GUI也没有平台依赖。仅改默认链接还不能证明相机一定在wide、VART和设备树完整就绪之后创建DPU owner。dfx-mgr本身Type=simple，“daemon已运行”不能代替“默认应用已经加载完成”。

## 与运行时恢复分开的最小修订

先完成 `RECOVERY_REVIEW.md` 中本boot正常停止、真checkpoint、成套wide、ID/STOP、原相机承接；保持无运动。随后主操作者另行封存默认链接、daemon.conf、服务有效配置及新增文件的所有权清单，再审阅持久修订。

1. 在 `/etc/dfx-mgrd/` 新建单独的 `aura-visual-servo-b4096-wide-v1` 选择文件，原字节为 `aura-visual-servo-b4096-wide-v1\n`，并回读核对。不要覆盖benchmark选择文件。
2. 对 `default_firmware` 使用同目录临时symlink再原子replace，改指向新wide选择文件。先记录当前symlink本身的目标、owner和mode；保留可回退的benchmark目标。不能用普通write穿过现有symlink去覆盖benchmark文件。
3. 不在相机运行时restart dfx-mgr，也不调用loadapp来“测试链接”。链接只改变后续启动选择，当前平台由前一阶段真实回执证明。
4. 新增一个只读就绪oneshot，并让相机Require/After它。就绪检查只读配置、固件与文件，既不加载PL也不创建runner；默认应用失败时应保持相机未启动，避免暗中回落benchmark后继续推理。

供审阅的unit形状（路径/文件SHA由最终发布事务确定，**当前没有安装该文件，也没有对应已发布脚本**）：

```ini
# /etc/systemd/system/aura-wide-platform-ready.service
[Unit]
Description=Verify selected AURA wide platform before native camera owner
Requires=dfx-mgr.service
After=dfx-mgr.service
Before=aura-camera-ui.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -B <经审阅发布的纯只读wide-ready脚本>
TimeoutStartSec=75
RemainAfterExit=yes
```

```ini
# 独立、唯一命名的 aura-camera-ui.service.d drop-in
[Unit]
Requires=aura-wide-platform-ready.service
After=aura-wide-platform-ready.service
```

GUI若加入平台依赖也只能引用同一只读ready unit，并保留所有现役来源/启动校验与暂停偏好。不要覆盖当前业务树、改Native shutdown保护或引入自动ARM。原camera的Restart=no、KillMode=process、SendSIGKILL=no、TimeoutStop=infinity必须保持。依赖的反向停止顺序应让相机正常完成checkpoint后才退出平台daemon。

就绪脚本需要实现的具体只读条件：

- 先核candidate manifest6a4b…及wide四固件配套，按已发布SHA核自身源；不import原相机/driver，不CDLL，不打开/dev或数据库。
- 在有限窗口轮询实际firmware-name、FPGA operating、精确wide VART；读取已加载DT的wide/ZOCL状态，计算本次FDT SHA供日志。不得把历史整棵FDT SHA当跨boot常量。
- 只有全部满足才退出0；超时、未知配置、文件不符、平台错误都退出非0，不自行unload/load、不强停相机、不修正guard、VART或marker。
- 不把“平台ready”写成“机械参考有效”。每个boot启动后运动保持关闭，旧动作、旧宽度和旧方向资格不自动重放。

这里的unit和检查逻辑仍是提案，尚需由主操作者落实成独立源文件并静态检查依赖图；不能把带占位ExecStart的unit直接安装。完成 `systemd-analyze verify` 只证明配置语法/依赖可解析，不代替冷启动。

## 业务与机械绑定仍有独立的重启边界

当前face readback配置严格绑定boot、相机PID/birth。持久默认wide并不自动授权修改这些字段。冷启动后应保留现有“源码闭包/原模型与私库选择/TTL/真实源推进”证据链，再由正常配置事务承接真实owner。如果要完全无人值守恢复GUI，应另审并实现这一动态承接事务，不能把其变成只改boot/PID或弱化身份校验。

机械context同样不能跨boot自动成为合格参考。平台可以在默认disabled状态就绪，但位置/方向/现场条件未建立时，GUI运动入口应继续拒绝；不把断电前1505µs或方向+1作为新boot事实。

## 冷启动验收与回退

安排受控重启前先结束业务、保持监听false/无播放/无运动、正常释放相机并确认真实最终checkpoint及其归档可读。转轴当前通电，重启/重配置期间需要现场观察与断电准备；不能用“RTL复位disabled”代替该电气观察。

冷启动验收至少记录：新bootID与正确时钟观察、default symlink新目标、dfx日志默认wide、实际wide/operating/VART和新FDT、ready unit先于相机、新相机真实owner/原checkpoint新内核归档链/真实源推进、第一项ID/STOP-only输出关闭，以及GUI/聆听偏好实际状态。没有自动ARM、没有重放旧动作。若只写入配置而没有这轮实证，状态应是 `PERSISTENCE_CONFIGURED_COLD_BOOT_PENDING`。

回退只撤回本事务拥有且SHA匹配的新ready unit/drop-in，原子恢复封存的benchmark默认symlink；保留所有历史、源码、Native marker和计数。当前运行平台的回退仍须先正常停止相机、封存它的新最终checkpoint、确认无DPU用户，再成套切回benchmark。不得以restart dfx-mgr或直接覆写VART替代该顺序。
