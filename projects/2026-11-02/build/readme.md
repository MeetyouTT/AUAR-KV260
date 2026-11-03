# FPGA 重建

发布物针对 xck26-sfvc784-2LV-c，板定义 kv260_som 1.4 与 kv260_carrier 1.3。Vivado/Vitis 2022.2 与原 PetaLinux 5.15.36-xilinx-v2022.2、DPUCZDX8G B4096 系统配套。src/fpga/inputs 保存基础 BD/XCI，visual_servo.sv、disabled_audio.sv 和 pin.xdc 是最终自定义输入。PWM 连接 E10、LVCMOS33、DRIVE 8、SLOW。src/fpga/reference/platform.xpr 是原工程索引，路径移机后使用下面的生成入口。仓库的 vendor 子目录保留原工程用到的三组非工具内置 IP 输入，包括旧 IP 缓存中被引用的文件。

在工程根目录，针对自己的 AMD 安装根目录执行以下命令。构建输出必须位于工程之外的全新目录。Vivado 本身以及商业 IP 的工具许可按原开发环境准备。

~~~sh
export XILINX_VITIS=/opt/Xilinx/Vitis/2022.2
export VIVADO_BIN=/opt/Xilinx/Vivado/2022.2/bin/vivado
python3 -B build/scripts/fpga.py check
python3 -B build/scripts/fpga.py prepare --out "$HOME/auar-implementation-01"
python3 -B build/scripts/fpga.py implement --out "$HOME/auar-implementation-01"
~~~

prepare 创建工程、绑定接口和地址、验证 BD、生成 IP 并写入 wrapper。implement 单作业综合，使用随包的 ac5f85a1… 参考 DCP 做增量布局，布线以后检查时序及 DRC，再重新打开本轮生成的已布线 DCP，导出含 bit 的 XSA。也可以对新目录执行 fpga.py build 一次编排两个阶段。reference/incremental.dcp 是窄范围前版的布局参考；最终 wide 已布线检查点的历史 SHA 为 933c712d…，二者用途不同。build/original 保留原始开发脚本供追溯。原脚本在工程模式末步导出 XSA 时找不到手工写出的 bit，发布入口直接采用成功的“从 routed checkpoint 非工程模式导出”路径。

在已有布局布线结果上单独复跑导出时，可用 fpga.py export --checkpoint /path/to/source_routed.dcp --out /new/place。原 wide DCP 保存在开发 Ubuntu 的 ~/aura-pan-wide-20261028/implementation/source_routed.dcp，主 RAR 中的 wide.xsa 和预构建固件可直接做交付校验。全量 implement 也会重新生成此阶段的 DCP。

~~~sh
export BOOTGEN="$XILINX_VITIS/bin/bootgen"
python3 -B build/scripts/pack_firmware.py \
  --xsa "$HOME/auar-implementation-01/implementation/visual_servo_source_implemented.xsa" \
  --bit "$HOME/auar-implementation-01/implementation/export-resume/visual_servo_source.bit" \
  --out "$HOME/auar-firmware-01"
~~~

固件入口核对同次 bit 与 XSA 的配置数据，比较已冻结的 HWH 后生成 .bit.bin，并配套相同接口的 DTBO、XCLBIN 与 shell.json。单元和端口发生改变时须重新生成设备树和对应的 XRT 工件。检查读者重新实现的输出应关注关键接口、时序、路由及 DRC，见 build/reports。原 wide 实现 setup WNS 为 0.001 ns，hold WHS 为 0.000 ns，DRC error 为 0。本轮新目录复跑的结果见 build/reports/clean_directory_validation.json，原始综合、布局、布线的结果与日志日期另行保留。低核机器优先做 check 和根目录的 reproduce，完整实现需要安装工具并预留运行内存和磁盘。

低核工作站可直接使用主 RAR 旁的 auar_wide_source_routed.dcp，其 SHA-256 为 933c712d30fd6aa549eb785a21dc6ca360ce179b24b9d3fb76a777d662d96007。进入解压后的 aura 并载入 Vivado 2022.2 后执行以下命令。

~~~sh
python3 -B build/scripts/fpga.py export --checkpoint ../auar_wide_source_routed.dcp --out "$HOME/auar-xsa-01"
~~~
