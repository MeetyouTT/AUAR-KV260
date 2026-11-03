# 2026-10-04：FPGA 开发环境实际核验

用户要求先确认 FPGA 环境是否完成。读取 ZIP 的 README、FPGA 框架/开工资料、当前分工和最新实际记录后，在独立工作目录 `/home/ghmd/kv260-fpga-environment-review-20261004` 核验工具和已有 M3 工件。

## 当前实际结果

- Vivado、v++、Vitis HLS 当前版本均为 2022.2，启动返回 0。
- K26 `xck26-sfvc784-2LV-c` 和 KV260 SOM board part 1.4 查询通过；在新目录创建 Clocking Wizard 并生成输出产品成功。
- 原 M3 RTL 当前 K26 OOC 综合通过，54 LUT、118 FF，Synthesis/device 授权实际取得并正常释放。没有改原 RTL、约束、工程或产物。
- XSCT -nodisp/HSI 实际读取原联合 XSA，175 个 cell，返回 0。
- PetaLinux 2022.2 环境加载、自带依赖检查和 build/config 入口检查通过；未发现 TFTP server 的提示保留，未配置/验收 TFTP 启动。
- 11 项原工件和 11 项原源码/配置 SHA-256 核验前后通过；四个设置脚本 SHA-256 一致，主机六项依赖安装状态通过。
- 独立主机回读 64 项检查全部通过。核验时约 30.8 GiB RAM、18 逻辑 CPU、110 GiB 可用存储。

结论：KV260/K26 核心 FPGA 开发环境已就绪，可从现有 M3 继续开发。完整 PWM/运动监督、实际引脚约束、最终联合实现及匹配 SDK/sysroot 等仍需完成。历史 M3 寄存器/DPU 板测已存在，不能替代完整运动验收；最新启动活动包为官方 benchmark，本轮未切换 PL 或连接板卡。

## 失败及修正

PetaLinux 检查的两次失败分别来自核查脚本的位置参数继承和错误版本变量名，安装未改动。v2 修正 source 调用，v3 改用真实 `PETALINUX_VER`，最终通过。三版脚本和全部失败证据保留，未在线修改正在运行的控制器。

## 下一步

先冻结运动 ABI 与实际 PWM/停止针脚和 XDC，再实现 PWM/监督 RTL、仿真和与 DPU 的联合实现。现有 routed 设计最差 setup/hold 余量 +0.009 ns、CLB site 占用 99.45%、LUT 60.23%，外部输入/输出延迟约束有 7/9 项缺口，新增运动逻辑需重新证明布局和时序。

本轮没有完整重建 FPGA/OS、安装新工具、修改全局 shell 配置或板端配置。板端 overlay/显示时钟告警仍由平台收尾跟踪。

详见 [核验报告](/home/ghmd/kv260-fpga-environment-review-20261004/FPGA_ENVIRONMENT_REPORT.md)、[结构化状态](/home/ghmd/kv260-fpga-environment-review-20261004/FPGA_ENVIRONMENT_STATUS.json)、[64 项独立核验](/home/ghmd/kv260-fpga-environment-review-20261004/reviews/20261004T113221.737583Z/review.json)。
