# KV260 文件、固件与现场入口

## 先在普通 Linux 生成暂存树

在工程根目录执行以下命令。输出目录须是全新的目录。脚本用 Python 标准库进行校验与复制。默认路径只生成离线树，不会连接 KV260、加载固件、启动摄像头或发送转轴命令。

~~~sh
python3 -B board/scripts/stage.py --out "$HOME/auar-rootfs-01" --audio ../auar_board_audio_dependencies.zip
~~~

若仅评审源码可省略 --audio。KV260 运行环境为 PetaLinux、aarch64、Linux 5.15.36-xilinx-v2022.2、板侧 Python 3.9、VART/XIR/Vitis AI 3.0、GTK/X11、GStreamer/OpenCV、ALSA 和 MCP01，显示屏为 1024×600。另一台 x86_64 Ubuntu 20.04 用于审查、仿真、构建和根文件系统暂存，板侧 wheel 仅用于对应的 ARM Python。stage 根据 board/config/deployment_files.json 和原部署树地址归位，保留历史上用 SHA 固定的相同文件。运行状态由实际目标设备生成。

## 运行前的检查顺序

1. **平台和固件。** 保留原卡或在匹配内核、设备树和 XRT 的独立系统上安装。固件文件位于 board/firmware/aura-visual-servo-b4096-wide-v1，身份和接口来自配对清单 board/firmware_pairing.json。用 xmutil listapps 查看实际加载项；板端切换平台前按原硬件操作流程关闭执行者、断开转轴动力并核实 STOP。工程包的离线阶段不需要上述操作。不得在正在采集或控制执行器的系统上直接覆盖已加载的固件或替换目录。
2. **相机和模型。** 运行时的独立相机服务为 aura-camera-ui.service。src/camera/runtime 保留 r4 Python 命名空间，entry_chain 和 native_operator 包含后续同版驱动源码，board/config/deployment_files.json 列出历史依赖路径。三模型采用已发布的 INT8 图，其 DPU 指纹必须与平台一致。可用本地 GET /health 核实相机所有者和 detector，再基于本机 boot_id、相机 PID / start ticks、启动命令、配置和 source SHA 建立当次绑定。原版本在 src/software/tools/private_gallery_reference.py 与 board/runtime 等模块验证绑定；板上的旧 PID 和开机证明只能用于历史核对。
3. **语音和个人数据。** 从独立附件准备 Paraformer-small、GTCRN、Silero、ECAPA 模型和 CPython 3.9 ARM wheel。config/board_avatar_gtk.json 固定了目录及参数。模型端口 8797 对应 Windows 有线 192.168.50.1，板端为 192.168.50.2。先在 Windows 验证 /health，再启动业务。个人数据库由对应设备保管。在已有演示卡复用自己的私有区和 production-bootstrap.json，首次配置应走 common/board_production_bootstrap.py 的数据初始化/封存流程并核对新回执。历史数据库哈希和权限回执不能代替新设备的初始化。
4. **界面和转轴。** board/config/startup.snapshot.json 含当前 380 项业务文件锁，launcher.py 校验入口、屏幕和组件。原界面服务为 aura-avatar-ui.service。现役设备可执行 systemctl status aura-camera-ui.service aura-avatar-ui.service 与 journalctl -u aura-avatar-ui.service -n 40 检查运行状态。暂存树不能直接覆盖正运行的根目录。在设备绑定、显示/音频、个人业务初始回执完成且手动核实当前机械位置后，使用原 GUI 的跟随按钮。原项目使用 ABIv2 的 0x10282601 wide 固件；本包没有将回中、寻零或历史运动试验加入启动步骤。

## 重新编译原生软件

在与目标一致的 AArch64 开发环境运行 sh build/scripts/native_build.sh /path/to/new-output。需要开发头文件和运行库、支持 C++20 的编译器、CMake、pkg-config、OpenCV、VART/XIR、Vitis AI Library、libpng 与 GLES。脚本保留原生运动、像素、YOLO、VART 和角色渲染的构建步骤，使用 CORE 与第三方头文件的原布局。保留已编译的 AArch64 原生 VART 对象用于链接；设置 RECOMPILE_VART=1 可从随包 C++ 文件重编译。当前打包验证运行了 host 侧的 C 协议及 Python 假时钟场景；整组 AArch64 原生重编译需要目标 SDK。新编译出的库需重新建立本次发布的 SHA 绑定。

## 板上原件与归位检查

三段系统提示音原件和 feedback.json 位于 board/public_cues。角色界面与语音业务都固定绑定这份清单。默认暂存命令将它们放回原板路径；校验会核对两处配置、清单 SHA、固定台词、采样数和音频数据。三段均为原选定音色的 24 kHz 单声道 PCM16，分别为问候 2.66 秒、邀请 2.28 秒和思考 1.79 秒。

board/config/image_inputs.json 中原先需从原卡补取的 12 个文件已全部收录，包括 7 项相机历史校验文件和现役原生算子共享库。两个 AArch64 共享库的原件位于 board/camera_binaries。board/systemd 保留界面和相机服务本体及两项服务实际加载的 56 份追加配置。board/config/public_board_resources.json 记录原路径、SHA 和加载顺序，并列出相机服务启动前实际核验的 20 组输入。data/reference/public_feedback.json 是历史生成回执；本轮取件和解包复验记录在交付目录的 verification 中。

普通电脑按本页第一条暂存命令即可还原这些文件。若另有匹配的原卡镜像，--image-root /mnt/kv260-original 可附加比对 12 个历史哈希。真实目标上的摄像头需重新绑定本次开机信息，个人数据初始化按本页的实机步骤进行。

若 Ubuntu 安装了 bubblewrap 且启用了用户命名空间，可对暂存树另外运行原版文件读取逻辑。该工具在只读隔离环境中执行相机服务的 20 道原始文件哈希检查，再用角色程序自身的两处提示音入口读取三段 WAV。结果写入外部 JSON 文件。

~~~sh
python3 -B board/scripts/replay_public_startup.py --rootfs "$HOME/auar-rootfs-01" --out "$HOME/auar-public-replay-01.json"
~~~
