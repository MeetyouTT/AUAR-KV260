# 断电后的摄像头预览恢复

记录时间：2026-10-08 08:04 UTC。用户要求“重新开机，断电了”。已读取 ZIP README、相关方案和既有运行/基准记录；本次范围为恢复板端摄像头画面及原蓝线。

## 实际结果

- 板子已由现场上电；本次没有远程开电或重启系统。第一次清单 boot 为 `0a3eb767-ec20-4c10-838f-0d0a176c0f58`，恢复前发生启动标识变化，首次脚本在启动进程前被检查拒绝。重新清单确认 boot 为 `f7a3ff07-fc20-4804-af12-c314a7a1847a`，具体重启原因未核实。
- 保存的发布包 `68bd0def762cc3cf` 源码 SHA 全部匹配；USB HD 720P Webcam 可用、相机无占用、HDMI/X11 1024×600、官方 B4096 活动 slot 0。
- 恢复既有纯视觉程序，PID 1498。启动后独立三秒核验采集 258→296、检测 183→211、显示入口 257→295、最终渲染 253→291；唯一相机所有者 [1498]、error=null、stopped=false、Monitor On。
- 实际 X11 截图有摄像头图像、正脸绿色框、中央蓝色竖线和 MOTION OFF。本次物理屏幕现场反馈尚未收到，不能把软件截图当作现场验收。
- 没有改变 FPGA 配置、启用 PWM、启动模拟运动服务或设置开机自启；串口回显恢复。机械参考在断电后标记为未核实，原图蓝线继续 x=320。

## 改动与证据

新增 [本次恢复脚本](../../../kv260-adaptation-check-20261006/scripts/preview_restore_20261008.py)，绑定已核验 boot、校验匹配发布清单、拒绝抢占相机，失败只回收本次启动的进程。更新只读清单选择逻辑，按当前发布路径匹配清单而非旧运行模式。更新 [当前运行指针](../../../kv260-realtime-vision-20261007/CURRENT_RUNTIME.json)、预览报告与机械基准记录；旧主机运行指针保存在恢复证据的 previous-host-runtime.json。

- [首次清单](../../../kv260-adaptation-check-20261006/evidence/20261008T075714.075327Z-restart_inventory/result.txt)
- [启动标识检查拒绝](../../../kv260-adaptation-check-20261006/evidence/20261008T080203.923202Z-preview_restore_20261008/result.txt)
- [重新清单](../../../kv260-adaptation-check-20261006/evidence/20261008T080236.045140Z-restart_inventory/result.txt)
- [恢复通过](../../../kv260-adaptation-check-20261006/evidence/20261008T080251.501650Z-preview_restore_20261008/result.txt)
- [独立核验](../../../kv260-adaptation-check-20261006/evidence/20261008T080318.369995Z-realtime_verify/verification.json) / [截图](../../../kv260-adaptation-check-20261006/evidence/20261008T080318.369995Z-realtime_verify/desktop.jpg)

本地检查语法与 UART 封装长度，实际板端恢复及独立核验均返回 0，输出 SHA 已校验。最初沙箱无法访问串口，使用既有获批的串口执行入口完成；未把失败尝试记作通过。

## 接续限制

摄像头仍未固定到舵机上，需要保持视角稳定，以蓝线为图像参考，重新核对机械零点与实测映射。真实随动尚未启用，不能宣称视觉与舵机协同验收完成。正式联合 FPGA 构建指针已显示 rc=0、implementation_complete=true，但 deployable=false、board_accessed=false；本次不部署未完成审查的候选。
