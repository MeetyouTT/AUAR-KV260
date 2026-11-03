# 微雪电容屏：补齐运行时触摸驱动，待接线和实物验收

日期：2026-10-09，证据以 UTC 时间记录。用户确认屏幕为微雪电容触摸屏，要求尝试解决。具体型号、硬件修订及 TOUCH USB 接线位置尚未回复；不能仅凭 1024×600 显示分辨率确定型号。

## 结论

已为 KV260 当前内核编译、传输、正常加载 `hid-multitouch.ko`，驱动注册成功，界面 API 无错误且原视觉进程继续运行。**USB 仍未枚举触摸控制器，实物触摸尚未恢复或验收。** 当前驱动只在本次启动加载，没有修改启动镜像、开机自启配置或 FPGA。

最后只读检查（14:38 UTC）：驱动和模块均在，触摸设备列表为空；XInput 仍只有鼠标及摄像头/音响按键。界面在互动页，实际音量 64%、非静音、MCP01 可用，没有 STAGE ERROR。该读数更新此前设置验收时的 100%，本轮没有改动声音设置。

## 诊断证据与判断

- USB 树四个下游端口为 `1-1.1` 摄像头、`1-1.2` SIGMACHIP 鼠标、`1-1.3` MCP01、`1-1.4` U 盘；没有新增触摸控制器。鼠标为相对 X/Y 输入，不能当成触摸设备。
- 实际 `/proc/config.gz`：`CONFIG_INPUT_EVDEV=y`、`CONFIG_USB_HID=y`、`CONFIG_HID_GENERIC=y`，但 `CONFIG_HID_MULTITOUCH` 未设置；原系统没有该模块，`modinfo` 与 `modprobe -n` 均提示不存在。
- Xorg 的 libinput/evdev 驱动已经安装并工作，因此目前没有依据重启 Xorg、调整坐标矩阵或重刷系统。
- USB 未枚举时，缺少多点触摸模块不能独立解释整个连接现象；须先确认屏幕数据口、数据线与 KV260 主机口的实际连接。驱动补齐不等于控制器已经到达 USB 总线。

接线依据为微雪同类 HDMI 电容屏官方资料：[C 型接口说明](https://docs.waveshare.net/7inch_HDMI_LCD_C/) 区分 HDMI 显示与 micro USB 供电/触摸；[H 型产品说明](https://www.waveshare.com/7inch-hdmi-lcd-h.htm) 列出 USB Touch Port，并区分 Touch 与 Power Only；[同系列 Linux FAQ](https://docs.waveshare.net/7inch_HDMI_LCD_B/FAQ/) 提到通用 hid-multitouch。型号未确认，不能把树莓派 config.txt 或某个旧屏专用协议直接应用到本板。

## 驱动实现与验证

复用已有 Xilinx Linux 源码提交 `19984dd147fa7fbb7cb14b17400263ad0925c189`，原始 `drivers/hid/hid-multitouch.c` 与 `hid-ids.h` 无修改。在新独立目录复制准备好的头文件/构建工具，使用 GCC 11.2.0 交叉编译，不修改已有内核工程或重编整套镜像。

板端配置解压 SHA256 `3d97bf208930f5696093d2d1999b4a0b16bcb121c97d70ca286bb8d4986e81ef`。与已有准备配置逐项比较，只差编译器名称的 `.real` 文本；版本、SMP、模块卸载等配置匹配，MODVERSIONS 未启用。

模块 34944 字节，SHA256 `fce568b070bbc0e9210bc6417b39e1c57637d9d24d9fdebc4cb913603505417b`；vermagic 为 `5.15.36-xilinx-v2022.2 SMP mod_unload aarch64`，与板端已有 ZOCL 一致。ELF 为 AArch64，38 个外部符号都存在于准备内核的 Module.symvers。原源码、配置和 Module.symvers 哈希复查不变。

板端路径：`/home/root/aura-waveshare-touch-20261009/module-fce568b070bbc0e9/hid-multitouch.ko`。压缩传输 11780 字节，解压后大小/SHA 写后回读一致；再次核对实际内核配置和 vermagic，使用普通 `insmod`，没有强制加载。

加载后 `/sys/module/hid_multitouch` 与 `/sys/bus/hid/drivers/hid-multitouch` 均存在，内核正常解析 38 个所需符号。已有 MCP01/鼠标仍绑定 hid-generic；视觉 PID 16981、界面 PID 48503、dfx-mgrd PID 1036、Xorg PID 1097 均在。boot ID 不变，taint 保持原有 4096，没有新增值。最终 UI API 返回正常，内核未出现 multitouch 的未知符号/版本错误。

## 首次加载检查纠正

首次传输完成，但额外检查要求在 `/proc/kallsyms` 找到 `__ksymtab_*` 标签，因全部找不到而安全停止在 `insmod` 前。原因是当前内核 `CONFIG_KALLSYMS_ALL` 未设置，不公开这部分导出表和数据符号；并非已证明模块符号不兼容。

专门只读核对得到 54892 个符号名、0 个 `__ksymtab_*`，38 个所需名中只有数据符号 `jiffies` 不展示。准备内核 System.map 证明其类型为 D；其余 37 个函数在板端均可见。修正可见性检查后，保留版本/配置/SHA/函数检查，由正常内核加载器解析实际导出，成功加载。首次失败原件完整保留，没有重复写入或覆盖已传输模块。

## 文件、证据与下一步

工作目录：[aura-waveshare-touch-20261009](/home/ghmd/aura-waveshare-touch-20261009)。新增 `diagnose_touch.py`、`build_touch_module.py`、`load_touch_module.py`、`verify_touch_repair.py`，运行工件与日志均在该目录；UI 源程序本轮未修改。

原始证据分别为 `evidence/20261009T135654.695352Z-inspect/`（USB/内核/X11）、`20261009T140429.187412Z-inspect/`（完整配置与 ABI）、`20261009T140918.791930Z-module-load/`（首次检查停止）、`20261009T141504.357541Z-inspect/`（符号可见性）、`20261009T142502.870425Z-module-load/`（成功加载）、`20261009T143817.658151Z-inspect/`（最终复查）。

[独立核验结果](/home/ghmd/aura-waveshare-touch-20261009/validation_final.json) 重新核对 24 份 UART 响应、模块和构建原输入的大小/SHA；验证包含首次预期失败。没有重复无关 UI 测试，模块运行时验证不能代替手指点击与坐标校准。

下一步需要用户确认背面型号，并使用可传数据的 USB 线连接屏幕 TOUCH/触摸数据口至 KV260 USB-A。若口已占满，可拔下已安全卸载的 U 盘腾出口；保持现有显示连接。若屏幕有 Power Only 口，不应将其作为触摸数据口。识别到控制器后再验证点击、滑动、坐标与单次激活；通过后再考虑持久化驱动。当前 USB 枚举未到达，不能通过软件替代物理接线。
